from __future__ import annotations
from collections import defaultdict
from typing import Dict, Any, List, Optional
import math
from .standardize import zscore, StandardizationUnavailable

# Raw feature builder. It deliberately keeps MOTE as an upstream supplied/derived field because
# the v1.1 master spec locks its role but does not authenticate a fresh OL/DL-to-MOTE numerical formula.

PASS_TYPES = {"Pass Reception","Pass Incompletion","Passing Touchdown","Pass Completion","Interception Return"}
RUSH_TYPES = {"Rush","Rushing Touchdown"}


def aggregate_plays(plays: List[dict], team: str) -> Dict[str, float]:
    own=[p for p in plays if p.get("offense")==team and not p.get("garbageTime",False)]
    if not own: return {}
    ppa=[p.get("ppa") for p in own if p.get("ppa") is not None]
    passes=[p for p in own if "Pass" in str(p.get("playType",""))]
    rushes=[p for p in own if "Rush" in str(p.get("playType",""))]
    def avg(xs): return sum(xs)/len(xs) if xs else 0.0
    pass_epa=avg([p["ppa"] for p in passes if p.get("ppa") is not None])
    rush_epa=avg([p["ppa"] for p in rushes if p.get("ppa") is not None])
    first_downs=sum(1 for p in own if p.get("yardsGained",0) >= p.get("distance",999) and p.get("down",0) in (1,2,3,4))
    explosive=sum(1 for p in own if p.get("yardsGained",0) >= (20 if "Pass" in str(p.get("playType","")) else 10))
    return {
        "off_epa":avg(ppa), "pass_epa":pass_epa, "rush_epa":rush_epa,
        "first_down_rate":first_downs/len(own), "explosiveness":explosive/len(own),
        "plays":len(own)
    }


def build_standardized_features(raw: Dict[str,float]) -> Dict[str,float]:
    mapping={
        "defensive_weakness":"defensive_weakness","off_epa":"off_epa",
        "defensive_turnover_generation":"defensive_turnover_generation","pass_epa":"pass_epa",
        "opp_special_teams":"opp_special_teams","run_mote":"run_mote","pace":"pace",
        "special_teams":"special_teams","first_down_rate":"first_down_rate","pass_mote":"pass_mote",
        "explosiveness":"explosiveness","rush_epa":"rush_epa","opp_turnover_generation":"opp_turnover_generation"
    }
    out={}
    for dest, src in mapping.items(): out[dest]=zscore(src, raw[src])
    out["home_field"] = float(raw.get("home_field",0.0))
    out["weather_adjustment"] = float(raw.get("weather_adjustment",0.0))
    return out
