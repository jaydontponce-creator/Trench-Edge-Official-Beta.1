from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, List

DQS_WEIGHTS = {
    "ol_personnel": 0.15,
    "dl_personnel": 0.15,
    "player_history": 0.10,
    "transfers_new_starters": 0.10,
    "continuity": 0.15,
    "injuries_availability": 0.10,
    "scheme_coaching": 0.05,
    "advanced_efficiency": 0.10,
    "opponent_strength_adjustment": 0.10,
}

OCRS_WEIGHTS = {
    "run_mote_disadvantage": 0.15,
    "pass_mote_disadvantage": 0.15,
    "qb_pressure_vulnerability": 0.12,
    "overall_efficiency_mismatch": 0.12,
    "explosiveness_mismatch": 0.08,
    "finishing_drive_mismatch": 0.10,
    "personnel_continuity_uncertainty": 0.05,
    "game_script_vulnerability": 0.07,
    "dfr": 0.10,
    "fpse": 0.06,
}


def _validate_0_100(values: Dict[str, float], required: Dict[str, float]) -> None:
    missing = [k for k in required if k not in values or values[k] is None]
    if missing:
        raise ValueError(f"Missing required components: {', '.join(missing)}")
    bad = {k: v for k, v in values.items() if k in required and not (0 <= float(v) <= 100)}
    if bad:
        raise ValueError(f"Components must be 0-100: {bad}")


def calculate_dqs(components: Dict[str, float]) -> Tuple[float, Dict[str, float]]:
    """Locked TE V4.1 DQS weighted formula."""
    _validate_0_100(components, DQS_WEIGHTS)
    contrib = {k: float(components[k]) * w for k, w in DQS_WEIGHTS.items()}
    score = sum(contrib.values())
    return round(score, 3), {k: round(v, 3) for k, v in contrib.items()}


def calculate_ocrs(components: Dict[str, float]) -> Tuple[float, Dict[str, Any]]:
    """Locked TE V4.1 OCRS weighted overlay and nonlinear multiplier rule."""
    _validate_0_100(components, OCRS_WEIGHTS)
    contrib = {k: float(components[k]) * w for k, w in OCRS_WEIGHTS.items()}
    raw = sum(contrib.values())
    major_count = sum(1 for k in OCRS_WEIGHTS if float(components[k]) >= 75)
    multiplier = 1.18 if major_count >= 6 else 1.10 if major_count >= 4 else 1.0
    final = min(100.0, raw * multiplier)
    if final <= 24:
        band = "Low"
    elif final <= 44:
        band = "Moderate"
    elif final <= 64:
        band = "Elevated"
    elif final <= 79:
        band = "High"
    else:
        band = "Severe"
    return round(final, 3), {
        "raw": round(raw, 3),
        "multiplier": multiplier,
        "major_components_ge_75": major_count,
        "band": band,
        "weighted_contributions": {k: round(v, 3) for k, v in contrib.items()},
    }
