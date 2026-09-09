
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import defaultdict
import json, math, os
from .providers.cfbd import CFBDProvider
from .providers.odds import OddsProvider
from .providers.weather import OpenMeteoProvider
from .mote_sources import advanced_to_partial_raw, merge_havoc, attach_sack_rates
from .priors import build_pregame_rows
from .mote import build_mote_slate
from .schemas import MatchupRequest, MarketSnapshot, DerivedMetrics, DQSComponents, OCRSComponents
from .engine import calculate_matchup
from .branding import from_cfbd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
FRONTEND_DATA = Path(__file__).resolve().parents[2] / "frontend" / "week2_board.json"

def _safe(v, default=None):
    return default if v is None else v

def _team_row_from_partial(p: Dict[str,Any]) -> Dict[str,Any]:
    return {
        "game_id": p.get("game_id"),
        "team": p.get("team"),
        "opponent": p.get("opponent"),
        "off_run_line": p.get("off_run_line"),
        "off_run_stuffavoid": p.get("off_run_stuffavoid"),
        "off_run_power": p.get("off_run_power"),
        "off_pass_protect": p.get("off_pass_protect"),
        "off_havoc_avoid": p.get("off_havoc_avoid"),
        "def_run_line": p.get("def_run_line"),
        "def_run_stuff": p.get("def_run_stuff"),
        "def_run_power": p.get("def_run_power"),
        "def_pass_rush": p.get("def_pass_rush"),
        "def_havoc": p.get("def_havoc"),
        "off_epa": p.get("off_epa"),
        "off_rush_epa": p.get("off_rush_epa"),
        "off_pass_epa": p.get("off_pass_epa"),
        "off_firstdown": p.get("off_firstdown"),
        "off_explosive": p.get("off_explosive"),
        "off_pace": p.get("off_pace"),
    }

def _feature_quality_score(row: Dict[str,Any], fields: List[str]) -> float:
    present=sum(1 for f in fields if row.get(f) is not None)
    return round(100*present/max(1,len(fields)),2)

def _dqs_components(row: Dict[str,Any], market_ready: bool, weather_ready: bool) -> DQSComponents:
    core_fields=[
        "off_run_line","off_run_stuffavoid","off_run_power","off_pass_protect","off_havoc_avoid",
        "def_run_line","def_run_stuff","def_run_power","def_pass_rush","def_havoc",
        "off_epa","off_rush_epa","off_pass_epa","off_firstdown","off_explosive","off_pace"
    ]
    q=_feature_quality_score(row,core_fields)
    # Data-quality scores, not football-strength scores.
    return DQSComponents(
        ol_personnel=q,
        dl_personnel=q,
        player_performance_history=q,
        transfers_new_starters=70.0 if q>=70 else q,
        continuity=70.0 if row.get("pregame_games",0)>=1 else 55.0,
        injuries_availability=70.0,
        scheme_coaching=75.0,
        advanced_efficiency=q,
        opponent_adjustment=80.0 if market_ready else 65.0,
    )

def _percentile_risk(value: float|None, low: float=-8, high: float=8, invert: bool=False) -> float:
    if value is None: return 50.0
    x=max(low,min(high,float(value)))
    score=(x-low)/(high-low)*100
    return round(100-score if invert else score,2)

def _ocrs_components(row: Dict[str,Any], dfr: float, fpse: float) -> OCRSComponents:
    return OCRSComponents(
        run_mote_disadvantage=_percentile_risk(row.get("RunMOTE"), invert=True),
        pass_mote_disadvantage=_percentile_risk(row.get("PassMOTE"), invert=True),
        qb_pressure_vulnerability=_percentile_risk(row.get("PassMOTE"), invert=True),
        overall_efficiency_mismatch=_percentile_risk(row.get("z_off_epa"), low=-3, high=3, invert=True),
        explosiveness_mismatch=_percentile_risk(row.get("z_off_explosive"), low=-3, high=3, invert=True),
        finishing_drive_mismatch=_percentile_risk(row.get("z_off_firstdown"), low=-3, high=3, invert=True),
        personnel_continuity_uncertainty=60.0 if row.get("pregame_games",0)<=1 else 40.0,
        game_script_vulnerability=_percentile_risk(row.get("PassMOTE"), invert=True),
        dfr=float(dfr),
        fpse=float(fpse),
    )

def _v4_features(row: Dict[str,Any], home: bool) -> Dict[str,float]:
    # V4 expects standardized continuous inputs. The refresh pipeline supplies z-scored fields.
    # Special teams and turnovers remain neutral when the provider snapshot does not supply authenticated fields.
    return {
        "DefensiveWeakness": float(-(row.get("z_opp_def_epa") or 0.0)),
        "OffEPA": float(row.get("z_off_epa") or 0.0),
        "HomeField": 1.0 if home else -1.0,
        "DefensiveTurnoverGeneration": float(row.get("z_def_turnover_generation") or 0.0),
        "PassEPA": float(row.get("z_off_pass_epa") or 0.0),
        "OppSpecialTeams": float(row.get("z_opp_special_teams") or 0.0),
        "RunMOTE": float(row.get("RunMOTE") or 0.0),
        "Pace": float(row.get("z_off_pace") or 0.0),
        "SpecialTeams": float(row.get("z_special_teams") or 0.0),
        "FirstDownRate": float(row.get("z_off_firstdown") or 0.0),
        "PassMOTE": float(row.get("PassMOTE") or 0.0),
        "Explosiveness": float(row.get("z_off_explosive") or 0.0),
        "RushEPA": float(row.get("z_off_rush_epa") or 0.0),
        "OppTurnoverGeneration": float(row.get("z_opp_turnover_generation") or 0.0),
        "WeatherAdjustment": float(row.get("weather_adjustment") or 0.0),
    }

def _board_card(result, game: Dict[str,Any], home_row: Dict[str,Any], away_row: Dict[str,Any], market: Dict[str,Any], provider_meta: Dict[str,Any]) -> Dict[str,Any]:
    return {
        "id": str(game.get("id") or game.get("game_id")),
        "away": game.get("awayTeam") or game.get("away_team"),
        "home": game.get("homeTeam") or game.get("home_team"),
        "kickoff": game.get("startDate") or game.get("start_date"),
        "venue": game.get("venue"),
        "market": market,
        "prediction": {
            "away_points": result.away_expected_points,
            "home_points": result.home_expected_points,
            "model_margin_home": result.model_margin_home,
            "model_total": result.model_total,
            "spread_edge_home": result.spread_edge_home,
            "total_edge_over": result.total_edge_over,
        },
        "decision": result.decision.model_dump(),
        "ev": result.ev.model_dump(),
        "derived": result.derived_metrics.model_dump(),
        "attribution": result.attribution,
        "trench": {
            "away": {"RunMOTE": away_row.get("RunMOTE"), "PassMOTE": away_row.get("PassMOTE"), "RunOTE":away_row.get("RunOTE"),"PassOTE":away_row.get("PassOTE")},
            "home": {"RunMOTE": home_row.get("RunMOTE"), "PassMOTE": home_row.get("PassMOTE"), "RunOTE":home_row.get("RunOTE"),"PassOTE":home_row.get("PassOTE")},
        },
        "quality": {
            "away_reliability": away_row.get("Reliability"),
            "home_reliability": home_row.get("Reliability"),
            "away_pregame_games": away_row.get("pregame_games"),
            "home_pregame_games": home_row.get("pregame_games"),
        },
        "branding": provider_meta.get("branding",{}),
        "provider_meta": provider_meta,
    }

def _load_demo_board() -> Dict[str,Any]:
    p=DATA_DIR/"demo_week2_board.json"
    return json.loads(p.read_text()) if p.exists() else {"games":[],"mode":"demo"}

def refresh_week(year:int=2026, week:int=2) -> Dict[str,Any]:
    cfbd=CFBDProvider()
    odds=OddsProvider()
    weather=OpenMeteoProvider()

    if not cfbd.ready:
        demo=_load_demo_board()
        demo["refresh_status"]="DEMO_MODE"
        demo["message"]="CFBD_API_KEY not configured; showing bundled operational demo snapshot."
        FRONTEND_DATA.write_text(json.dumps(demo,indent=2))
        return demo

    games=[]
    try: games.extend(cfbd.games(year,week,classification="fbs"))
    except TypeError: games.extend(cfbd.games(year,week))
    try: games.extend(cfbd.games(year,week,classification="fcs"))
    except Exception: pass
    # De-duplicate cross-division games returned in both classification feeds.
    unique={}
    for g in games: unique[str(g.get("id"))]=g
    games=list(unique.values())
    if not games:
        return {"games":[],"refresh_status":"NO_GAMES"}

    # Pull current + prior season source data needed for priors.
    previous_adv=cfbd.advanced_game_stats(year-1)
    current_completed=cfbd.advanced_game_stats(year, week=max(1,week-1))
    previous_havoc=cfbd.game_havoc(year-1)
    current_havoc=cfbd.game_havoc(year, week=max(1,week-1))

    prev_partials=[advanced_to_partial_raw(x) for x in previous_adv]
    cur_partials=[advanced_to_partial_raw(x) for x in current_completed]
    merge_havoc(prev_partials, previous_havoc)
    merge_havoc(cur_partials, current_havoc)

    # Fetch play-by-play for sack rate reconstruction.
    prev_plays=[]
    for w in range(1,16):
        try:
            prev_plays.extend(cfbd.plays(year=year-1, week=w))
        except Exception:
            continue
    cur_plays=[]
    for w in range(1,max(1,week)):
        try:
            cur_plays.extend(cfbd.plays(year=year, week=w))
        except Exception:
            continue
    attach_sack_rates(prev_partials, prev_plays)
    attach_sack_rates(cur_partials, cur_plays)

    prev_rows=[_team_row_from_partial(p) | {"game_id":p.get("game_id")} for p in prev_partials]
    cur_rows=[_team_row_from_partial(p) | {"game_id":p.get("game_id")} for p in cur_partials]

    # Build one row per team in the target slate.
    slate=[]
    for g in games:
        home=g.get("homeTeam"); away=g.get("awayTeam")
        if not home or not away: continue
        slate.append({"game_id":str(g.get("id")),"team":home,"opponent":away})
        slate.append({"game_id":str(g.get("id")),"team":away,"opponent":home})

    priors=build_pregame_rows(slate,prev_rows,cur_rows)

    # Standardize all scoring and MOTE base features across the target week.
    from .standardize import standardize_slate
    standard_fields=[
        "off_run_line","off_run_stuffavoid","off_run_power","off_pass_protect","off_havoc_avoid",
        "def_run_line","def_run_stuff","def_run_power","def_pass_rush","def_havoc",
        "off_epa","off_rush_epa","off_pass_epa","off_firstdown","off_explosive","off_pace"
    ]
    standardize_slate(priors, standard_fields)
    build_mote_slate(priors)

    by_game=defaultdict(dict)
    for r in priors: by_game[str(r["game_id"])][r["team"]]=r

    odds_snapshot=odds.ncaaf_snapshot() if odds.ready else []
    market_by_matchup=odds.index_consensus(odds_snapshot) if odds.ready else {}

    board=[]
    for g in games:
        gid=str(g.get("id")); home=g.get("homeTeam"); away=g.get("awayTeam")
        if home not in by_game[gid] or away not in by_game[gid]: continue
        hr=by_game[gid][home]; ar=by_game[gid][away]

        market=market_by_matchup.get((away,home),{})
        market_ready=bool(market)
        dqs_h=_dqs_components(hr,market_ready,False)
        dqs_a=_dqs_components(ar,market_ready,False)

        # Experimental risk inputs, using currently available pregame fields.
        dfr_inputs_h={k:hr.get(k) for k in ["pre_off_epa","pre_off_pass_epa","pre_off_rush_epa","pre_off_firstdown","pre_off_pass_protect","pre_off_havoc_avoid","RunMOTE","PassMOTE","Reliability"]}
        dfr_inputs_a={k:ar.get(k) for k in ["pre_off_epa","pre_off_pass_epa","pre_off_rush_epa","pre_off_firstdown","pre_off_pass_protect","pre_off_havoc_avoid","RunMOTE","PassMOTE","Reliability"]}

        # Until live ST priors are available, FPSE uses neutral provider-ready inputs and remains experimental.
        fpse_neutral={"st_epa_pp_pre":0.0,"punt_epa_pp_pre":0.0,"ko_epa_pp_pre":0.0,"havoc_total_rate_pre":0.12,"takeaway_rate_pre":0.02,"Reliability":hr.get("Reliability",0)}
        from .empirical_risk import calculate_dfr, calculate_fpse
        dfr_h=calculate_dfr(dfr_inputs_h); dfr_a=calculate_dfr(dfr_inputs_a)
        fpse_h=calculate_fpse(fpse_neutral); fpse_a=calculate_fpse(fpse_neutral)

        ocrs_h=_ocrs_components(hr,dfr_h,fpse_h)
        ocrs_a=_ocrs_components(ar,dfr_a,fpse_a)

        # One matchup request includes per-team V4 features; the engine handles both scoring sides.
        ms=MarketSnapshot(
            home_spread=market.get("home_spread"),
            total=market.get("total"),
            spread_price_american=market.get("spread_price_american",-110),
            total_price_american=market.get("total_price_american",-110),
        )
        # Use the weaker DQS and higher OCRS as matchup gates.
        from .risk import calculate_dqs, calculate_ocrs
        dqh,_=calculate_dqs(dqs_h.model_dump()); dqa,_=calculate_dqs(dqs_a.model_dump())
        oh,_=calculate_ocrs(ocrs_h.model_dump()); oa,_=calculate_ocrs(ocrs_a.model_dump())

        req=MatchupRequest(
            game_id=gid, away_team=away, home_team=home,
            away_features=_v4_features(ar,False),
            home_features=_v4_features(hr,True),
            market=ms,
            derived_metrics=DerivedMetrics(
                dqs=min(dqh,dqa), ocrs=max(oh,oa), dfr=max(dfr_h,dfr_a), fpse=max(fpse_h,fpse_a),
                source="refresh_v5",
                details={"home_dqs":dqh,"away_dqs":dqa,"home_ocrs":oh,"away_ocrs":oa}
            )
        )
        result=calculate_matchup(req)
        try: home_meta=cfbd.team(home)
        except Exception: home_meta=None
        try: away_meta=cfbd.team(away)
        except Exception: away_meta=None
        board.append(_board_card(result,g,hr,ar,market,{
            "cfbd":True,"odds":odds.ready,"weather":weather.ready,
            "mode":"live","year":year,"week":week,
            "branding":{
                "home":from_cfbd(home_meta,home),
                "away":from_cfbd(away_meta,away)
            }
        }))

    payload={"games":board,"refresh_status":"LIVE","mode":"live","year":year,"week":week}
    (DATA_DIR/f"week{week}_outputs.json").write_text(json.dumps(payload,indent=2))
    FRONTEND_DATA.write_text(json.dumps(payload,indent=2))
    return payload
