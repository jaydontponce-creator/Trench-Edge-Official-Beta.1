from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json, re
from .provisional import complete_feature_vector, completeness, display_statistics
from .schemas import MatchupRequest, MarketSnapshot, DerivedMetrics
from .engine import calculate_matchup

DATA = Path(__file__).resolve().parents[1] / "data"

def _slug(a:str,h:str)->str:
    return re.sub(r"[^a-z0-9]+","-",f"{a}-{h}".lower()).strip("-")

def _key(g:Dict[str,Any])->str:
    away=g.get("away") or g.get("away_team") or g.get("awayTeam") or ""
    home=g.get("home") or g.get("home_team") or g.get("homeTeam") or ""
    return _slug(away,home)

def _shell(g:Dict[str,Any])->Dict[str,Any]:
    if g.get("decision") is not None:
        return dict(g)
    away=g.get("away") or g.get("awayTeam")
    home=g.get("home") or g.get("homeTeam")
    return {
        "id":g.get("id") or _slug(away,home),
        "away":away,"home":home,
        "classification":g.get("classification","NCAA"),
        "kickoff":g.get("kickoff") or g.get("startDate"),
        "venue":g.get("venue"),
        "market":{"display":"Market / line pending live refresh","home_spread":None,"total":None},
        "prediction":{"away_points":None,"home_points":None,"model_margin_home":None,"model_total":None,
                      "spread_edge_home":None,"total_edge_over":None},
        "decision":{"state":"NEEDS_DATA","market":None,"side":None,"edge":None,
                    "reasons":["Game is on the Week 2 slate. TE is waiting for the complete live feature package before issuing a wager status."],
                    "gate_results":{}},
        "ev":{"probability":None,"break_even_probability":None,"expected_value":None,
              "source":"pending","calibrated":False,"odds_american":None},
        "derived":{"ocrs":None,"dqs":None,"dfr":None,"fpse":None,"source":"pending","details":{}},
        "attribution":{"drivers":[],"counterweights":[],"ecs":None,"dac":None},
        "trench":{"away":{"RunMOTE":None,"PassMOTE":None},"home":{"RunMOTE":None,"PassMOTE":None}},
        "quality":{"away_reliability":None,"home_reliability":None},
        "provider_meta":{"mode":"schedule-shell"}
    }

def _load(path:Path):
    if not path.exists(): return None
    return json.loads(path.read_text(encoding="utf-8"))


def _apply_provisional_prediction(g:Dict[str,Any])->Dict[str,Any]:
    """Populate a best-available V4.1 score for any schedule-shell game.

    Neutral standardized inputs are used only where historical/live inputs are
    genuinely unavailable. Provenance and completeness are exposed so the UI
    never confuses imputation with observed information.
    """
    if (g.get("prediction") or {}).get("home_points") is not None:
        return g
    away=g.get("away",""); home=g.get("home","")
    af,ap=complete_feature_vector({},False)
    hf,hp=complete_feature_vector({},True)
    req=MatchupRequest(
        game_id=str(g.get("id") or _slug(away,home)),
        away_team=away,home_team=home,
        away_features=af,home_features=hf,
        market=MarketSnapshot(),
        derived_metrics=DerivedMetrics(dqs=0.0,ocrs=50.0,dfr=50.0,fpse=50.0,source="missing")
    )
    try:
        result=calculate_matchup(req)
        g["prediction"]={
            "away_points":result.away.expected_points,
            "home_points":result.home.expected_points,
            "model_margin_home":result.model_margin_home,
            "model_total":result.model_total,
            "spread_edge_home":None,"total_edge_over":None
        }
    except Exception:
        # absolute last-resort display baseline
        g["prediction"]={"away_points":28.0,"home_points":30.0,"model_margin_home":2.0,
                         "model_total":58.0,"spread_edge_home":None,"total_edge_over":None}
    g["feature_provenance"]={"away":ap,"home":hp}
    g["feature_completeness"]={"away":completeness(ap),"home":completeness(hp)}
    g["statistics"]={"away":display_statistics({}),"home":display_statistics({})}
    g["projection_status"]="PROVISIONAL"
    g["decision"]={
        **(g.get("decision") or {}),
        "state":"NEEDS_DATA",
        "market":None,"side":None,"edge":None,
        "reasons":["Best-available score is published using population-average fallbacks for missing standardized inputs. Wager qualification is withheld until data quality improves."]
    }
    return g


def complete_week_board(week:int)->Dict[str,Any]:
    full = _load(DATA/f"week{week}_full_product_demo.json")
    if full is None and week == 2:
        full = _load(DATA/"week2_full_product_demo.json")
    if full is None:
        full = _load(DATA/f"week{week}_complete_schedule_fallback.json")
    if full is None and week == 2:
        full = _load(DATA/"week2_complete_schedule_fallback.json")
    if full is None:
        full={"games":[]}

    base=[_apply_provisional_prediction(_shell(g)) for g in full.get("games",[])]

    live=_load(DATA/f"week{week}_outputs.json") or {"games":[]}
    live_games=live.get("games",[]) if isinstance(live,dict) else live
    by_key={_key(g):g for g in live_games if _key(g)}

    merged=[]
    for g in base:
        k=_key(g)
        if k in by_key:
            calculated=dict(by_key[k])
            for fld in ("classification","kickoff","venue","branding"):
                if calculated.get(fld) is None and g.get(fld) is not None:
                    calculated[fld]=g[fld]
            merged.append(calculated)
        else:
            merged.append(g)

    existing={_key(g) for g in merged}
    for g in live_games:
        if _key(g) not in existing:
            merged.append(g)

    qualified=sum(1 for g in merged if (g.get("decision") or {}).get("state") in ("PASS","QUALIFIED"))
    failed=sum(1 for g in merged if (g.get("decision") or {}).get("state")=="FAIL")
    waiting=sum(1 for g in merged if (g.get("decision") or {}).get("state")=="NEEDS_DATA")

    return {
        "games":merged,
        "week":week,
        "season":live.get("year",full.get("season",2026)) if isinstance(live,dict) else 2026,
        "mode":"complete-board",
        "summary":{"games":len(merged),"qualified":qualified,"pass":failed,"waiting_for_data":waiting},
        "message":"Complete NCAA Week board with live TE calculations overlaid on the full schedule."
    }
