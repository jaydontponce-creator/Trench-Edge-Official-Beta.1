
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json
import re
import threading
import time

from .providers.cfbd import CFBDProvider

DATA = Path(__file__).resolve().parents[1] / "data"
_lock = threading.Lock()
_cache = {"at": 0.0, "week": None, "payload": None}


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _first(game: Dict[str, Any], *names: str, default=None):
    for name in names:
        if game.get(name) is not None:
            return game.get(name)
    return default


def _load_schedule(week: int) -> list[Dict[str, Any]]:
    candidates = [
        DATA / f"week{week}_full_product_demo.json",
        DATA / f"week{week}_complete_schedule_fallback.json",
    ]
    if week == 2:
        candidates += [
            DATA / "week2_full_product_demo.json",
            DATA / "week2_complete_schedule_fallback.json",
        ]

    for path in candidates:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload.get("games", [])
            if isinstance(payload, list):
                return payload
    return []


def _shell_card(game: Dict[str, Any]) -> Dict[str, Any]:
    away = _first(game, "away", "awayTeam", "away_team")
    home = _first(game, "home", "homeTeam", "home_team")
    return {
        "id": str(_first(game, "id", default=f"{away}-{home}")),
        "away": away,
        "home": home,
        "away_score": None,
        "home_score": None,
        "kickoff": _first(game, "kickoff", "startDate", "start_date"),
        "venue": _first(game, "venue", "venueName"),
        "venue_city": _first(game, "venue_city", "venueCity", "city"),
        "venue_state": _first(game, "venue_state", "venueState", "state"),
        "completed": False,
        "status": "scheduled",
        "period": None,
        "clock": None,
        "detail": "Scheduled",
        "live": False,
        "classification": _first(game, "classification", default="NCAA"),
        "branding": _first(game, "branding", default={}),
    }


def _live_card(game: Dict[str, Any]) -> Dict[str, Any]:
    away = _first(game, "awayTeam", "away_team", "away")
    home = _first(game, "homeTeam", "home_team", "home")
    completed = bool(_first(game, "completed", default=False))
    away_score = _first(game, "awayPoints", "away_points", "awayScore")
    home_score = _first(game, "homePoints", "home_points", "homeScore")
    status = _first(game, "status", "gameStatus", "state", default="scheduled")
    period = _first(game, "period", "currentPeriod", "quarter")
    clock = _first(game, "clock", "currentClock", "displayClock")
    detail = _first(game, "statusDetail", "detail")

    return {
        "id": str(_first(game, "id", default=f"{away}-{home}")),
        "away": away,
        "home": home,
        "away_score": away_score,
        "home_score": home_score,
        "kickoff": _first(game, "startDate", "start_date", "kickoff"),
        "venue": _first(game, "venue", "venueName"),
        "venue_city": _first(game, "venue_city", "venueCity", "city"),
        "venue_state": _first(game, "venue_state", "venueState", "state"),
        "completed": completed,
        "status": status,
        "period": period,
        "clock": clock,
        "detail": detail,
        "live": (not completed and (away_score is not None or home_score is not None)),
    }


def scoreboard(
    week: int = 2,
    year: int = 2026,
    max_age_seconds: int = 5,
    force: bool = False,
) -> Dict[str, Any]:
    """Return the complete weekly scoreboard.

    The full local schedule is always the base so games appear before kickoff.
    Live CFBD scores/status are overlaid whenever the upstream provider returns them.
    """
    now = time.time()

    with _lock:
        if (
            not force
            and _cache["payload"] is not None
            and _cache["week"] == week
            and now - _cache["at"] < max_age_seconds
        ):
            result = dict(_cache["payload"])
            result["cache_age_seconds"] = round(now - _cache["at"], 2)
            return result

        base_games = [_shell_card(g) for g in _load_schedule(week)]
        by_key = {
            (_norm(g.get("away")), _norm(g.get("home"))): g
            for g in base_games
            if g.get("away") and g.get("home")
        }

        provider = CFBDProvider()
        provider_error = None

        if provider.ready:
            try:
                rows = []
                for classification in ("fbs", "fcs"):
                    try:
                        rows.extend(
                            provider.games(
                                year,
                                week,
                                classification=classification,
                            )
                        )
                    except Exception:
                        pass

                for raw in rows:
                    live = _live_card(raw)
                    key = (_norm(live.get("away")), _norm(live.get("home")))
                    current = by_key.get(key, {})

                    if current:
                        for field in (
                            "kickoff",
                            "venue",
                            "venue_city",
                            "venue_state",
                            "classification",
                            "branding",
                        ):
                            if live.get(field) is None and current.get(field) is not None:
                                live[field] = current[field]

                    by_key[key] = {**current, **live}

            except Exception as exc:
                provider_error = str(exc)

        games = list(by_key.values())

        payload = {
            "games": games,
            "week": week,
            "season": year,
            "refreshed_epoch": now,
            "refresh_interval_seconds": max_age_seconds,
            "provider": "CFBD + complete local schedule",
            "provider_ready": provider.ready,
            "error": provider_error,
            "accuracy_note": (
                "All scheduled games remain visible. Scores and game state update "
                "as quickly as the upstream provider publishes them."
            ),
        }

        _cache.update({"at": now, "week": week, "payload": payload})
        return payload
