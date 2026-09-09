from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from .base import HTTPProvider, ProviderError

class CFBDProvider(HTTPProvider):
    base = "https://api.collegefootballdata.com"
    def __init__(self, api_key: Optional[str]=None):
        self.api_key = api_key or os.getenv("CFBD_API_KEY")
    @property
    def ready(self): return bool(self.api_key)
    def _headers(self):
        if not self.api_key:
            raise ProviderError("CFBD_API_KEY is not configured")
        return {"Authorization": f"Bearer {self.api_key}"}
    def get(self, path: str, **params):
        return self.get_json(self.base + path, params=params, headers=self._headers())
    def games(self, year: int, week: int, season_type: str="regular", classification: str="fbs"):
        return self.get("/games", year=year, week=week, seasonType=season_type, classification=classification)
    def plays(self, year: int, week: int, team: Optional[str]=None):
        p = {"year":year,"week":week,"seasonType":"regular","classification":"fbs"}
        if team: p["team"] = team
        return self.get("/plays", **p)
    def core_ratings(self, year: int): return self.get("/ratings/core", year=year)
    def sp_ratings(self, year: int): return self.get("/ratings/sp", year=year)
    def roster(self, team: str, year: int):
        # CFBD legacy-compatible REST route. Kept behind the provider abstraction so it can be replaced without touching TE.
        return self.get("/roster", team=team, year=year)
    def team(self, team: str):
        rows = self.get("/teams", school=team)
        return rows[0] if rows else None
    def venues(self): return self.get("/venues")
    def advanced_game_stats(self, year: int, week: Optional[int]=None, team: Optional[str]=None, exclude_garbage_time: bool=True):
        p={"year":year,"seasonType":"regular","excludeGarbageTime":str(exclude_garbage_time).lower()}
        if week is not None: p["week"]=week
        if team: p["team"]=team
        return self.get("/stats/game/advanced", **p)
    def advanced_season_stats(self, year: int, team: Optional[str]=None, start_week: Optional[int]=None, end_week: Optional[int]=None, exclude_garbage_time: bool=True):
        p={"year":year,"classification":"fbs","excludeGarbageTime":str(exclude_garbage_time).lower()}
        if team: p["team"]=team
        if start_week is not None: p["startWeek"]=start_week
        if end_week is not None: p["endWeek"]=end_week
        return self.get("/stats/season/advanced", **p)
    def game_havoc(self, year: int, week: Optional[int]=None, team: Optional[str]=None):
        p={"year":year,"seasonType":"regular"}
        if week is not None: p["week"]=week
        if team: p["team"]=team
        return self.get("/stats/game/havoc", **p)

