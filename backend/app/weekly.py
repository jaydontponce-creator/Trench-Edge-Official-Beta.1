
from __future__ import annotations
from pathlib import Path
from typing import Dict,Any
import json, datetime
from .refresh import refresh_week

DATA=Path(__file__).resolve().parents[1]/"data"

def current_cfb_week(today=None):
    # Application override is preferred because NCAA week boundaries can vary.
    override=(DATA/"active_week.json")
    if override.exists():
        d=json.loads(override.read_text())
        return int(d.get("season",2026)), int(d.get("week",2))
    return 2026,2

def run_weekly_refresh():
    season,week=current_cfb_week()
    return refresh_week(season,week)
