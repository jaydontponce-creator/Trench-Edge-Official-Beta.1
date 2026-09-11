from __future__ import annotations
from typing import Any, Dict, Mapping
import math

# Historical FBS-vs-FCS mean margin is used ONLY when a cross-division SRS
# comparison is unavailable. It is not used for FBS-vs-FBS or FCS-vs-FCS games.
FALLBACK_FBS_OVER_FCS_MARGIN = 28.8
HOME_FIELD_POINTS = 2.0
SRS_BLEND_WEIGHT = 0.70
FALLBACK_BLEND_WEIGHT = 0.60

def _cls(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    if "fbs" in s:
        return "fbs"
    if "fcs" in s:
        return "fcs"
    return None

def rating_index(rows) -> Dict[str, Dict[str,Any]]:
    out = {}
    for row in rows or []:
        team = row.get("team")
        if not team:
            continue
        rating = row.get("rating")
        try:
            rating = float(rating) if rating is not None else None
        except (TypeError, ValueError):
            rating = None
        out[team] = {
            "rating": rating,
            "classification": _cls(row.get("classification") or row.get("division")),
            "ranking": row.get("ranking"),
        }
    return out

def classification_for(
    team: str,
    ratings: Mapping[str, Mapping[str,Any]],
    explicit: Any=None,
) -> str | None:
    return _cls(explicit) or _cls((ratings.get(team) or {}).get("classification"))

def _finite(value):
    try:
        x = float(value)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None

def apply_cross_division_adjustment(
    game: Dict[str,Any],
    ratings: Mapping[str, Mapping[str,Any]],
) -> Dict[str,Any]:
    """Normalize an FBS/FCS matchup after the locked V4.1 equation.

    The canonical V4.1 equation is left untouched.

    For cross-division games only:
      1. Prefer CFBD expanded SRS, which contains both FBS and FCS teams.
      2. Blend the raw TE margin with the neutral-field SRS differential plus
         a small home-field term.
      3. If SRS is unavailable, use a transparent historical class prior.
      4. Preserve the raw TE projected total, moving points between teams to
         match the adjusted margin.

    This prevents missing/neutral FCS features from making an FCS team look
    like an average FBS team while still preserving TE's scoring signal.
    """
    home = game.get("home")
    away = game.get("away")
    if not home or not away:
        return game

    meta = game.setdefault("provider_meta", {})
    classes = meta.setdefault("classifications", {})

    hcls = classification_for(
        home, ratings,
        classes.get("home") or meta.get("home_classification")
    )
    acls = classification_for(
        away, ratings,
        classes.get("away") or meta.get("away_classification")
    )
    classes["home"] = hcls
    classes["away"] = acls

    if {hcls, acls} != {"fbs", "fcs"}:
        meta["cross_division"] = {
            "applied": False,
            "home_classification": hcls,
            "away_classification": acls,
        }
        return game

    p = game.get("prediction") or {}
    raw_margin = _finite(p.get("model_margin_home"))
    model_total = _finite(p.get("model_total"))
    if raw_margin is None or model_total is None:
        return game

    hr = _finite((ratings.get(home) or {}).get("rating"))
    ar = _finite((ratings.get(away) or {}).get("rating"))

    if hr is not None and ar is not None:
        target_margin = (hr - ar) + HOME_FIELD_POINTS
        weight = SRS_BLEND_WEIGHT
        source = "CFBD expanded SRS cross-division normalization"
    else:
        # Home-margin sign. The class prior is deliberately weaker than the
        # SRS path and exists only so missing FCS analytics cannot collapse to 0.
        sign = 1.0 if hcls == "fbs" else -1.0
        target_margin = sign * FALLBACK_FBS_OVER_FCS_MARGIN + HOME_FIELD_POINTS
        weight = FALLBACK_BLEND_WEIGHT
        source = "historical FBS/FCS class prior fallback"

    adjusted_margin = (1.0 - weight) * raw_margin + weight * target_margin

    # Preserve TE's total while altering only the allocation between teams.
    home_points = max(0.0, (model_total + adjusted_margin) / 2.0)
    away_points = max(0.0, (model_total - adjusted_margin) / 2.0)

    p["raw_model_margin_home"] = raw_margin
    p["raw_home_points"] = p.get("home_points")
    p["raw_away_points"] = p.get("away_points")
    p["model_margin_home"] = round(adjusted_margin, 6)
    p["home_points"] = round(home_points, 6)
    p["away_points"] = round(away_points, 6)
    game["prediction"] = p

    meta["cross_division"] = {
        "applied": True,
        "home_classification": hcls,
        "away_classification": acls,
        "method": source,
        "raw_te_margin_home": round(raw_margin, 4),
        "normalization_target_margin_home": round(target_margin, 4),
        "blend_weight": weight,
        "adjusted_margin_home": round(adjusted_margin, 4),
        "home_srs": hr,
        "away_srs": ar,
    }
    return game
