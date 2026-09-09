from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from .providers import CFBDProvider, OddsProvider, OpenMeteoProvider, InjuryProvider
from .providers.base import ProviderError

class WeekPipeline:
    """Provider orchestration layer.

    It can discover the weekly FBS slate and automatically attach market/weather/efficiency/roster/injury
    source snapshots. It does NOT invent missing standardization constants, MOTE formulas, DFR/FPSE scores,
    or probability calibration. Those remain explicit model-readiness blockers.
    """
    def __init__(self):
        self.cfbd=CFBDProvider(); self.odds=OddsProvider(); self.weather=OpenMeteoProvider(); self.injuries=InjuryProvider()

    def provider_status(self):
        return {
            "cfbd":{"ready":self.cfbd.ready,"requires":"CFBD_API_KEY"},
            "odds":{"ready":self.odds.ready,"requires":"ODDS_API_KEY"},
            "weather":{"ready":True,"requires":None},
            "injuries":{"ready":self.injuries.ready,"requires":"timestamped injuries.json or licensed injury adapter"},
        }

    def refresh(self, year:int, week:int)->Dict[str,Any]:
        report={"year":year,"week":week,"generated_at":datetime.now(timezone.utc).isoformat(),"providers":self.provider_status(),"games":[],"errors":[]}
        if not self.cfbd.ready:
            report["errors"].append("CFBD_API_KEY missing: schedule/efficiency/roster enrichment cannot run.")
            return report
        try:
            games=self.cfbd.games(year,week)
            sp_rows=self.cfbd.sp_ratings(year)
            sp={r.get("team"):r for r in sp_rows}
            odds_rows=self.odds.fetch() if self.odds.ready else []
            venue_rows=self.cfbd.venues()
            venue_map={v.get("name"):v for v in venue_rows if v.get("name")}
        except Exception as exc:
            report["errors"].append(str(exc)); return report

        for g in games:
            home=g.get("homeTeam") or g.get("home_team"); away=g.get("awayTeam") or g.get("away_team")
            if not home or not away: continue
            row={
                "game_id":str(g.get("id")),"home_team":home,"away_team":away,
                "kickoff":g.get("startDate") or g.get("start_date"),"venue":g.get("venue"),
                "source_snapshots":{},"model_readiness":{}
            }
            row["source_snapshots"]["sp"]={"home":sp.get(home),"away":sp.get(away)}
            try: row["source_snapshots"]["market"]=self.odds.consensus(home,away,odds_rows) if odds_rows else None
            except Exception as exc: row["source_snapshots"]["market_error"]=str(exc)
            row["source_snapshots"]["injuries"]={"home":self.injuries.for_team(home),"away":self.injuries.for_team(away)}
            venue=venue_map.get(row.get("venue"))
            if venue and row.get("kickoff"):
                lat=venue.get("latitude") or venue.get("lat")
                lon=venue.get("longitude") or venue.get("lon")
                if lat is not None and lon is not None:
                    try: row["source_snapshots"]["weather"]=self.weather.game_weather(float(lat),float(lon),row["kickoff"])
                    except Exception as exc: row["source_snapshots"]["weather_error"]=str(exc)
            # Roster is fetched team-by-team. This provides player size/position source data for the future authenticated MOTE builder.
            try:
                row["source_snapshots"]["roster"]={"home":self.cfbd.roster(home,year),"away":self.cfbd.roster(away,year)}
            except Exception as exc: row["source_snapshots"]["roster_error"]=str(exc)
            row["model_readiness"]={
                "schedule":True,"efficiency":bool(sp.get(home) and sp.get(away)),
                "market":row["source_snapshots"].get("market") is not None,
                "injuries":self.injuries.ready,"roster":row["source_snapshots"].get("roster") is not None,
                "weather":row["source_snapshots"].get("weather") is not None,
                "standardization":False,"mote":False,"dfr_fpse":False,"probability_ev":False
            }
            report["games"].append(row)
        return report
