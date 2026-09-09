
from __future__ import annotations
from typing import Dict, Any, List, Tuple
from collections import defaultdict

def _g(d, *path, default=None):
    cur=d
    for key in path:
        if not isinstance(cur,dict):
            return default
        cur=cur.get(key)
    return default if cur is None else cur

def advanced_to_partial_raw(row: Dict[str,Any]) -> Dict[str,Any]:
    """Map CFBD advanced-game output to the recovered historical TE feature directions.

    Pass-protection/pass-rush sack rates are attached separately from play-by-play.
    """
    off=row.get("offense") or {}
    deff=row.get("defense") or {}
    return {
        "game_id": str(row.get("gameId")),
        "season": row.get("season"),
        "week": row.get("week"),
        "team": row.get("team"),
        "opponent": row.get("opponent"),
        "off_run_line": off.get("lineYards"),
        "off_run_stuffavoid": None if off.get("stuffRate") is None else -float(off["stuffRate"]),
        "off_run_power": off.get("powerSuccess"),
        "def_run_line": None if deff.get("lineYards") is None else -float(deff["lineYards"]),
        "def_run_stuff": deff.get("stuffRate"),
        "def_run_power": None if deff.get("powerSuccess") is None else -float(deff["powerSuccess"]),
        "off_epa": off.get("ppa"),
        "off_rush_epa": _g(off,"rushingPlays","ppa"),
        "off_pass_epa": _g(off,"passingPlays","ppa"),
        "off_explosive_cfbd": off.get("explosiveness"),
        "off_pace": off.get("plays"),
    }

def merge_havoc(partials: List[Dict[str,Any]], havoc_rows: List[Dict[str,Any]]) -> None:
    by={(str(r.get("gameId")),r.get("team")):r for r in havoc_rows}
    for p in partials:
        h=by.get((str(p.get("game_id")),p.get("team")))
        if not h: continue
        off=h.get("offense") or {}; deff=h.get("defense") or {}
        if off.get("havocRate") is not None:
            p["off_havoc_avoid"]=-float(off["havocRate"])
        if deff.get("havocRate") is not None:
            p["def_havoc"]=float(deff["havocRate"])

def attach_sack_rates(partials: List[Dict[str,Any]], plays: List[Dict[str,Any]]) -> None:
    """Derive offensive sack-allowed and defensive sack-created rates from play-by-play.

    Uses pass-attempt-like plays as denominator and play-type text containing 'sack' as the sack event.
    This keeps the sack-rate calculation transparent and provider-independent.
    """
    acc=defaultdict(lambda: {"off_pass_plays":0,"off_sacks_allowed":0,"def_pass_plays":0,"def_sacks":0})
    for p in plays:
        off=p.get("offense"); deff=p.get("defense"); pt=str(p.get("playType") or "").lower()
        if not off or not deff: continue
        is_pass=("pass" in pt) or ("sack" in pt)
        if not is_pass: continue
        keyo=(str(p.get("gameId")),off); keyd=(str(p.get("gameId")),deff)
        acc[keyo]["off_pass_plays"]+=1; acc[keyd]["def_pass_plays"]+=1
        if "sack" in pt:
            acc[keyo]["off_sacks_allowed"]+=1; acc[keyd]["def_sacks"]+=1
    for r in partials:
        a=acc.get((str(r.get("game_id")),r.get("team")))
        if not a: continue
        if a["off_pass_plays"]:
            r["off_pass_protect"]=-(a["off_sacks_allowed"]/a["off_pass_plays"])
        if a["def_pass_plays"]:
            r["def_pass_rush"]=a["def_sacks"]/a["def_pass_plays"]
