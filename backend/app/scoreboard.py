
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict
import json, time, threading, re
from .providers.cfbd import CFBDProvider

DATA = Path(__file__).resolve().parents[1]/"data"
_lock=threading.Lock()
_cache={"at":0.0,"week":None,"payload":None}

def _norm(s:str)->str:
    return re.sub(r"[^a-z0-9]+","",(s or "").lower())

def _first(g:Dict[str,Any], *names, default=None):
    for n in names:
        if g.get(n) is not None:
            return g.get(n)
    return default

def _load_schedule(week:int)->list[Dict[str,Any]]:
    candidates=[
        DATA/f"week{week}_full_product_demo.json",
        DATA/f"week{week}_complete_schedule_fallback.json",
        DATA/"week2_full_product_demo.json" if week==2 else None,
        DATA/"week2_complete_schedule_fallback.json" if week==2 else None,
    ]
    for p in candidates:
        if p and p.exists():
            payload=json.loads(p.read_text(encoding="utf-8"))
            return payload.get("games",[]) if isinstance(payload,dict) else payload
    return []

def _shell_card(g:Dict[str,Any])->Dict[str,Any]:
    away=_first(g,"away","awayTeam","away_team")
    home=_first(g,"home","homeTeam","home_team")
    return {
        "id":str(_first(g,"id",default=f"{away}-{home}")),
        "away":away,"home":home,
        "away_score":None,"home_score":None,
        "kickoff":_first(g,"kickoff","startDate","start_date"),
        "venue":_first(g,"venue","venueName"),
        "completed":False,"status":"scheduled","period":None,"clock":None,"detail":"Scheduled",
        "live":False,
        "classification":_first(g,"classification",default="NCAA"),
        "branding":_first(g,"branding",default={}),
    }

def _live_card(g:Dict[str,Any])->Dict[str,Any]:
    away=_first(g,"awayTeam","away_team","away")
    home=_first(g,"homeTeam","home_team","home")
    completed=bool(_first(g,"completed",default=False))
    away_score=_first(g,"awayPoints","away_points","awayScore")
    home_score=_first(g,"homePoints","home_points","homeScore")
    status=_first(g,"status","gameStatus","state",default="scheduled")
    period=_first(g,"period","currentPeriod","quarter")
    clock=_first(g,"clock","currentClock","displayClock")
    detail=_first(g,"statusDetail","detail")
    return {
        "id":str(_first(g,"id",default=f"{away}-{home}")),
        "away":away,"home":home,
        "away_score":away_score,"home_score":home_score,
        "kickoff":_first(g,"startDate","start_date","kickoff"),
        "venue":_first(g,"venue","venueName"),
        "completed":completed,"status":status,"period":period,"clock":clock,"detail":detail,
        "live": (not completed and (away_score is not None or home_score is not None))
    }

def scoreboard(week:int=2,year:int=2026,max_age_seconds:int=5,force:bool=False):
    now=time.time()
    with _lock:
        if (not force and _cache["payload"] is not None and _cache["week"]==week
            and now-_cache["at"]<max_age_seconds):
            out=dict(_cache["payload"])
            out["cache_age_seconds"]=round(now-_cache["at"],2)
            return out

        # Full schedule is always the base, so not-yet-started games are visible.
        base=[_shell_card(g) for g in _load_schedule(week)]
        by_key={(_norm(g["away"]),_norm(g["home"])):g for g in base}

        cfbd=CFBDProvider()
        err=None
        if cfbd.ready:
            try:
                rows=[]
                for cls in ("fbs","fcs"):
                    try:
                        rows.extend(cfbd.games(year,week,classification=cls))
                    except Exception:
                        pass
                for raw in rows:
                    live=_live_card(raw)
                    key=(_norm(live["away"]),_norm(live["home"]))
                    if key in by_key:
                        current=by_key[key]
                        # Keep schedule/branding if provider omits them.
                        for fld in ("kickoff","venue"):
                            if live.get(fld) is None:
                                live[fld]=current.get(fld)
                        live["classification"]=current.get("classification","NCAA")
                        live["branding"]=current.get("branding",{})
                        by_key[key]=live
                    else:
                        by_key[key]=live
            except Exception as exc:
                err=str(exc)

        games=list(by_key.values())
        payload={
            "games":games,
            "week":week,"season":year,
            "refreshed_epoch":now,
            "refresh_interval_seconds":5,
            "provider":"CFBD + complete schedule fallback",
            "provider_ready":cfbd.ready,
            "error":err,
            "accuracy_note":"Every scheduled Week game is shown. Scores and game state update as quickly as the upstream provider publishes them."
        }
        _cache.update({"at":now,"week":week,"payload":payload})
        return payload
