from __future__ import annotations
from typing import Dict, Any

# Backend TeamFeatures field names. These match schemas.py exactly.
TEAM_FEATURE_FIELDS = [
    "defensive_weakness",
    "off_epa",
    "defensive_turnover_generation",
    "pass_epa",
    "opp_special_teams",
    "run_mote",
    "pace",
    "special_teams",
    "first_down_rate",
    "pass_mote",
    "explosiveness",
    "rush_epa",
    "opp_turnover_generation",
]

RAW_DISPLAY_DEFAULTS = {
    "off_epa": 0.0,
    "off_pass_epa": 0.0,
    "off_rush_epa": 0.0,
    "first_down_rate": 0.0,
    "explosiveness": 0.0,
    "pace": 0.0,
    "run_mote": 0.0,
    "pass_mote": 0.0,
    "special_teams": 0.0,
    "turnover_generation": 0.0,
    "weather_adjustment": 0.0,
}

# Accept both canonical V4 names and backend snake_case names.
ALIASES = {
    "defensive_weakness": ("defensive_weakness","DefensiveWeakness"),
    "off_epa": ("off_epa","OffEPA"),
    "defensive_turnover_generation": ("defensive_turnover_generation","DefensiveTurnoverGeneration"),
    "pass_epa": ("pass_epa","PassEPA"),
    "opp_special_teams": ("opp_special_teams","OppSpecialTeams"),
    "run_mote": ("run_mote","RunMOTE"),
    "pace": ("pace","Pace"),
    "special_teams": ("special_teams","SpecialTeams"),
    "first_down_rate": ("first_down_rate","FirstDownRate"),
    "pass_mote": ("pass_mote","PassMOTE"),
    "explosiveness": ("explosiveness","Explosiveness"),
    "rush_epa": ("rush_epa","RushEPA"),
    "opp_turnover_generation": ("opp_turnover_generation","OppTurnoverGeneration"),
    "weather_adjustment": ("weather_adjustment","WeatherAdjustment"),
}

def _first(features: Dict[str,Any], keys):
    for k in keys:
        if k in features and features[k] is not None:
            return features[k]
    return None

def complete_feature_vector(features: Dict[str,Any] | None, home: bool):
    """Return a schema-valid TeamFeatures dict plus provenance.

    Missing standardized inputs are imputed to 0.0, which is the population
    mean in standardized space. Every imputed field is labeled in provenance.
    """
    features = dict(features or {})
    out: Dict[str,float] = {}
    provenance: Dict[str,str] = {}

    for name in TEAM_FEATURE_FIELDS:
        v = _first(features, ALIASES[name])
        if v is None:
            out[name] = 0.0
            provenance[name] = "population_mean_imputation"
        else:
            out[name] = float(v)
            provenance[name] = "observed_or_prior"

    out["home_field"] = 1.0 if home else -1.0
    provenance["home_field"] = "schedule"

    weather = _first(features, ALIASES["weather_adjustment"])
    out["weather_adjustment"] = float(weather or 0.0)
    provenance["weather_adjustment"] = (
        "observed_or_neutral" if weather is not None
        else "neutral_pending_weather"
    )

    return out, provenance

def completeness(provenance: Dict[str,str]) -> float:
    if not provenance:
        return 0.0
    trusted = sum(
        1 for v in provenance.values()
        if v in ("observed_or_prior","schedule","observed_or_neutral")
    )
    return round(100.0 * trusted / len(provenance), 1)

def display_statistics(existing: Dict[str,Any] | None = None):
    existing = existing or {}
    out = {}
    for field, default in RAW_DISPLAY_DEFAULTS.items():
        v = existing.get(field)
        if v is None:
            out[field] = {
                "value": default,
                "source": "estimated_population_baseline",
                "estimated": True,
            }
        else:
            out[field] = {
                "value": float(v),
                "source": "model_input",
                "estimated": False,
            }
    return out
