from app.schemas import TeamFeatures, MatchupRequest, MarketSnapshot, DerivedMetrics, EVAssessment, DQSComponents, OCRSComponents
from app.engine import project_team, calculate_matchup
from app.risk import calculate_dqs, calculate_ocrs


def zeros(home=0.0):
    return TeamFeatures(
        defensive_weakness=0, off_epa=0, home_field=home,
        defensive_turnover_generation=0, pass_epa=0, opp_special_teams=0,
        run_mote=0, pace=0, special_teams=0, first_down_rate=0,
        pass_mote=0, explosiveness=0, rush_epa=0, opp_turnover_generation=0,
        weather_adjustment=0,
    )


def test_intercept():
    p = project_team("A", zeros())
    assert abs(p.expected_points - 28.225) < 1e-9


def test_home_field_coefficient():
    p = project_team("A", zeros(home=1.0))
    assert abs(p.expected_points - (28.225 + 1.862)) < 1e-9


def test_dqs_locked_weighted_formula():
    values = {k: 80 for k in [
        "ol_personnel","dl_personnel","player_history","transfers_new_starters","continuity",
        "injuries_availability","scheme_coaching","advanced_efficiency","opponent_strength_adjustment"
    ]}
    score, detail = calculate_dqs(values)
    assert score == 80.0


def test_ocrs_locked_formula_and_multiplier():
    values = {
        "run_mote_disadvantage":80,"pass_mote_disadvantage":80,"qb_pressure_vulnerability":80,
        "overall_efficiency_mismatch":80,"explosiveness_mismatch":20,"finishing_drive_mismatch":20,
        "personnel_continuity_uncertainty":20,"game_script_vulnerability":20,"dfr":20,"fpse":20
    }
    score, detail = calculate_ocrs(values)
    assert detail["multiplier"] == 1.10
    assert 0 <= score <= 100


def test_market_edge_requires_calibrated_ev_for_final_pass():
    req = MatchupRequest(
        game_id="x", away_team="Away", home_team="Home",
        away_features=zeros(), home_features=zeros(home=1.0),
        market=MarketSnapshot(home_spread=-1.0, total=55.0),
        derived_metrics=DerivedMetrics(ocrs=20,dqs=80,dfr=20,fpse=70,source="external")
    )
    out = calculate_matchup(req)
    assert round(out.model_margin_home,3) == 1.862
    assert out.decision.state == "FAIL"
    assert out.decision.gate_results["ev"]["pass"] is False


def test_final_pass_with_positive_calibrated_ev():
    req = MatchupRequest(
        game_id="y", away_team="Away", home_team="Home",
        away_features=zeros(), home_features=zeros(home=1.0),
        market=MarketSnapshot(home_spread=-1.0, total=55.0),
        derived_metrics=DerivedMetrics(ocrs=20,dqs=80,dfr=20,fpse=20,source="external"),
        ev=EVAssessment(probability=.57, break_even_probability=.524, expected_value=.045, calibrated=True, source="test")
    )
    out = calculate_matchup(req)
    assert out.decision.state == "PASS"
