
from __future__ import annotations
from typing import Any, Dict
import time, threading
from .providers.cfbd import CFBDProvider

_lock=threading.Lock()
_cache={"at":0.0,"week":None,"payload":None}

def _first(g:Dict[str,Any], *names, default=None):
    for n in names:
        if g.get(n) is not None:
            return g.get(n)
    return default

def _card(g:Dict[str,Any])->Dict[str,Any]:
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

        cfbd=CFBDProvider()
        games=[]
        err=None
        if cfbd.ready:
            try:
                rows=[]
                try: rows.extend(cfbd.games(year,week,classification="fbs"))
                except Exception: pass
                try: rows.extend(cfbd.games(year,week,classification="fcs"))
                except Exception: pass
                seen={}
                for g in rows:
                    seen[str(g.get("id") or f"{g.get('awayTeam')}-{g.get('homeTeam')}")]=g
                games=[_card(g) for g in seen.values()]
            except Exception as exc:
                err=str(exc)

        payload={
            "games":games,
            "week":week,"season":year,
            "refreshed_epoch":now,
            "refresh_interval_seconds":5,
            "provider":"CFBD",
            "provider_ready":cfbd.ready,
            "error":err,
            "accuracy_note":"Scores and game state are refreshed as quickly as the upstream provider publishes them."
        }
        _cache.update({"at":now,"week":week,"payload":payload})
        return payload
