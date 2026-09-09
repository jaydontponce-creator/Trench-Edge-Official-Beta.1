
from __future__ import annotations
from typing import Dict, Any, List, Iterable, Tuple
from collections import defaultdict
from .standardize import standardize_slate

# Exact identities recovered from 15,544 archived TE V2 rows.
RUN_OTE_WEIGHTS = {
    "off_run_line": 2.50,
    "off_run_stuffavoid": 1.25,
    "off_run_power": 1.25,
}
RUN_DTE_WEIGHTS = {
    "def_run_line": 2.50,
    "def_run_stuff": 1.25,
    "def_run_power": 1.25,
}
PASS_OTE_WEIGHTS = {
    "off_pass_protect": 3.35,
    "off_havoc_avoid": 1.65,
}
PASS_DTE_WEIGHTS = {
    "def_pass_rush": 3.35,
    "def_havoc": 1.65,
}

MOTE_STANDARDIZE_FIELDS = [
    "off_run_line","off_run_stuffavoid","off_run_power",
    "off_pass_protect","off_havoc_avoid",
    "def_run_line","def_run_stuff","def_run_power",
    "def_pass_rush","def_havoc",
]

def reliability(pregame_games: int) -> float:
    """Exact recovered reliability schedule: n / (n + 3)."""
    n = max(0, int(pregame_games))
    return n / (n + 3.0)

def offseason_prior(previous_team_mean: float | None, previous_global_mean: float) -> float:
    """Recovered offseason regression: 50% prior-season team mean + 50% prior-season global mean."""
    if previous_team_mean is None:
        return float(previous_global_mean)
    return 0.5 * float(previous_team_mean) + 0.5 * float(previous_global_mean)

def inseason_prior(season_baseline: float, current_team_mean: float | None, pregame_games: int) -> float:
    """Recovered within-season shrinkage toward the preseason baseline."""
    r = reliability(pregame_games)
    if current_team_mean is None or pregame_games <= 0:
        return float(season_baseline)
    return r * float(current_team_mean) + (1.0 - r) * float(season_baseline)

def _weighted(row: Dict[str, Any], weights: Dict[str, float]) -> float:
    total = 0.0
    for field, w in weights.items():
        zname = "z_" + field
        if row.get(zname) is None:
            raise ValueError(f"Missing standardized MOTE field: {zname}")
        total += w * float(row[zname])
    return total

def calculate_ote_dte(row: Dict[str, Any]) -> Dict[str, float]:
    return {
        "RunOTE": _weighted(row, RUN_OTE_WEIGHTS),
        "RunDTE": _weighted(row, RUN_DTE_WEIGHTS),
        "PassOTE": _weighted(row, PASS_OTE_WEIGHTS),
        "PassDTE": _weighted(row, PASS_DTE_WEIGHTS),
    }

def calculate_matchup_mote(team_row: Dict[str, Any], opponent_row: Dict[str, Any]) -> Dict[str, float]:
    t = calculate_ote_dte(team_row)
    o = calculate_ote_dte(opponent_row)
    return {
        **t,
        "OppRunDTE": o["RunDTE"],
        "OppPassDTE": o["PassDTE"],
        "RunMOTE": t["RunOTE"] - o["RunDTE"],
        "PassMOTE": t["PassOTE"] - o["PassDTE"],
    }

def build_mote_slate(rows: List[Dict[str, Any]], team_key: str = "team", opponent_key: str = "opponent"):
    """Cross-sectionally standardize the slate, calculate OTE/DTE, and attach opponent-adjusted MOTE."""
    diag = standardize_slate(rows, MOTE_STANDARDIZE_FIELDS)
    by_team = {r[team_key]: r for r in rows}
    for row in rows:
        opp = by_team.get(row[opponent_key])
        if opp is None:
            row["mote_ready"] = False
            row["mote_error"] = f"Opponent row missing: {row.get(opponent_key)}"
            continue
        row.update(calculate_matchup_mote(row, opp))
        row["mote_ready"] = True
    return diag
