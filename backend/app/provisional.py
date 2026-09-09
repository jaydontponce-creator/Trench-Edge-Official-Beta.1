
from __future__ import annotations
from typing import Dict, Any, Iterable
import math

# These are transparent fallback conventions, not observed statistics.
# Standardized V4 inputs use zero as the population-average fallback.
V4_STANDARDIZED_FIELDS = [
    "DefensiveWeakness","OffEPA","DefensiveTurnoverGeneration","PassEPA",
    "OppSpecialTeams","RunMOTE","Pace","SpecialTeams","FirstDownRate",
    "PassMOTE","Explosiveness","RushEPA","OppTurnoverGeneration"
]

RAW_DISPLAY_DEFAULTS = {
    "off_epa": 0.0, "off_pass_epa": 0.0, "off_rush_epa": 0.0,
    "first_down_rate": 0.0, "explosiveness": 0.0, "pace": 0.0,
    "run_mote": 0.0, "pass_mote": 0.0, "special_teams": 0.0,
    "turnover_generation": 0.0, "weather_adjustment": 0.0,
}

def complete_feature_vector(features: Dict[str,Any] | None, home: bool) -> tuple[Dict[str,float],Dict[str,str]]:
    """Return a complete V4 feature vector plus provenance per field.

    Missing standardized continuous inputs are filled with 0.0, which represents
    the reference/population mean after standardization. HomeField is always known.
    """
    features = dict(features or {})
    out: Dict[str,float] = {}
    provenance: Dict[str,str] = {}
    for name in V4_STANDARDIZED_FIELDS:
        v = features.get(name)
        if v is None:
            out[name] = 0.0
            provenance[name] = "population_mean_imputation"
        else:
            out[name] = float(v)
            provenance[name] = "observed_or_prior"
    out["HomeField"] = 1.0 if home else -1.0
    provenance["HomeField"] = "schedule"
    out["WeatherAdjustment"] = float(features.get("WeatherAdjustment") or 0.0)
    provenance["WeatherAdjustment"] = "observed_or_neutral" if features.get("WeatherAdjustment") is not None else "neutral_pending_weather"
    return out, provenance

def completeness(provenance: Dict[str,str]) -> float:
    if not provenance: return 0.0
    trusted = sum(1 for v in provenance.values() if v in ("observed_or_prior","schedule","observed_or_neutral"))
    return round(100.0*trusted/len(provenance),1)

def display_statistics(existing: Dict[str,Any] | None = None) -> Dict[str,Dict[str,Any]]:
    """Never leave public statistical columns blank.

    Values not supported by live/archived inputs are explicitly tagged as estimates
    rather than masquerading as measured statistics.
    """
    existing = existing or {}
    out={}
    for field, default in RAW_DISPLAY_DEFAULTS.items():
        v=existing.get(field)
        if v is None:
            out[field]={"value":default,"source":"estimated_population_baseline","estimated":True}
        else:
            out[field]={"value":float(v),"source":"model_input","estimated":False}
    return out
