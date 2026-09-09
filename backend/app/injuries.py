
from __future__ import annotations
from pathlib import Path
from typing import Dict,Any
import json, os, urllib.request

DATA = Path(__file__).resolve().parents[1]/"data"

class InjuryProvider:
    """Optional injury/availability adapter.

    If INJURY_FEED_URL is configured, it expects JSON and optionally an
    INJURY_API_KEY bearer token. Without a provider, TE remains operational and
    labels injury information as unavailable rather than inventing it.
    """
    def __init__(self):
        self.url=os.getenv("INJURY_FEED_URL")
        self.key=os.getenv("INJURY_API_KEY")

    @property
    def ready(self): return bool(self.url)

    def fetch(self) -> Dict[str,Any]:
        if not self.url:
            return {"teams":{},"source":"not_configured"}
        req=urllib.request.Request(self.url)
        if self.key:
            req.add_header("Authorization",f"Bearer {self.key}")
        with urllib.request.urlopen(req,timeout=12) as r:
            payload=json.loads(r.read().decode("utf-8"))
        if isinstance(payload,dict):
            payload.setdefault("source","external_injury_feed")
            payload.setdefault("teams",{})
            return payload
        return {"teams":{},"source":"invalid_injury_feed"}

def manual_injuries() -> Dict[str,Any]:
    p=DATA/"manual_injuries.json"
    if not p.exists(): return {"teams":{},"source":"manual_none"}
    return json.loads(p.read_text(encoding="utf-8"))

def merged_injuries() -> Dict[str,Any]:
    manual=manual_injuries()
    provider=InjuryProvider()
    external=provider.fetch() if provider.ready else {"teams":{},"source":"not_configured"}
    teams=dict(external.get("teams",{}))
    teams.update(manual.get("teams",{}))  # manual overrides external
    return {
        "teams":teams,
        "source": external.get("source") if provider.ready else manual.get("source","not_configured"),
        "provider_ready":provider.ready
    }
