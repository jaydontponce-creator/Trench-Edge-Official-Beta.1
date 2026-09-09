
from app.calibration import spread_probability,total_probability,home_win_probability,american_break_even,expected_value,assess
from app.empirical_risk import calculate_dfr,calculate_fpse

def test_calibration_bounds():
    for x in [0,1,2.5,5,10,20]:
        assert 0 <= spread_probability(x) <= 1
        assert 0 <= total_probability(x) <= 1

def test_moneyline_monotonic():
    assert home_win_probability(10) > home_win_probability(0) > home_win_probability(-10)

def test_american_break_even():
    assert abs(american_break_even(-110)-0.5238095238) < 1e-8
    assert abs(expected_value(0.55,-110) - (0.55*(100/110)-0.45)) < 1e-8

def test_empirical_risk_bounds():
    dfr=calculate_dfr({
        "pre_off_epa":0.0,"pre_off_pass_epa":0.0,"pre_off_rush_epa":0.0,
        "pre_off_firstdown":0.25,"pre_off_pass_protect":-0.05,"pre_off_havoc_avoid":-0.12,
        "RunMOTE":0.0,"PassMOTE":0.0,"Reliability":0.25
    })
    fp=calculate_fpse({
        "st_epa_pp_pre":0.0,"punt_epa_pp_pre":0.0,"ko_epa_pp_pre":0.0,
        "havoc_total_rate_pre":0.12,"takeaway_rate_pre":0.02,"Reliability":0.25
    })
    assert 0 <= dfr <= 100
    assert 0 <= fp <= 100


def test_negative_calibrated_ev_is_fail_not_needs_data():
    import json
    from pathlib import Path
    from app.schemas import MatchupRequest
    from app.engine import calculate_matchup
    sample=Path(__file__).resolve().parents[1]/"sample_predict_request.json"
    req=MatchupRequest(**json.loads(sample.read_text()))
    result=calculate_matchup(req)
    assert result.ev.calibrated is True
    assert result.ev.expected_value is not None
    if result.ev.expected_value <= 0 and result.decision.gate_results["dqs"]["pass"] and result.decision.gate_results["market_edge"]["pass"]:
        assert result.decision.state=="FAIL"
