
from __future__ import annotations
from pathlib import Path
import json, math
from typing import Dict, Any

CONFIG = Path(__file__).resolve().parents[1] / "config" / "empirical_risk_models.json"

def _load():
    return json.loads(CONFIG.read_text())

def _predict(section: str, inputs: Dict[str,float]) -> float:
    spec=_load()[section]["model"]
    vals=[]
    for i,name in enumerate(spec["features"]):
        v=inputs.get(name)
        if v is None: v=spec["imputer_medians"][i]
        z=(float(v)-float(spec["scaler_mean"][i]))/float(spec["scaler_scale"][i])
        vals.append(z)
    linear=float(spec["intercept"])+sum(float(c)*v for c,v in zip(spec["coefficients"],vals))
    p=1.0/(1.0+math.exp(-linear))
    return round(100.0*p,3)

def calculate_dfr(inputs: Dict[str,float]) -> float:
    return _predict("dfr",inputs)

def calculate_fpse(inputs: Dict[str,float]) -> float:
    return _predict("fpse",inputs)

def metadata() -> Dict[str,Any]:
    a=_load()
    return {"version":a["version"],"status":a["status"],"versioning_note":a["versioning_note"]}
