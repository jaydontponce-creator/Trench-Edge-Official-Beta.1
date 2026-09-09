from __future__ import annotations
from typing import Dict, List, Tuple, Any
from .schemas import TeamFeatures, TeamProjection, FeatureContribution, MatchupRequest, MatchupResponse, Decision, DerivedMetrics
from .model_config import INTERCEPT, COEFFICIENTS
from .risk import calculate_dqs, calculate_ocrs
from .empirical_risk import calculate_dfr, calculate_fpse, metadata as empirical_risk_metadata
from .calibration import assess as calibrate_market


def _terms(f: TeamFeatures) -> Dict[str, float]:
    return {
        "defensive_weakness": f.defensive_weakness,
        "off_epa": f.off_epa,
        "home_field": f.home_field,
        "defensive_turnover_generation": f.defensive_turnover_generation,
        "pass_epa": f.pass_epa,
        "opp_special_teams": f.opp_special_teams,
        "run_mote": f.run_mote,
        "pace": f.pace,
        "special_teams": f.special_teams,
        "first_down_rate": f.first_down_rate,
        "pass_mote_x_explosiveness": f.pass_mote * f.explosiveness,
        "run_mote_x_rush_epa": f.run_mote * f.rush_epa,
        "opp_turnover_generation": f.opp_turnover_generation,
        "pass_mote_x_pass_epa": f.pass_mote * f.pass_epa,
        "pass_mote": f.pass_mote,
    }


def project_team(team: str, f: TeamFeatures) -> TeamProjection:
    rows: List[FeatureContribution] = [FeatureContribution(feature="intercept", value=1.0, coefficient=None, contribution=INTERCEPT)]
    expected = INTERCEPT
    for name, value in _terms(f).items():
        beta = COEFFICIENTS[name]
        contribution = beta * value
        expected += contribution
        rows.append(FeatureContribution(feature=name, value=value, coefficient=beta, contribution=contribution))
    expected += f.weather_adjustment
    rows.append(FeatureContribution(feature="weather_adjustment", value=f.weather_adjustment, coefficient=1.0, contribution=f.weather_adjustment))
    return TeamProjection(team=team, expected_points=round(expected, 3), contributions=rows)


def _rank_attribution(home: TeamProjection, away: TeamProjection) -> Dict[str, Any]:
    h = {x.feature: x.contribution for x in home.contributions}
    a = {x.feature: x.contribution for x in away.contributions}
    diff = {k: h.get(k,0.0)-a.get(k,0.0) for k in set(h)|set(a) if k!="intercept"}
    ranked=sorted(diff.items(), key=lambda kv:abs(kv[1]), reverse=True)
    abs_sum=sum(abs(v) for _,v in ranked)
    ecs=(abs(ranked[0][1])/abs_sum) if ranked and abs_sum else 0.0
    direction="home" if sum(diff.values())>=0 else "away"
    dac=sum(1 for _,v in ranked if (v>0 if direction=="home" else v<0))
    return {
        "direction":direction,
        "feature_vector":[{"feature":k,"margin_contribution":round(v,4)} for k,v in ranked],
        "top_drivers":[{"feature":k,"margin_contribution":round(v,4)} for k,v in ranked if (v>0 if direction=="home" else v<0)][:3],
        "counterweights":[{"feature":k,"margin_contribution":round(v,4)} for k,v in ranked if (v<0 if direction=="home" else v>0)][:2],
        "ecs":round(ecs,4),"dac":dac,"method":"TE Attribution & Explainability Layer v1"
    }


def _resolve_derived(req: MatchupRequest) -> DerivedMetrics:
    dm=req.derived_metrics.model_copy(deep=True)
    source_parts=[]

    # Empirically complete previously unauthenticated DFR/FPSE conversions when model-ready inputs exist.
    if dm.dfr is None and dm.dfr_inputs is not None:
        dm.dfr=calculate_dfr(dm.dfr_inputs)
        dm.details["dfr_empirical"]={"score":dm.dfr, **empirical_risk_metadata()}
        source_parts.append("dfr_empirical")
    if dm.fpse is None and dm.fpse_inputs is not None:
        dm.fpse=calculate_fpse(dm.fpse_inputs)
        dm.details["fpse_empirical"]={"score":dm.fpse, **empirical_risk_metadata()}
        source_parts.append("fpse_empirical")

    if dm.dqs_components is not None:
        score, detail=calculate_dqs(dm.dqs_components.model_dump())
        dm.dqs=score; dm.details["dqs"]=detail; source_parts.append("dqs_locked")

    if dm.ocrs_components is not None:
        comp=dm.ocrs_components.model_dump()
        # Empirical DFR/FPSE override only those two OCRS component values when available.
        if dm.dfr is not None: comp["dfr"]=dm.dfr
        if dm.fpse is not None: comp["fpse"]=dm.fpse
        score, detail=calculate_ocrs(comp)
        dm.ocrs=score; dm.ocrs_band=detail["band"]
        dm.dfr=comp["dfr"]; dm.fpse=comp["fpse"]
        dm.details["ocrs"]=detail; source_parts.append("ocrs_locked")

    if source_parts:
        dm.source="mixed" if any("empirical" in x for x in source_parts) else "locked_formula"
    return dm

def _decision(req: MatchupRequest, dm: DerivedMetrics, model_margin_home:float, model_total:float):
    spread_edge_home=total_edge_over=None
    reasons=[]; gates={}; candidates=[]
    if req.market.home_spread is not None:
        spread_edge_home=model_margin_home+req.market.home_spread
        candidates.append(("spread", req.home_team if spread_edge_home>=0 else req.away_team, abs(spread_edge_home)))
    if req.market.total is not None:
        total_edge_over=model_total-req.market.total
        candidates.append(("total", "OVER" if total_edge_over>=0 else "UNDER", abs(total_edge_over)))

    gates["dqs"]={"value":dm.dqs,"minimum":60,"pass": dm.dqs is not None and dm.dqs>=60}
    if dm.dqs is None: reasons.append("DQS unavailable.")
    elif dm.dqs<60: reasons.append(f"DQS {dm.dqs:.1f} is below the locked 60 minimum.")

    complete_risk=all(x is not None for x in [dm.ocrs,dm.dfr,dm.fpse])
    gates["ocrs_complete"]={"pass":complete_risk,"value":dm.ocrs,"band":dm.ocrs_band}
    if not complete_risk: reasons.append("OCRS/DFR/FPSE are incomplete.")

    if not candidates: reasons.append("No market spread/total supplied.")
    best=max(candidates,key=lambda x:x[2]) if candidates else None
    edge=best[2] if best else None
    gates["market_edge"]={"value":edge,"minimum":2.5,"preferred":3.0,"pass":edge is not None and edge>=2.5}
    if best and edge<2.5: reasons.append(f"Largest model/market disagreement is {edge:.2f}, below 2.5.")

    # Use external calibrated EV when explicitly supplied; otherwise use the provisional historical TE-lineage calibrator.
    ev_assessment=req.ev
    if best is not None and not req.ev.calibrated:
        odds=req.market.spread_price_american if best[0]=="spread" else req.market.total_price_american
        auto=calibrate_market(best[0], edge, odds=odds, model_margin_home=model_margin_home)
        from .schemas import EVAssessment
        ev_assessment=EVAssessment(**auto)
    ev_ok=ev_assessment.calibrated and ev_assessment.expected_value is not None and ev_assessment.expected_value>0
    gates["ev"]={"calibrated":ev_assessment.calibrated,"probability":ev_assessment.probability,
                 "break_even_probability":ev_assessment.break_even_probability,
                 "expected_value":ev_assessment.expected_value,"source":ev_assessment.source,"pass":ev_ok}
    if not ev_assessment.calibrated: reasons.append("Calibrated probability/EV unavailable.")
    elif ev_assessment.expected_value is None or ev_assessment.expected_value<=0:
        reasons.append(f"Calibrated EV is not positive ({ev_assessment.expected_value}).")

    if dm.dqs is None or not complete_risk or not candidates:
        return Decision(state="NEEDS_DATA", market=best[0] if best else None, side=best[1] if best else None, edge=round(edge,3) if edge is not None else None, reasons=reasons, gate_results=gates),spread_edge_home,total_edge_over,ev_assessment
    if dm.dqs<60 or edge<2.5:
        return Decision(state="FAIL",market=best[0],side=best[1],edge=round(edge,3),reasons=reasons,gate_results=gates),spread_edge_home,total_edge_over,ev_assessment

    # Operationally, severe OCRS (80-100) is treated as a risk veto only when it is the OCRS for the candidate selection.
    # This is logged explicitly and never rewrites the raw score.
    if dm.ocrs is not None and dm.ocrs>=80:
        gates["ocrs_veto"]={"pass":False,"reason":"Severe OCRS band (80-100)"}
        reasons.append(f"OCRS {dm.ocrs:.1f} is Severe; candidate is vetoed by the risk overlay.")
        return Decision(state="FAIL",market=best[0],side=best[1],edge=round(edge,3),reasons=reasons,gate_results=gates),spread_edge_home,total_edge_over,ev_assessment
    gates["ocrs_veto"]={"pass":True}

    if not ev_ok:
        if ev_assessment.calibrated:
            reasons.append(f"Qualified model-market edge exists ({edge:.2f} points), but the calibrated EV gate fails.")
            return Decision(state="FAIL",market=best[0],side=best[1],edge=round(edge,3),reasons=reasons,gate_results=gates),spread_edge_home,total_edge_over,ev_assessment
        reasons.append(f"Qualified model-market edge: {best[0]} {best[1]} by {edge:.2f} points, but calibrated EV is unavailable.")
        return Decision(state="NEEDS_DATA",market=best[0],side=best[1],edge=round(edge,3),reasons=reasons,gate_results=gates),spread_edge_home,total_edge_over,ev_assessment

    reasons.append(f"{best[0].title()} edge {edge:.2f} clears the market threshold and calibrated EV is positive.")
    return Decision(state="PASS",market=best[0],side=best[1],edge=round(edge,3),reasons=reasons,gate_results=gates),spread_edge_home,total_edge_over,ev_assessment


def calculate_matchup(req:MatchupRequest)->MatchupResponse:
    dm=_resolve_derived(req)
    away=project_team(req.away_team,req.away_features); home=project_team(req.home_team,req.home_features)
    margin=home.expected_points-away.expected_points; total=home.expected_points+away.expected_points
    attribution=_rank_attribution(home,away)
    decision,spread_edge_home,total_edge_over,ev_assessment=_decision(req,dm,margin,total)
    return MatchupResponse(game_id=req.game_id,away=away,home=home,model_margin_home=round(margin,3),model_total=round(total,3),spread_edge_home=None if spread_edge_home is None else round(spread_edge_home,3),total_edge_over=None if total_edge_over is None else round(total_edge_over,3),attribution=attribution,derived_metrics=dm,ev=ev_assessment,decision=decision)
