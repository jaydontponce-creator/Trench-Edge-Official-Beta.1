
from __future__ import annotations
from typing import Dict, Any, List

def grade_prediction(game:Dict[str,Any], final_home:float, final_away:float) -> Dict[str,Any]:
    p=game.get("prediction",{})
    dec=game.get("decision",{})
    market=game.get("market",{})
    result={
        "final_home":final_home,"final_away":final_away,
        "projected_home":p.get("home_points"),"projected_away":p.get("away_points"),
        "winner_correct":None,"wager_result":"NO BET","explanation":""
    }
    if p.get("home_points") is not None and p.get("away_points") is not None:
        pred_home=float(p["home_points"])>float(p["away_points"])
        act_home=float(final_home)>float(final_away)
        result["winner_correct"]=pred_home==act_home

    state=dec.get("state")
    if state in ("PASS","QUALIFIED"):
        market_type=str(dec.get("market") or "").lower()
        side=str(dec.get("side") or "")
        if market_type=="total" and market.get("total") is not None:
            actual=final_home+final_away; line=float(market["total"])
            if "under" in side.lower(): won=actual<line
            elif "over" in side.lower(): won=actual>line
            else: won=None
            result["wager_result"]="WIN" if won else ("LOSS" if won is False else "PUSH/UNKNOWN")
        elif market_type=="spread" and market.get("home_spread") is not None:
            hs=float(market["home_spread"]); home_cover=final_home+hs>final_away
            if game.get("home","").lower() in side.lower(): won=home_cover
            elif game.get("away","").lower() in side.lower(): won=not home_cover
            else: won=None
            result["wager_result"]="WIN" if won else ("LOSS" if won is False else "PUSH/UNKNOWN")

    drivers=(game.get("attribution") or {}).get("drivers") or []
    counters=(game.get("attribution") or {}).get("counterweights") or []
    winner_text="correctly identified the outright winner" if result["winner_correct"] else "missed the outright winner"
    driver_text=", ".join(d.get("name","") for d in drivers[:2] if d.get("name")) or "the core matchup profile"
    counter_text=", ".join(d.get("name","") for d in counters[:2] if d.get("name")) or "game variance"
    result["explanation"]=(
        f"TE {winner_text}. The pregame case was driven most by {driver_text}. "
        f"The result should be reviewed against {counter_text} to see whether those risks were correctly priced."
    )
    return result
