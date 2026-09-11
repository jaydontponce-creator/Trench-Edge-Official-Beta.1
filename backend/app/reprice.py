from __future__ import annotations
from typing import Any, Dict
from .calibration import assess as calibrate_market

def reprice_game(game: Dict[str,Any], market: Dict[str,Any] | None=None) -> None:
    """Recalculate model-vs-market edge, calibrated EV and decision.

    This is deliberately separate from the scoring engine so any legitimate
    score change (full model rebuild or cross-division adjustment) is repriced
    against the newest market using exactly one code path.
    """
    if market:
        game["market"] = {**(game.get("market") or {}), **market}

    market = game.get("market") or {}
    prediction = game.get("prediction") or {}
    margin = prediction.get("model_margin_home")
    total = prediction.get("model_total")
    spread = market.get("home_spread")
    market_total = market.get("total")

    spread_edge = (
        float(margin) + float(spread)
        if margin is not None and spread is not None else None
    )
    total_edge = (
        float(total) - float(market_total)
        if total is not None and market_total is not None else None
    )
    prediction["spread_edge_home"] = spread_edge
    prediction["total_edge_over"] = total_edge
    game["prediction"] = prediction

    options = []
    if spread_edge is not None:
        side = game.get("home") if spread_edge > 0 else game.get("away")
        line = spread if spread_edge > 0 else -float(spread)
        options.append(("spread", f"{side} {line:+g}", abs(spread_edge)))

    if total_edge is not None:
        side = ("Over" if total_edge > 0 else "Under") + f" {float(market_total):g}"
        options.append(("total", side, abs(total_edge)))

    if not options:
        return

    market_type, side, edge = max(options, key=lambda x: x[2])
    odds = -110.0
    calibrated = calibrate_market(
        market_type, edge, odds=odds, model_margin_home=margin
    )
    game["ev"] = calibrated

    dqs = (game.get("derived") or {}).get("dqs")
    enough_edge = edge >= 2.5
    enough_quality = dqs is not None and float(dqs) >= 60
    positive_ev = (calibrated.get("expected_value") or 0) > 0

    if enough_edge and enough_quality and positive_ev:
        state = "PASS"
        reasons = [
            "Current TE projection clears the live edge, data-quality and calibrated EV gates."
        ]
    elif enough_quality:
        state = "FAIL"
        reasons = [
            "TE has a current projection, but the current market does not clear all betting gates."
        ]
    else:
        state = "NEEDS_DATA"
        reasons = [
            "TE is publishing a provisional projection, but data quality is not high enough for a qualified wager."
        ]

    game["decision"] = {
        **(game.get("decision") or {}),
        "state": state,
        "market": market_type,
        "side": side,
        "edge": round(edge, 3),
        "reasons": reasons,
    }
