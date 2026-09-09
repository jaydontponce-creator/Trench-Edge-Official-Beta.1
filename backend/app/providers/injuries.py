from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import json

class InjuryProvider:
    """Production-safe injury adapter.

    No authenticated free college-football injury API is assumed. This provider reads a timestamped
    JSON snapshot produced by any licensed feed or verified research process. Replacing this adapter
    later does not change the TE engine.
    """
    def __init__(self, path: Optional[Path]=None):
        self.path = path or (Path(__file__).resolve().parents[2] / "data" / "injuries.json")
    @property
    def ready(self):
        if not self.path.exists(): return False
        try:
            data=json.loads(self.path.read_text())
            return bool(data.get("teams")) and data.get("source") not in (None,"missing","not_connected")
        except Exception:
            return False
    def load(self):
        if not self.path.exists(): return {"teams":{},"source":"missing"}
        return json.loads(self.path.read_text())
    def for_team(self, team: str):
        return self.load().get("teams",{}).get(team, {"players":[],"completeness":0,"availability_score":None})
