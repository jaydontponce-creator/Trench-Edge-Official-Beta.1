# Trench Edge V4.1 Full-Stack Backend v1

This version moves TE from manually populated cards toward a calculation-driven application.

## What is real and locked now

- Canonical `ExpectedPoints_V4` equation is implemented exactly from the locked V4 specification.
- Every V4 term is calculated server-side from standardized inputs.
- Interaction terms are calculated server-side:
  - PassMOTE × Explosiveness
  - RunMOTE × RushEPA
  - PassMOTE × PassEPA
- WeatherAdjustment is applied after the linear terms.
- Full per-team feature contribution vectors are generated.
- Matchup differential attribution, top drivers, counterweights, ECS and DAC are generated automatically.
- Model spread, model total, spread edge and total edge are calculated automatically.
- Known qualification gates are enforced:
  - DQS < 60 = FAIL
  - Spread/total disagreement < 2.5 points = FAIL
  - 3+ points is marked as preferred
- If required derived metrics are unavailable, decision becomes `NEEDS_DATA` instead of fabricating a PASS.

## What is intentionally NOT invented

The exact locked formulas for OCRS, DQS, DFR and FPSE were not present in the accessible model context when this backend was built. The API therefore accepts those values as externally supplied derived metrics and blocks qualification when they are absent. Their config file is `backend/config/derived_metrics.json`.

Likewise, the locked standardization means/standard deviations are required before raw-stat input mode can be implemented. Current `/predict` requests expect already-standardized feature inputs. See `backend/config/standardization.json`.

This is deliberate. It prevents mock UI formulas from contaminating the TE production model.

## Run locally

### Windows
Double-click `start_te.bat`, then open:

`http://127.0.0.1:8000`

### macOS/Linux

```bash
./start_te.sh
```

Then open `http://127.0.0.1:8000`.

## API

- `GET /api/v1/health`
- `POST /api/v1/predict`
- `POST /api/v1/recalculate-week2`
- `GET /api/v1/games`
- `GET /api/v1/games/{game_id}`
- Interactive API docs: `http://127.0.0.1:8000/docs`

Use `sample_predict_request.json` as an example request body.

## Week 2 batch flow

Populate `backend/data/week2_inputs.json` with matchup request objects. Then call:

`POST /api/v1/recalculate-week2`

The backend will write immutable-style calculated output snapshots to `backend/data/week2_outputs.json`. The website reads those outputs through `/api/v1/games`.

## Next integrations

1. Recover and encode the locked OCRS/DQS/DFR/FPSE formulas.
2. Lock and load the V4 standardization table.
3. Add market-line adapter.
4. Add injury adapter.
5. Add weather adapter.
6. Add scheduled snapshotting and closing-line/result grading.
7. Move JSON persistence to SQLite/PostgreSQL.

## v2 data-pipeline additions

The backend now implements the authenticated DQS and OCRS formulas from Master Specification v1.1.

### Provider environment variables

Set these before starting the API:

```bash
CFBD_API_KEY=your_collegefootballdata_key
ODDS_API_KEY=your_the_odds_api_key
```

Windows PowerShell example:

```powershell
$env:CFBD_API_KEY="..."
$env:ODDS_API_KEY="..."
```

### New endpoints

- `GET /api/v1/model-spec` - locked machine-readable DQS/OCRS/gate configuration
- `GET /api/v1/providers` - tells you which live data adapters are configured
- `POST /api/v1/refresh-week/2026/2` - discovers/enriches the Week 2 FBS slate

### Live feed architecture

- CFBD: schedule, analytics, ratings, play data, roster source data
- The Odds API: NCAAF spread/total consensus snapshot
- Open-Meteo: venue weather adapter
- InjuryProvider: timestamped local/licensed feed adapter; no unverified injury scraper is assumed

### Intentionally blocked until authenticated/recovered

The pipeline will not invent: V4 standardization means/stds, the raw OL/DL-to-MOTE formula,
DFR raw-to-risk scoring, FPSE raw-to-risk scoring, probability calibration, or staking. These remain
explicit readiness blockers rather than silent approximations.


## v3 recovered scaler + MOTE pipeline

The archived `te_v2_predictions.csv` was used to mathematically recover the original TE lineage transformations.

Recovered exactly:
- Reliability = `pregame_games / (pregame_games + 3)`
- Offseason prior = 50% previous-season team mean + 50% previous-season global mean
- In-season prior = Reliability × current-season team mean + (1 − Reliability) × offseason prior
- Standardization = cross-sectional z-score within the same season/week using population standard deviation
- RunOTE = 2.50 × z(off_run_line) + 1.25 × z(off_run_stuffavoid) + 1.25 × z(off_run_power)
- RunDTE = 2.50 × z(def_run_line) + 1.25 × z(def_run_stuff) + 1.25 × z(def_run_power)
- PassOTE = 3.35 × z(off_pass_protect) + 1.65 × z(off_havoc_avoid)
- PassDTE = 3.35 × z(def_pass_rush) + 1.65 × z(def_havoc)
- RunMOTE = RunOTE − opponent RunDTE
- PassMOTE = PassOTE − opponent PassDTE

These identities reproduce the archived MOTE fields to floating-point precision across 15,544 rows.

The current CFBD adapter now exposes `/stats/game/advanced`, `/stats/season/advanced`, and `/stats/game/havoc` so current data can feed the recovered transformation chain. Sack rates are transparently derived from play-by-play.

Still gated:
- exact V4 mapping for any feature whose raw historical definition has not been authenticated
- DFR/FPSE numeric scoring conversion
- probability/EV calibration
- injury normalization from a licensed/timestamped source


## v4 probability calibration + empirical DFR/FPSE

### Probability
`TE_LINEAGE_CAL_0.1` is now the default provisional calibration layer.

- Historical scope: FBS, 2016-2025.
- Temporal validation: 2016-2024 training, 2025 holdout.
- Spread and total probabilities use isotonic calibration of absolute model-market edge.
- Moneyline/winner probability uses logistic calibration of model home margin.
- 2026 prospective TE evidence is logged separately and will increasingly replace the historical lineage calibration as the live V4.1 sample grows.

2025 holdout:
- Spread: n=762, hit=0.500, Brier=0.2500.
- Total: n=762, hit=0.492, Brier=0.2525.
- Moneyline winner probability: n=762, Brier=0.1904, AUC=0.770.

The spread holdout result is intentionally conservative: raw edge alone did not beat the market. The engine therefore will not fabricate positive EV from a large point discrepancy.

### Empirical DFR / FPSE
`TE_EMPIRICAL_RISK_E1` fills the previously unauthenticated 0-100 DFR/FPSE conversions as an explicitly experimental OCRS overlay.

- DFR predicts severe drive-failure exposure using pregame EPA, first-down production, pass-protection/havoc avoidance, RunMOTE, PassMOTE and reliability.
- FPSE predicts severe field-position/special-teams exposure using smoothed special-teams, punt/kickoff, opponent havoc and opponent takeaway inputs.
- These risk scores do not alter the canonical raw V4.1 equation.
- Because these are newly defined numerical conversions, they are versioned separately and must be prospectively validated before being treated as canonical.

2025 holdout:
- DFR AUC=0.693, Brier=0.1677.
- FPSE AUC=0.612, Brier=0.1827.


## v5 end-to-end Week 2 refresh

New endpoint:

`POST /api/v1/refresh-week/2026/2`

Refresh pipeline:

1. Discover target-week games from CFBD.
2. Pull prior-season and completed-current-season advanced stats.
3. Build recovered TE preseason and in-season priors.
4. Standardize the target-week slate cross-sectionally.
5. Calculate RunOTE/RunDTE/PassOTE/PassDTE and RunMOTE/PassMOTE.
6. Build DQS and experimental DFR/FPSE inputs.
7. Calculate OCRS.
8. Pull consensus market spread/total when an odds provider key is configured.
9. Run canonical V4.1 scoring + attribution + calibrated probability/EV.
10. Freeze PASS/FAIL/NEEDS_DATA output into `backend/data/week2_outputs.json`.
11. Mirror that payload to `frontend/week2_board.json`.

The frontend supports an operational demo mode when API keys are absent. This allows every screen/tab/filter to be tested immediately. A live refresh requires CFBD_API_KEY and ODDS_API_KEY in the environment.

Run locally:
`start_te.bat`
Then open:
`http://127.0.0.1:8000`


## v6 product expansion
- Landing slogan removed.
- Added plain-language “How Trench Edge Works” education page.
- Added complete Week 2 FBS/cross-division + FCS schedule fallback.
- Live refresh is designed to request both FBS and FCS from CFBD and de-duplicate cross-division games.
- Matchups with incomplete live TE data display WAIT FOR MORE DATA instead of fabricated recommendations.
- Win-probability donut uses team school colors from CFBD metadata in live mode, with a fallback color map.
- Risk page now defines risk and explains concrete ways a prediction can fail.
- Added postgame result grading and model-driver explanation.
- Added weekly_refresh.py for Task Scheduler/cron deployment. Automatic updating occurs while the application/deployment is running and has network/API access.
