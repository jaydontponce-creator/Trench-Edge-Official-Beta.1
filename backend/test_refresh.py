
from pathlib import Path
import json
from app.refresh import _load_demo_board

def test_demo_board_present():
    d=_load_demo_board()
    assert d["mode"]=="demo"
    assert len(d["games"])>=5

def test_frontend_board_written():
    p=Path(__file__).resolve().parents[1]/"frontend"/"week2_board.json"
    assert p.exists()
    d=json.loads(p.read_text())
    assert d["week"]==2
