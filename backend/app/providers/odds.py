from __future__ import annotations
import os, statistics
from typing import Optional, Dict, Any, List
from .base import HTTPProvider, ProviderError

class OddsProvider(HTTPProvider):
    url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds"
    def __init__(self, api_key: Optional[str]=None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
    @property
    def ready(self): return bool(self.api_key)
    def fetch(self, regions="us", markets="h2h,spreads,totals"):
        if not self.api_key: raise ProviderError("ODDS_API_KEY is not configured")
        return self.get_json(self.url, params={
            "apiKey":self.api_key,"regions":regions,"markets":markets,
            "oddsFormat":"american","dateFormat":"iso"
        })
    def consensus(self, home: str, away: str, rows: Optional[List[dict]]=None):
        rows = rows if rows is not None else self.fetch()
        def norm(s): return s.lower().replace("state","st").replace("university","").strip()
        event = None
        for e in rows:
            if norm(home) in norm(e.get("home_team","")) or norm(e.get("home_team","")) in norm(home):
                if norm(away) in norm(e.get("away_team","")) or norm(e.get("away_team","")) in norm(away):
                    event=e; break
        if not event: return None
        spreads=[]; totals=[]; home_ml=[]; away_ml=[]; stamps=[]
        for b in event.get("bookmakers",[]):
            stamps.append(b.get("last_update"))
            for m in b.get("markets",[]):
                if m.get("key")=="spreads":
                    for o in m.get("outcomes",[]):
                        if o.get("name")==event.get("home_team") and o.get("point") is not None: spreads.append(float(o["point"]))
                elif m.get("key")=="totals":
                    pts=[float(o["point"]) for o in m.get("outcomes",[]) if o.get("point") is not None]
                    if pts: totals.append(pts[0])
                elif m.get("key")=="h2h":
                    for o in m.get("outcomes",[]):
                        if o.get("name")==event.get("home_team"): home_ml.append(o.get("price"))
                        if o.get("name")==event.get("away_team"): away_ml.append(o.get("price"))
        return {
            "home_spread": statistics.median(spreads) if spreads else None,
            "total": statistics.median(totals) if totals else None,
            "source":"The Odds API consensus",
            "timestamp": max([s for s in stamps if s], default=None),
            "bookmaker_count": len(event.get("bookmakers",[])),
            "event_id": event.get("id")
        }


    def ncaaf_snapshot(self):
        return self.fetch(markets="h2h,spreads,totals")

    def index_consensus(self, events):
        out={}
        for ev in events or []:
            home=ev.get("home_team"); away=ev.get("away_team")
            if not home or not away: continue
            spreads=[]; totals=[]
            for bm in ev.get("bookmakers",[]):
                for m in bm.get("markets",[]):
                    if m.get("key")=="spreads":
                        hs=next((o for o in m.get("outcomes",[]) if o.get("name")==home),None)
                        if hs and hs.get("point") is not None: spreads.append(float(hs["point"]))
                    if m.get("key")=="totals":
                        ov=next((o for o in m.get("outcomes",[]) if o.get("name")=="Over"),None)
                        if ov and ov.get("point") is not None: totals.append(float(ov["point"]))
            if spreads or totals:
                out[(away,home)]={
                    "home_spread": sum(spreads)/len(spreads) if spreads else None,
                    "total": sum(totals)/len(totals) if totals else None,
                    "spread_price_american": -110,
                    "total_price_american": -110,
                    "books": len(ev.get("bookmakers",[]))
                }
        return out
