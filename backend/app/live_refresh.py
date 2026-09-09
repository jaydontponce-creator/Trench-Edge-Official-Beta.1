
from __future__ import annotations
from pathlib import Path
from typing import Dict,Any
import json, time, threading, copy
from .providers.odds import OddsProvider
from .injuries import merged_injuries
from .calibration import assess as calibrate_market

DATA = Path(__file__).resolve().parents[1]/"data"
_lock=threading.Lock()
_cache: Dict[str,Any]={"at":0.0,"week":None,"payload":None}

def _load_board(week:int) -> Dict[str,Any]:
    # board_service is optional so this file can coexist with older deployments
    try:
        from .board_service import complete_week_board
        return complete_week_board(week)
    except Exception:
        p=DATA/f"week{week}_outputs.json"
        if p.exists():
            x=json.loads(p.read_text(encoding="utf-8"))
            return x if isinstance(x,dict) else {"games":x,"week":week}
        return {"games":[],"week":week}

def _norm(s:str)->str:
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())

def _market_index(rows):
    out={}
    for ev in rows or []:
        away=ev.get("away_team",""); home=ev.get("home_team","")
        out[(_norm(away),_norm(home))]=ev
    return out

def _consensus_from_event(ev:Dict[str,Any]) -> Dict[str,Any]:
    home=ev.get("home_team"); spreads=[]; totals=[]; stamps=[]
    for bm in ev.get("bookmakers",[]):
        if bm.get("last_update"): stamps.append(bm["last_update"])
        for m in bm.get("markets",[]):
            if m.get("key")=="spreads":
                for o in m.get("outcomes",[]):
                    if o.get("name")==home and o.get("point") is not None:
                        spreads.append(float(o["point"]))
            elif m.get("key")=="totals":
                ov=next((o for o in m.get("outcomes",[]) if o.get("name")=="Over" and o.get("point") is not None),None)
                if ov: totals.append(float(ov["point"]))
    return {
        "home_spread": sum(spreads)/len(spreads) if spreads else None,
        "total": sum(totals)/len(totals) if totals else None,
        "spread_price_american":-110.0,
        "total_price_american":-110.0,
        "bookmaker_count":len(ev.get("bookmakers",[])),
        "timestamp":max(stamps) if stamps else None,
        "source":"The Odds API live consensus"
    }

def _refresh_market_and_decision(game:Dict[str,Any], market:Dict[str,Any]) -> None:
    if not market: return
    game["market"]={**(game.get("market") or {}),**market}
    p=game.get("prediction") or {}
    margin=p.get("model_margin_home"); total=p.get("model_total")
    spread=market.get("home_spread"); mtotal=market.get("total")
    spread_edge=(float(margin)+float(spread)) if margin is not None and spread is not None else None
    total_edge=(float(total)-float(mtotal)) if total is not None and mtotal is not None else None
    p["spread_edge_home"]=spread_edge
    p["total_edge_over"]=total_edge
    game["prediction"]=p

    options=[]
    if spread_edge is not None:
        side=game.get("home") if spread_edge>0 else game.get("away")
        line=(spread if spread_edge>0 else -float(spread))
        label=f"{side} {line:+g}"
        options.append(("spread",label,abs(spread_edge)))
    if total_edge is not None:
        label=("Over" if total_edge>0 else "Under")+f" {float(mtotal):g}"
        options.append(("total",label,abs(total_edge)))
    if not options: return
    market_type,side,edge=max(options,key=lambda x:x[2])
    odds=-110.0
    cal=calibrate_market(market_type,edge,odds=odds,model_margin_home=margin)
    game["ev"]=cal

    dqs=(game.get("derived") or {}).get("dqs")
    # Keep model's integrity gates. Provisional score stays visible even if wager is withheld.
    enough_edge=edge>=2.5
    enough_quality=dqs is not None and float(dqs)>=60
    positive_ev=(cal.get("expected_value") or 0)>0
    if enough_edge and enough_quality and positive_ev:
        state="PASS"
        reasons=["Live market price clears TE's edge, data-quality and calibrated EV gates."]
    elif enough_quality:
        state="FAIL"
        reasons=["TE has a current projection, but the live price does not clear all betting gates."]
    else:
        state="NEEDS_DATA"
        reasons=["TE is publishing a provisional projection, but data quality is not high enough for a qualified wager."]
    game["decision"]={
        **(game.get("decision") or {}),
        "state":state,"market":market_type,"side":side,"edge":round(edge,3),"reasons":reasons
    }

def fast_refresh(week:int=2, max_age_seconds:int=60, force:bool=False) -> Dict[str,Any]:
    now=time.time()
    with _lock:
        if (not force and _cache["payload"] is not None and _cache["week"]==week
                and now-_cache["at"] < max_age_seconds):
            payload=copy.deepcopy(_cache["payload"])
            payload["cache_age_seconds"]=round(now-_cache["at"],1)
            return payload

        board=_load_board(week)
        games=copy.deepcopy(board.get("games",[]))
        odds=OddsProvider()
        rows=[]
        market_error=None
        if odds.ready:
            try: rows=odds.ncaaf_snapshot()
            except Exception as exc: market_error=str(exc)
        idx=_market_index(rows)
        injuries=merged_injuries()

        for g in games:
            ev=idx.get((_norm(g.get("away","")),_norm(g.get("home",""))))
            if ev:
                _refresh_market_and_decision(g,_consensus_from_event(ev))
            team_inj={
                "away":injuries.get("teams",{}).get(g.get("away"),{}),
                "home":injuries.get("teams",{}).get(g.get("home"),{})
            }
            g["injuries"]=team_inj
            g.setdefault("live_meta",{})
            g["live_meta"].update({
                "refreshed_epoch":now,
                "refresh_interval_seconds":60,
                "market_live":bool(ev),
                "injury_feed_ready":injuries.get("provider_ready",False),
                "injury_source":injuries.get("source"),
            })

        payload={
            **board,
            "games":games,
            "live_refresh":True,
            "refreshed_epoch":now,
            "refresh_interval_seconds":60,
            "market_provider_ready":odds.ready,
            "market_error":market_error,
            "injury_provider_ready":injuries.get("provider_ready",False),
        }
        _cache.update({"at":now,"week":week,"payload":copy.deepcopy(payload)})
        return payload
