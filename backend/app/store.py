from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
INPUTS = DATA_DIR / "week2_inputs.json"
OUTPUTS = DATA_DIR / "week2_outputs.json"


def load_inputs() -> List[Dict[str, Any]]:
    if not INPUTS.exists(): return []
    return json.loads(INPUTS.read_text(encoding="utf-8"))

def save_inputs(rows: List[Dict[str, Any]]):
    INPUTS.write_text(json.dumps(rows, indent=2), encoding="utf-8")

def load_outputs() -> List[Dict[str, Any]]:
    if not OUTPUTS.exists(): return []
    return json.loads(OUTPUTS.read_text(encoding="utf-8"))

def save_outputs(rows: List[Dict[str, Any]]):
    OUTPUTS.write_text(json.dumps(rows, indent=2), encoding="utf-8")
