
from __future__ import annotations
from pathlib import Path
import json, math
from typing import Dict, Any, Optional

CONFIG = Path(__file__).resolve().parents[1] / "config" / "probability_calibration.json"

def _load():
    return json.loads(CONFIG.read_text())

def _interp_iso(x: float, xs, ys) -> float:
    x=float(x)
    if x <= xs[0]: return float(ys[0])
    if x >= xs[-1]: return float(ys[-1])
    for i in range(1,len(xs)):
        if x <= xs[i]:
            x0,x1=float(xs[i-1]),float(xs[i]); y0,y1=float(ys[i-1]),float(ys[i])
            if x1==x0: return y1
            w=(x-x0)/(x1-x0)
            return y0+w*(y1-y0)
    return float(ys[-1])

def spread_probability(abs_edge: float) -> float:
    c=_load()["spread"]
    return _interp_iso(abs_edge,c["x_thresholds"],c["y_thresholds"])

def total_probability(abs_edge: float) -> float:
    c=_load()["total"]
    return _interp_iso(abs_edge,c["x_thresholds"],c["y_thresholds"])

def home_win_probability(model_margin_home: float) -> float:
    c=_load()["moneyline"]
    z=float(c["intercept"])+float(c["coefficient_model_margin"])*float(model_margin_home)
    return 1.0/(1.0+math.exp(-z))

def american_break_even(odds: float) -> float:
    odds=float(odds)
    return (-odds)/((-odds)+100.0) if odds < 0 else 100.0/(odds+100.0)

def profit_per_unit(odds: float) -> float:
    odds=float(odds)
    return 100.0/abs(odds) if odds < 0 else odds/100.0

def expected_value(probability: float, odds: float) -> float:
    p=float(probability); profit=profit_per_unit(odds)
    return p*profit-(1.0-p)

def assess(market: str, edge: float, odds: float=-110.0, model_margin_home: Optional[float]=None) -> Dict[str,Any]:
    if market=="spread":
        p=spread_probability(abs(edge))
    elif market=="total":
        p=total_probability(abs(edge))
    elif market=="moneyline":
        if model_margin_home is None: raise ValueError("model_margin_home required for moneyline")
        p=home_win_probability(model_margin_home)
    else:
        raise ValueError(f"Unknown market {market}")
    be=american_break_even(odds)
    ev=expected_value(p,odds)
    return {
        "probability":round(p,6),
        "break_even_probability":round(be,6),
        "expected_value":round(ev,6),
        "source":_load()["version"],
        "calibrated":True,
        "odds_american":odds
    }
