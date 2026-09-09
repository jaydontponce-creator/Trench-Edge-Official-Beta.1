
from app.mote import reliability, offseason_prior, inseason_prior, calculate_ote_dte, calculate_matchup_mote
from app.standardize import standardize_slate

def test_reliability_schedule():
    assert reliability(0)==0
    assert reliability(1)==0.25
    assert reliability(2)==0.4
    assert reliability(3)==0.5
    assert round(reliability(9),12)==0.75

def test_offseason_and_inseason_prior():
    assert offseason_prior(3.08,2.5063756983240224)==(3.08+2.5063756983240224)/2
    baseline=2.6283318472550685
    # archived UNC example: current mean 3.155 after two games, n=2 => r=.4
    got=inseason_prior(baseline,3.155,2)
    assert abs(got-2.838999108353041) < 1e-12

def test_cross_sectional_population_z():
    rows=[{"x":1.0},{"x":2.0},{"x":3.0}]
    d=standardize_slate(rows,["x"])
    assert abs(sum(r["z_x"] for r in rows)) < 1e-12
    assert abs(sum(r["z_x"]**2 for r in rows)/3 - 1) < 1e-12

def test_exact_mote_weights():
    team={
        "z_off_run_line":1.0,"z_off_run_stuffavoid":2.0,"z_off_run_power":-1.0,
        "z_off_pass_protect":0.5,"z_off_havoc_avoid":1.0,
        "z_def_run_line":0.0,"z_def_run_stuff":0.0,"z_def_run_power":0.0,
        "z_def_pass_rush":0.0,"z_def_havoc":0.0,
    }
    opp={
        "z_off_run_line":0.0,"z_off_run_stuffavoid":0.0,"z_off_run_power":0.0,
        "z_off_pass_protect":0.0,"z_off_havoc_avoid":0.0,
        "z_def_run_line":1.0,"z_def_run_stuff":1.0,"z_def_run_power":1.0,
        "z_def_pass_rush":1.0,"z_def_havoc":1.0,
    }
    m=calculate_matchup_mote(team,opp)
    # RunOTE = 2.5 + 2.5 -1.25 = 3.75; OppRunDTE = 5.0
    assert abs(m["RunMOTE"] - (-1.25)) < 1e-12
    # PassOTE = 3.35*.5 + 1.65 = 3.325; OppPassDTE = 5.0
    assert abs(m["PassMOTE"] - (-1.675)) < 1e-12
