
from __future__ import annotations
from typing import Dict, Any, List, Iterable
from collections import defaultdict
from .mote import offseason_prior, inseason_prior, reliability

RAW_PRIOR_FIELDS = [
    "off_run_line","off_run_stuffavoid","off_run_power",
    "off_pass_protect","off_havoc_avoid",
    "def_run_line","def_run_stuff","def_run_power",
    "def_pass_rush","def_havoc",
    "off_epa","off_rush_epa","off_pass_epa","off_firstdown","off_explosive","off_pace",
]

def _mean(vals):
    vals=[float(v) for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None

def season_means(game_rows: List[Dict[str, Any]], fields=RAW_PRIOR_FIELDS):
    team_values=defaultdict(lambda: defaultdict(list))
    global_values=defaultdict(list)
    for r in game_rows:
        team=r.get("team")
        if not team:
            continue
        for f in fields:
            v=r.get(f)
            if v is not None:
                team_values[team][f].append(v)
                global_values[f].append(v)
    team_means={t:{f:_mean(vs) for f,vs in fs.items()} for t,fs in team_values.items()}
    global_means={f:_mean(vs) for f,vs in global_values.items()}
    return team_means, global_means

def build_pregame_rows(
    slate_rows: List[Dict[str, Any]],
    previous_season_games: List[Dict[str, Any]],
    current_season_completed_games: List[Dict[str, Any]],
    fields=RAW_PRIOR_FIELDS,
):
    """Build the exact recovered smoothed pregame feature state.

    preseason baseline = .5 previous team mean + .5 previous global mean
    reliability = n/(n+3)
    pregame feature = reliability * current-season team mean + (1-reliability) * preseason baseline
    """
    prev_team, prev_global = season_means(previous_season_games, fields)
    cur_team, _ = season_means(current_season_completed_games, fields)
    cur_counts=defaultdict(int)
    seen_games=defaultdict(set)
    for r in current_season_completed_games:
        t=r.get("team"); gid=r.get("game_id")
        if t and gid is not None:
            seen_games[t].add(str(gid))
    for t,s in seen_games.items():
        cur_counts[t]=len(s)

    out=[]
    for row in slate_rows:
        r=dict(row)
        team=r["team"]
        n=cur_counts.get(team,0)
        r["pregame_games"]=n
        r["Reliability"]=reliability(n)
        for f in fields:
            gprev=prev_global.get(f)
            if gprev is None:
                r[f]=None
                continue
            baseline=offseason_prior((prev_team.get(team) or {}).get(f),gprev)
            current=(cur_team.get(team) or {}).get(f)
            r[f]=inseason_prior(baseline,current,n)
            r[f+"_season_baseline"]=baseline
            r[f+"_current_mean"]=current
        out.append(r)
    return out
