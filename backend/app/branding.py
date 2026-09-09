
from __future__ import annotations
from typing import Dict, Any
import re

FALLBACK_COLORS = {
    "Oklahoma":("#841617","#FDF9D8"), "Michigan":("#00274C","#FFCB05"),
    "Alabama":("#9E1B32","#FFFFFF"), "Kentucky":("#0033A0","#FFFFFF"),
    "Tennessee":("#FF8200","#FFFFFF"), "Georgia Tech":("#B3A369","#003057"),
    "Ohio State":("#BB0000","#666666"), "Texas":("#BF5700","#FFFFFF"),
    "Iowa State":("#C8102E","#F1BE48"), "Iowa":("#FFCD00","#000000"),
    "UTSA":("#0C2340","#F15A22"), "Texas State":("#501214","#B9975B"),
    "UCF":("#BA9B37","#000000"), "Pittsburgh":("#003594","#FFB81C"),
    "Missouri":("#F1B82D","#000000"), "Kansas":("#0051BA","#E8000D"),
    "Oregon":("#154733","#FEE123"), "Oklahoma State":("#FF7300","#000000"),
    "Texas A&M":("#500000","#FFFFFF"), "Arizona State":("#8C1D40","#FFC627"),
    "USC":("#990000","#FFC72C"), "Notre Dame":("#0C2340","#C99700"),
    "Georgia":("#BA0C2F","#000000"), "Miami (FL)":("#F47321","#005030"),
    "Louisville":("#AD0000","#000000"), "BYU":("#002E5D","#FFFFFF"),
    "LSU":("#461D7C","#FDD023"), "Clemson":("#F56600","#522D80"),
    "Utah":("#CC0000","#000000"), "Boise State":("#0033A0","#D64309"),
}

def _clean_hex(v, default):
    if not v: return default
    s=str(v).strip()
    if not s.startswith("#"): s="#"+s
    return s if re.fullmatch(r"#[0-9A-Fa-f]{6}",s) else default

def fallback_colors(team:str):
    return FALLBACK_COLORS.get(team,("#476582","#AFC5D8"))

def from_cfbd(team_meta:Dict[str,Any]|None, team_name:str):
    p,a=fallback_colors(team_name)
    if not team_meta: return {"primary":p,"secondary":a,"source":"fallback"}
    return {
        "primary":_clean_hex(team_meta.get("color"),p),
        "secondary":_clean_hex(team_meta.get("altColor"),a),
        "source":"CFBD team metadata"
    }
