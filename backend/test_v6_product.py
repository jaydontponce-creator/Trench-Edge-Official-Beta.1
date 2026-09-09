
from app.branding import fallback_colors
from app.results import grade_prediction
import json
from pathlib import Path

def test_team_colors():
    assert fallback_colors("Oklahoma")[0].lower()=="#841617"
    assert fallback_colors("Michigan")[0].lower()=="#00274c"

def test_complete_fallback_schedule():
    p=Path(__file__).resolve().parent/"data"/"week2_complete_schedule_fallback.json"
    d=json.loads(p.read_text())
    assert len(d["games"]) > 100
    assert any(g["classification"]=="FCS" for g in d["games"])

def test_result_explanation():
    game={"prediction":{"home_points":30,"away_points":20},
          "decision":{"state":"FAIL"},
          "market":{},"attribution":{"drivers":[{"name":"Pass protection"}],"counterweights":[{"name":"Turnover variance"}]}}
    r=grade_prediction(game,31,17)
    assert r["winner_correct"] is True
    assert "Pass protection" in r["explanation"]
