from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .schemas import MatchupRequest, MatchupResponse
from .engine import calculate_matchup
from .refresh import refresh_week as run_refresh_week
from .store import load_inputs, load_outputs, save_outputs
from .risk import DQS_WEIGHTS, OCRS_WEIGHTS
from .empirical_risk import metadata as empirical_risk_metadata
from .results import grade_prediction
from .board_service import complete_week_board
from .live_refresh import fast_refresh

app = FastAPI(title="Trench Edge API", version="4.1-v5-refresh")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"]
)

@app.get("/api/v1/health")
def health():
    return {
        "ok": True,
        "model": "TE V4.1",
        "pipeline": "v5 end-to-end Week refresh",
        "v4_equation": "locked",
        "mote": "recovered and automated",
        "standardization": "recovered season-week cross-sectional z-score",
        "probability": "TE_LINEAGE_CAL_0.1 provisional",
        "empirical_risk": empirical_risk_metadata(),
    }

@app.get("/api/v1/model-spec")
def model_spec():
    return {
        "model":"TE V4.1",
        "dqs_weights":DQS_WEIGHTS,
        "dqs_minimum":60,
        "ocrs_weights":OCRS_WEIGHTS,
        "ocrs_multipliers":{"four_components_ge_75":1.10,"six_components_ge_75":1.18,"cap":100},
        "spread_total_min_edge":2.5,
        "spread_total_preferred_edge":3.0,
        "moneyline_min_probability_advantage":0.05,
        "probability_calibration":"TE_LINEAGE_CAL_0.1",
        "risk_overlay":"TE_EMPIRICAL_RISK_E1",
    }

@app.post("/api/v1/refresh-week/{year}/{week}")
def refresh_week_endpoint(year:int, week:int):
    return run_refresh_week(year,week)

@app.get("/api/v1/week-board/{week}")
def week_board(week:int):
    return complete_week_board(week)

@app.get("/api/v1/live-board/{week}")
def live_board(week:int, force:bool=False):
    return fast_refresh(week=week,max_age_seconds=60,force=force)

@app.post("/api/v1/predict", response_model=MatchupResponse)
def predict(req: MatchupRequest):
    return calculate_matchup(req)

@app.post("/api/v1/recalculate-week2")
def recalculate_week2():
    inputs = load_inputs()
    outputs, errors = [], []
    for row in inputs:
        try:
            req = MatchupRequest.model_validate(row)
            outputs.append(calculate_matchup(req).model_dump())
        except Exception as exc:
            errors.append({"game_id": row.get("game_id"), "error": str(exc)})
    save_outputs(outputs)
    return {"calculated": len(outputs), "errors": errors, "outputs": outputs}

@app.get("/api/v1/games")
def games():
    return load_outputs()

@app.get("/api/v1/games/{game_id}")
def game(game_id: str):
    for row in load_outputs():
        if row.get("game_id") == game_id:
            return row
    raise HTTPException(404, "Game not found or not calculated yet")


@app.post("/api/v1/grade-result/{game_id}")
def grade_result(game_id:str, final_home:float, final_away:float):
    import json
    p=Path(__file__).resolve().parents[1]/"data"/"week2_outputs.json"
    if not p.exists(): raise HTTPException(404,"No refreshed week board")
    payload=json.loads(p.read_text())
    for g in payload.get("games",[]):
        if str(g.get("id"))==str(game_id):
            g["result"]=grade_prediction(g,final_home,final_away)
            p.write_text(json.dumps(payload,indent=2))
            (Path(__file__).resolve().parents[2]/"frontend"/"week2_board.json").write_text(json.dumps(payload,indent=2))
            return g["result"]
    raise HTTPException(404,"Game not found")

FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

@app.get("/")
def root():
    return FileResponse(FRONTEND / "index.html")

# Assets/static fallback comes last so it does not shadow /api routes.
app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="frontend")
