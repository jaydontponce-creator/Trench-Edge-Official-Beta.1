from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field

class TeamFeatures(BaseModel):
    defensive_weakness: float
    off_epa: float
    home_field: float = 0.0
    defensive_turnover_generation: float
    pass_epa: float
    opp_special_teams: float
    run_mote: float
    pace: float
    special_teams: float
    first_down_rate: float
    pass_mote: float
    explosiveness: float
    rush_epa: float
    opp_turnover_generation: float
    weather_adjustment: float = 0.0

class MarketSnapshot(BaseModel):
    home_spread: Optional[float] = None
    total: Optional[float] = None
    spread_price_american: float = -110.0
    total_price_american: float = -110.0
    home_moneyline_prob: Optional[float] = Field(default=None, ge=0, le=1)
    away_moneyline_prob: Optional[float] = Field(default=None, ge=0, le=1)
    timestamp: Optional[str] = None
    source: Optional[str] = None
    bookmaker_count: Optional[int] = None

class DQSComponents(BaseModel):
    ol_personnel: float = Field(ge=0, le=100)
    dl_personnel: float = Field(ge=0, le=100)
    player_history: float = Field(ge=0, le=100)
    transfers_new_starters: float = Field(ge=0, le=100)
    continuity: float = Field(ge=0, le=100)
    injuries_availability: float = Field(ge=0, le=100)
    scheme_coaching: float = Field(ge=0, le=100)
    advanced_efficiency: float = Field(ge=0, le=100)
    opponent_strength_adjustment: float = Field(ge=0, le=100)

class OCRSComponents(BaseModel):
    run_mote_disadvantage: float = Field(ge=0, le=100)
    pass_mote_disadvantage: float = Field(ge=0, le=100)
    qb_pressure_vulnerability: float = Field(ge=0, le=100)
    overall_efficiency_mismatch: float = Field(ge=0, le=100)
    explosiveness_mismatch: float = Field(ge=0, le=100)
    finishing_drive_mismatch: float = Field(ge=0, le=100)
    personnel_continuity_uncertainty: float = Field(ge=0, le=100)
    game_script_vulnerability: float = Field(ge=0, le=100)
    dfr: float = Field(ge=0, le=100)
    fpse: float = Field(ge=0, le=100)

class DerivedMetrics(BaseModel):
    ocrs: Optional[float] = None
    dqs: Optional[float] = None
    dfr: Optional[float] = None
    fpse: Optional[float] = None
    ocrs_band: Optional[str] = None
    dqs_components: Optional[DQSComponents] = None
    ocrs_components: Optional[OCRSComponents] = None
    dfr_inputs: Optional[Dict[str, float]] = None
    fpse_inputs: Optional[Dict[str, float]] = None
    details: Dict[str, Any] = {}
    source: Literal["locked_formula", "external", "mixed", "missing"] = "missing"

class EVAssessment(BaseModel):
    probability: Optional[float] = Field(default=None, ge=0, le=1)
    break_even_probability: Optional[float] = Field(default=None, ge=0, le=1)
    expected_value: Optional[float] = None
    source: Optional[str] = None
    calibrated: bool = False

class MatchupRequest(BaseModel):
    game_id: str
    away_team: str
    home_team: str
    away_features: TeamFeatures
    home_features: TeamFeatures
    market: MarketSnapshot = MarketSnapshot()
    derived_metrics: DerivedMetrics = DerivedMetrics()
    ev: EVAssessment = EVAssessment()
    metadata: Dict[str, Any] = {}

class FeatureContribution(BaseModel):
    feature: str
    value: float
    coefficient: Optional[float] = None
    contribution: float

class TeamProjection(BaseModel):
    team: str
    expected_points: float
    contributions: List[FeatureContribution]

class Decision(BaseModel):
    state: Literal["PASS", "FAIL", "NEEDS_DATA"]
    market: Optional[str] = None
    side: Optional[str] = None
    edge: Optional[float] = None
    reasons: List[str]
    gate_results: Dict[str, Any] = {}

class MatchupResponse(BaseModel):
    game_id: str
    away: TeamProjection
    home: TeamProjection
    model_margin_home: float
    model_total: float
    spread_edge_home: Optional[float] = None
    total_edge_over: Optional[float] = None
    attribution: Dict[str, Any]
    derived_metrics: DerivedMetrics
    ev: EVAssessment
    decision: Decision
    model_version: str = "TE V4.1"
