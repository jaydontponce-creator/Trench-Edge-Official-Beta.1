
from pathlib import Path
def test_grouped_frontend_exists():
    p=Path(__file__).resolve().parents[1]/"frontend"/"trench_edge_v6_grouped.html"
    t=p.read_text()
    assert "Qualified Bets" in t
    assert "Best Value" in t
    assert "Sat Primetime" in t
    assert "data-slate=\"fbs\"" in t
    assert "data-slate=\"fcs\"" in t
