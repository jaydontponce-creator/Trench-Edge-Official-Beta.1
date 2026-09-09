
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Iterable, List
import json, math, statistics

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "standardization.json"

class StandardizationUnavailable(RuntimeError):
    pass

# Recovered from te_v2_predictions.csv:
# all archived z_* fields were standardized cross-sectionally inside the same season/week
# using the population mean and population standard deviation (ddof=0).
RECOVERED_METHOD = "season_week_cross_sectional_population_zscore"

def cross_sectional_zscore(values: List[float]) -> List[float]:
    vals = [float(v) for v in values]
    if not vals:
        return []
    mu = sum(vals) / len(vals)
    var = sum((v - mu) ** 2 for v in vals) / len(vals)
    sd = math.sqrt(var)
    if sd == 0:
        return [0.0 for _ in vals]
    return [(v - mu) / sd for v in vals]

def standardize_slate(rows: List[Dict[str, Any]], fields: Iterable[str], *, prefix: str = "z_") -> Dict[str, Any]:
    """Standardize model rows across the current season/week slate.

    This reproduces the archived TE V2 z-score method exactly: each feature is centered and scaled
    across the rows present in that season/week, using population standard deviation.
    """
    diagnostics = {"method": RECOVERED_METHOD, "features": {}}
    for field in fields:
        usable = [(i, float(r[field])) for i, r in enumerate(rows) if r.get(field) is not None]
        if not usable:
            continue
        vals = [v for _, v in usable]
        mu = sum(vals) / len(vals)
        sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / len(vals))
        diagnostics["features"][field] = {"mean": mu, "std": sd, "n": len(vals)}
        for (idx, raw), z in zip(usable, cross_sectional_zscore(vals)):
            rows[idx][prefix + field] = z
    return diagnostics

# Retain fixed-config support for any future authenticated scaler artifact.
def load_constants() -> Dict[str, Dict[str, float]]:
    if not CONFIG_PATH.exists():
        raise StandardizationUnavailable("standardization.json missing")
    data = json.loads(CONFIG_PATH.read_text())
    constants = data.get("features", data)
    usable = {}
    for name, spec in constants.items():
        if isinstance(spec, dict) and spec.get("mean") is not None and spec.get("std") not in (None, 0):
            usable[name] = {"mean": float(spec["mean"]), "std": float(spec["std"])}
    return usable

def zscore(name: str, raw_value: float) -> float:
    constants = load_constants()
    if name not in constants:
        raise StandardizationUnavailable(
            f"No authenticated fixed mean/std for '{name}'. "
            "Use standardize_slate() for the recovered season-week cross-sectional TE lineage method."
        )
    s = constants[name]
    return (float(raw_value) - s["mean"]) / s["std"]
