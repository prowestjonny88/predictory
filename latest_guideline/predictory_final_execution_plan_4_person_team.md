# Predictory Final Execution Plan — 4-Person Team

**Purpose:** Convert all locked decisions into a practical, low-conflict execution plan for the Predictory finals build.

**Team constraint:** 4 people total.

- **Member 1:** ML owner, using the previously generated ML guidebook / ML workflow MD.
- **Members 2–4:** Frontend/backend/integration work.
- Main risk to avoid: merge conflicts, inconsistent variable names, duplicate logic, and different teammates defining the same concept differently.

**Final product framing:**

> **Predictory is the decision layer between yesterday’s sales and tomorrow’s bake — an AI-assisted planning copilot that helps bakery MSMEs decide what to prep, what to reorder, and why.**

---

## 1. Locked Strategic Decisions

### 1.1 ML / Decision Engine

| Area | Locked Decision |
|---|---|
| Forecast direction | MLOps-ready LightGBM prototype |
| Dataset strategy | French Bakery demand base + FreshRetailNet grounding |
| Model target | `estimated_true_demand` |
| Stockout recovery | Hybrid recovery with caps |
| Forecast output | LightGBM `p50` + residual `p10/p90` bands now; true quantile models later |
| Residual bands | SKU category + daypart, with global fallback |
| LightGBM feature set | Practical feature set: outlet/SKU/category/daypart/calendar/weather/promo/lags/waste/stockout/price |
| Optimizer objective | Minimize financial mismatch cost: waste cost + stockout/lost-sales cost |
| SKU economics | Derived from price + assumed margin ratio; configurable later |
| Optimizer constraints | Batch size + capacity + freshness |
| Forecast generation | Read latest saved forecast run by default; manual regenerate button |
| Model status wording | MLOps prototype; validated on POS-style demo window; ready for POS/ERP retraining |

### 1.2 Data Pipeline

| Area | Locked Decision |
|---|---|
| Training grain | `date × outlet_id × sku_id × daypart` |
| Dataset size | 5 outlets × 12 SKUs × 3 dayparts × 180 days = 32,400 rows |
| Outlet profiles | Malaysian realistic outlet archetypes |
| SKUs | French Bakery mapped SKUs |
| Dayparts | Morning / Midday / Evening |
| Prep simulation | Naive human planner with outlet/SKU/daypart bias and noise |
| Opening stock | Freshness-adjusted carryover by SKU |
| BOM | Practical BOM with 4–6 ingredients per SKU |
| Ingredient stock | Simulated stock with daily consumption and simple replenishment |
| Storage | DB tables + model artifacts, with CSV exports for debugging |
| Training trigger | Manual script + backend admin training endpoint |

### 1.3 Repo Cleanup

| Area | Locked Decision |
|---|---|
| Cleanup order | Runtime correctness → truthfulness → data/model consistency → security/audit |
| First runtime batch | Crashes + data shape mismatches now; full sweep later if time |
| Seed/data alignment | Add new ML/demo seed pipeline alongside old seed |
| Fake charts | Replace with real compact ML/decision evidence |
| Hardcoded confidence | Replace with model evidence |
| Old endpoints | Visible flow uses LightGBM + optimizer; old heuristic kept internally as fallback/debug baseline |
| Fallback UI | Small model status badge |
| Audit log | Decision audit log |
| Auth/RBAC | Demo-grade role switcher |
| Admin endpoint security | Simple admin token |
| Stale ingredient stock | Simple stock movement on plan approval / replenishment receipt |
| DB lifecycle | `create_all` only in local/dev seed mode; Alembic for normal startup |
| Page data source | Visible pages read latest saved forecast run |
| Smoke testing | Scripted backend smoke tests + manual frontend demo checklist |

### 1.4 UI / UX

| Area | Locked Decision |
|---|---|
| Main screen | Daily Planning Workspace-first |
| First visible card | Action summary first, with compact model badge nearby |
| Recommendation grouping | Top Actions first, with By Outlet / By SKU / By Risk filters |
| p10/p50/p90 visual | Compact uncertainty bar with recommended prep marker |
| Gemini UI | Inline explanations + manager-note parser panel |
| Approval UI | Side drawer with details, reason field, and audit preview |
| Replenishment UI | Prep-to-ingredient breakdown as core; supplier message optional |
| Risk UI | Risk with financial exposure |
| Model evidence | Compact badge + expandable evidence drawer |
| Demo sequence | Linear decision flow |

---

## 2. Team Role Assignment — Best Low-Conflict Split

### Overview

To avoid merge conflicts, **each person owns a clearly separated surface area**. Only the integration lead touches cross-cutting files after contract approval.

| Member | Role | Owns | Avoids Touching |
|---|---|---|---|
| Member 1 | ML/Data Owner | Dataset generation, feature table, model training, residual bands, metrics, artifacts | Frontend UI, API route design except agreed artifact contracts |
| Member 2 | Backend/API Owner | DB models, forecast run APIs, optimizer, BOM/replenishment APIs, approval/audit APIs | ML training internals, frontend components |
| Member 3 | Frontend/UI Owner | Daily Planning Workspace, cards, uncertainty bar, drawers, role switcher, demo flow UI | Backend logic, ML artifacts |
| Member 4 | Integration/QA/Repo Cleanup Owner | Runtime fixes, fake chart removal, smoke tests, env setup, merge coordination, demo rehearsal, pitch support | ML model internals, major UI redesign unless coordinated |

### Recommended naming for teammates

If names are not finalized, use internal labels in tasks:

```text
ML Owner
Backend Owner
Frontend Owner
Integration/QA Owner
```

Do not assign two people to the same file unless one is the reviewer only.

---

## 3. Merge-Conflict Prevention Rules

### 3.1 Contract-first rule

Before heavy implementation, create one small PR called:

```text
PR-0: contracts-and-naming-freeze
```

This PR defines:

- API response shapes
- shared field names
- model artifact names
- route names
- DB table names
- UI copy for model status

No one starts large work until this PR is merged.

### 3.2 Ownership boundaries

#### ML Owner may edit

```text
scripts/generate_demo_dataset.py
scripts/train_lightgbm.py
scripts/generate_forecast_artifacts.py
apps/api/ml/
models/
exports/
data/demo/
docs/ml/
```

#### Backend Owner may edit

```text
apps/api/models/
apps/api/schemas/
apps/api/routes/
apps/api/services/forecast_runs.py
apps/api/services/optimizer.py
apps/api/services/replenishment.py
apps/api/services/audit.py
apps/api/services/model_loader.py
apps/api/alembic/
```

#### Frontend Owner may edit

```text
apps/web/src/app/daily-planning/
apps/web/src/components/planning/
apps/web/src/components/model-evidence/
apps/web/src/components/gemini/
apps/web/src/components/approval/
apps/web/src/lib/api/planning.ts
```

#### Integration/QA Owner may edit

```text
scripts/smoke_test_demo_flow.py
scripts/reset_demo_env.sh
README.md
.env.example
docs/demo/
docs/pitch/
apps/web/src/app/page.tsx          # only for routing/hiding weak pages
apps/web/src/navigation*           # only for hiding demo-theater routes
```

### 3.3 Shared-file lock rule

Shared files require coordination before editing:

```text
apps/api/main.py
apps/api/database.py
apps/api/config.py
apps/web/src/lib/api/client.ts
apps/web/src/app/layout.tsx
package.json / pyproject.toml / requirements.txt
.env.example
```

Only the Integration/QA Owner should merge changes to these files after reviewing impact.

### 3.4 Naming freeze

Everyone uses the same canonical field names:

| Concept | Canonical Name |
|---|---|
| Forecast run ID | `forecast_run_id` |
| Model run ID | `model_run_id` |
| Model version | `model_version` |
| Forecast engine | `engine_name` |
| Low demand estimate | `p10` |
| Median/expected demand estimate | `p50` |
| High demand estimate | `p90` |
| Model target | `estimated_true_demand` |
| Current POS sales | `actual_sales` |
| Recommended prep | `recommended_prep` |
| Final approved prep | `final_prep` |
| Stockout cost | `stockout_cost` |
| Waste cost | `waste_cost` |
| Financial risk | `financial_exposure` |
| Decision impact | `estimated_mismatch_cost_delta` |
| Operator action | `operator_action` |
| Operator reason | `operator_reason` |
| Gemini parsed adjustment | `gemini_note_adjustment` |

Do not invent alternatives like:

```text
forecastId
run_id
median_forecast
expected_sales
predicted_sales
recommended_quantity
ai_confidence
```

unless mapped explicitly in a serializer.

---

## 4. Canonical API Contracts

These contracts should be frozen early so frontend and backend can work independently.

### 4.0 Phase 0 — Contract Freeze (Immediate)

**Owner:** Integration/QA (Member 4) initiates this now.

Lock the exact field names and types so frontend and backend can implement in parallel:

- `p10`, `p50`, `p90`, `recommended_prep` are **integers (unit counts)** and **always present** on each recommendation.
- Keys are **exact** (no camelCase or alternate names).
- `p10 <= p50 <= p90` for the same outlet/SKU/daypart; `recommended_prep` is the **suggested prep units** (post batch-size rounding if applicable).

Frozen mini-contract (reference snippet):

```json
{
  "p10": 82,
  "p50": 100,
  "p90": 125,
  "recommended_prep": 105
}
```

### 4.1 Latest Daily Plan

```http
GET /api/daily-plan/latest?date=2026-04-30
```

Response:

```json
{
  "forecast_run_id": "fr_20260430_001",
  "model_run_id": "mr_lightgbm_p50_v1",
  "model_version": "lightgbm_p50_v1",
  "engine_name": "lightgbm_mlops_prototype",
  "model_status": "MLOps prototype",
  "validation_window": "last_30_demo_days",
  "metrics": {
    "wape": 0.168,
    "bias": -0.021,
    "p10_p90_coverage": 0.78,
    "estimated_mismatch_cost_delta_pct": -0.12
  },
  "top_actions": [
    {
      "id": "rec_001",
      "outlet_id": "cheras_hub",
      "outlet_name": "Cheras Community Hub",
      "sku_id": "butter_croissant",
      "sku_name": "Butter Croissant",
      "sku_category": "Pastry",
      "daypart": "Morning",
      "p10": 82,
      "p50": 100,
      "p90": 125,
      "opening_stock": 5,
      "recommended_prep": 105,
      "batch_size": 5,
      "waste_cost": 3.4,
      "stockout_cost": 5.1,
      "financial_exposure": {
        "stockout_exposure_rm": 132,
        "waste_exposure_rm": 38
      },
      "reason_summary": "Stockout cost is higher than waste cost, so prep is slightly above expected demand.",
      "replenishment": [
        {
          "ingredient_id": "butter",
          "ingredient_name": "Butter",
          "required_qty": 4.2,
          "current_stock": 2.6,
          "shortage_qty": 1.6,
          "unit": "kg"
        }
      ],
      "status": "pending_approval"
    }
  ]
}
```

### 4.2 Regenerate Plan

```http
POST /api/daily-plan/regenerate
```

Request:

```json
{
  "date": "2026-04-30",
  "reason": "manual_demo_refresh"
}
```

Response:

```json
{
  "forecast_run_id": "fr_20260430_002",
  "status": "generated",
  "message": "Daily plan regenerated successfully."
}
```

### 4.3 Manager Note Parser

```http
POST /api/gemini/parse-manager-note
```

Request:

```json
{
  "forecast_run_id": "fr_20260430_001",
  "note": "School group visiting Cheras community center tomorrow morning, expect more pastries."
}
```

Response:

```json
{
  "parsed_adjustment": {
    "outlet_id": "cheras_hub",
    "daypart": "Morning",
    "sku_category": "Pastry",
    "suggested_adjustment_pct": 15,
    "reason": "school group visit",
    "requires_confirmation": true
  },
  "explanation": "The note indicates additional morning pastry demand at Cheras Community Hub. Apply only after manager confirmation."
}
```

### 4.4 Apply Manager Note Adjustment

```http
POST /api/daily-plan/apply-adjustment
```

Request:

```json
{
  "forecast_run_id": "fr_20260430_001",
  "adjustment": {
    "outlet_id": "cheras_hub",
    "daypart": "Morning",
    "sku_category": "Pastry",
    "adjustment_pct": 15,
    "reason": "school group visit"
  }
}
```

Response:

```json
{
  "forecast_run_id": "fr_20260430_003",
  "status": "recomputed",
  "message": "Adjustment applied and daily plan recomputed."
}
```

### 4.5 Approval / Edit / Reject

```http
POST /api/daily-plan/recommendations/{recommendation_id}/decision
```

Request:

```json
{
  "operator_action": "edited",
  "final_prep": 110,
  "operator_reason": "Corporate breakfast order",
  "role": "outlet_manager"
}
```

Response:

```json
{
  "audit_event_id": "audit_001",
  "status": "recorded",
  "final_prep": 110
}
```

---

## 5. Workstream Breakdown

## Workstream 1 — ML/Data Owner

### Mission

Build the MLOps-ready LightGBM prototype using the ML guidebook.

### Files owned

```text
scripts/generate_demo_dataset.py
scripts/train_lightgbm.py
scripts/generate_forecast_artifacts.py
apps/api/ml/
models/
exports/
data/demo/
docs/ml/
```

### Step-by-step tasks

#### ML-1 — Generate demo dataset

Build:

```text
5 outlets × 12 SKUs × 3 dayparts × 180 days = 32,400 rows
```

Required rows:

```text
date
outlet_id
outlet_type
sku_id
sku_category
daypart
weekday
is_weekend
is_holiday
rain_mm
temperature
promo_flag
unit_price
unit_cost
true_demand
prep_qty
opening_stock
available_units
actual_sales
stockout_units
waste_units
stockout_flag
estimated_true_demand
```

Acceptance criteria:

- `exports/feature_table.csv` exists.
- Exactly 32,400 training rows unless intentionally filtered.
- No negative demand/sales/prep/waste values.
- Identity checks pass:

```text
actual_sales = min(estimated_true_demand, available_units)
stockout_units = max(estimated_true_demand - available_units, 0)
waste_units = max(available_units - estimated_true_demand, 0)
```

#### ML-2 — Implement feature engineering

Required v1 features:

```text
outlet_id
sku_id
sku_category
outlet_type
daypart
weekday
is_weekend
is_holiday
rain_mm
temperature
promo_flag
lag_1_sales
lag_7_sales
rolling_7d_mean
rolling_14d_mean
rolling_7d_std
stockout_flag_prev
recent_waste_rate
unit_price
```

Target:

```text
estimated_true_demand
```

Acceptance criteria:

- `models/feature_schema.json` exists.
- Feature columns match backend/frontend contract.
- Missing values are handled consistently.

#### ML-3 — Train LightGBM p50 model

Train one median/expected-demand model first.

Artifact:

```text
models/lightgbm_p50_v1.pkl
```

Acceptance criteria:

- Model artifact saved.
- Model can be loaded by backend `model_loader`.
- Prediction returns non-negative values.

#### ML-4 — Generate residual p10/p90 bands

Use validation residuals grouped by:

```text
sku_category + daypart
```

Fallback:

```text
global residual distribution
```

Artifact:

```text
models/residual_bands_v1.json
```

Acceptance criteria:

- Every SKU category + daypart has either group-specific or global fallback bands.
- `p10 <= p50 <= p90` after guardrails.

#### ML-5 — Model metrics

Calculate:

```text
WAPE
Bias
p10-p90 coverage
estimated mismatch cost delta
```

Artifact:

```text
models/model_metrics_v1.json
```

Acceptance criteria:

- Metrics are shown in expected JSON shape.
- Clearly labeled as POS-style demo validation, not production validation.

#### ML-6 — Handoff to Backend Owner

Provide:

```text
models/lightgbm_p50_v1.pkl
models/residual_bands_v1.json
models/feature_schema.json
models/model_metrics_v1.json
exports/feature_table.csv
exports/validation_predictions.csv
```

Do not change backend API shape without Backend Owner agreement.

---

## Workstream 2 — Backend/API Owner

### Mission

Implement the saved forecast-run architecture, optimizer, replenishment, approval, audit, and endpoint contracts.

### Files owned

```text
apps/api/models/
apps/api/schemas/
apps/api/routes/
apps/api/services/forecast_runs.py
apps/api/services/optimizer.py
apps/api/services/replenishment.py
apps/api/services/audit.py
apps/api/services/model_loader.py
apps/api/alembic/
```

### Step-by-step tasks

#### BE-1 — Create/align database tables

Minimum tables:

```text
model_runs
forecast_runs
forecast_lines
prep_recommendations
replenishment_recommendations
decision_audit_events
```

Acceptance criteria:

- Alembic migration exists.
- App does not rely on `create_all` except explicit local/dev seed mode.

#### BE-2 — Model artifact loader

Load:

```text
models/lightgbm_p50_v1.pkl
models/residual_bands_v1.json
models/feature_schema.json
models/model_metrics_v1.json
```

Fallback:

```text
baseline_heuristic
```

Acceptance criteria:

- If model loads, engine is `lightgbm_mlops_prototype`.
- If model missing/fails, engine is `baseline_heuristic` and model badge reflects fallback.

#### BE-3 — Implement forecast run generation

Endpoint:

```http
POST /api/daily-plan/regenerate
```

Process:

```text
load latest features
predict p50
apply residual bands
save forecast_run
save forecast_lines
run optimizer
save prep recommendations
run BOM/replenishment
save replenishment recommendations
return forecast_run_id
```

Acceptance criteria:

- Repeated calls create versioned forecast runs.
- UI reads latest saved run, not direct recomputation.

#### BE-4 — Implement financial optimizer

Inputs:

```text
p10, p50, p90
opening_stock
unit_price
unit_cost
batch_size
capacity
freshness_hours
```

Core logic:

```text
waste_cost = unit_cost - salvage_value
stockout_cost = unit_price - unit_cost
critical_ratio = stockout_cost / (stockout_cost + waste_cost)
recommended_demand_level = interpolate across p10/p50/p90
recommended_prep = max(recommended_demand_level - opening_stock, 0)
apply batch size
apply capacity
apply freshness rules
```

Acceptance criteria:

- No fractional prep output.
- Batch size respected.
- Capacity warning appears when capped.
- Recommended prep is explainable.

#### BE-5 — Implement BOM/replenishment

Process:

```text
recommended_prep × ingredient_per_unit
→ required ingredient quantity
→ compare with current stock
→ shortage quantity
→ replenishment recommendation
```

Acceptance criteria:

- At least one demo action shows ingredient shortage.
- Replenishment output ties clearly to prep recommendation.

#### BE-6 — Stock movement on approval/receipt

When prep plan is approved:

```text
ingredient_stock -= ingredients_required_for_approved_prep
```

When replenishment is marked received:

```text
ingredient_stock += received_qty
```

Acceptance criteria:

- Ingredient stock changes after approval/receipt.
- No negative ingredient stock without warning.

#### BE-7 — Decision audit log

Log:

```text
forecast_run_id
model_version
engine_name
p10/p50/p90
recommended_prep
final_prep
operator_action
operator_reason
gemini_note_adjustment_applied
gemini_note_summary
timestamp
```

Acceptance criteria:

- Approval/edit/reject creates audit event.
- Audit event visible in API and UI drawer.

#### BE-8 — Admin training endpoint

Endpoint:

```http
POST /admin/models/train
Authorization: Bearer ${ADMIN_API_TOKEN}
```

Acceptance criteria:

- Missing/invalid token returns 401/403.
- Endpoint can call training script or return a controlled stub if training is run manually.
- Does not expose model retraining publicly.

---

## Workstream 3 — Frontend/UI Owner

### Mission

Build the Daily Planning Workspace and all visible demo interactions.

### Files owned

```text
apps/web/src/app/daily-planning/
apps/web/src/components/planning/
apps/web/src/components/model-evidence/
apps/web/src/components/gemini/
apps/web/src/components/approval/
apps/web/src/lib/api/planning.ts
```

### Step-by-step tasks

#### FE-1 — Daily Planning Workspace page

Route:

```text
/daily-planning
```

Sections:

```text
Action Summary
Model Badge
Top Actions
Recommendation Cards
Replenishment Breakdown
Gemini Note Parser
Approval Side Drawer
Audit Preview
```

Acceptance criteria:

- Page opens directly into tomorrow’s plan.
- No broad fake dashboard is needed for demo.

#### FE-2 — Action summary first card

Show:

```text
Tomorrow’s action summary
- top prep action
- top reorder action
- top stockout/waste risk
- estimated mismatch cost reduction
```

Acceptance criteria:

- First screen communicates what operator should do.
- Compact model badge is visible nearby.

#### FE-3 — Compact model badge + evidence drawer

Compact badge:

```text
Engine: LightGBM MLOps prototype
Validation: Last 30 demo days
WAPE: 16.8%
Coverage: 78%
```

Drawer:

```text
model_version
target
training_rows
validation window
WAPE
bias
coverage
residual band method
status
```

Acceptance criteria:

- Badge is always visible near top.
- Drawer can be opened during technical Q&A.

#### FE-4 — Recommendation cards

Each card shows:

```text
outlet
SKU
daypart
p10/p50/p90 compact uncertainty bar
recommended prep marker
risk financial exposure
short reason summary
status
```

Acceptance criteria:

- p10/p50/p90 appears as range, not just table numbers.
- Recommended prep marker is visually obvious.

#### FE-5 — Filters

Tabs/filters:

```text
Top Actions
By Outlet
By SKU
By Risk
```

Acceptance criteria:

- Default is Top Actions.
- Outlet Manager role can filter to own outlet.

#### FE-6 — Replenishment breakdown

Show:

```text
Recommended prep
Ingredient need
Current stock
Shortage/reorder need
```

Optional if time:

```text
Generate supplier message
```

Acceptance criteria:

- Replenishment is visibly caused by prep recommendation.
- At least one ingredient shortage appears in demo.

#### FE-7 — Gemini inline explanation

Inside recommendation card or drawer:

```text
Why this recommendation?
```

Acceptance criteria:

- Explanation uses provided numbers only.
- Does not imply Gemini invented forecast/prep.

#### FE-8 — Manager note parser panel

Input:

```text
School group visiting Cheras community center tomorrow morning, expect more pastries.
```

Flow:

```text
Parse note
→ show structured adjustment
→ Apply / Edit / Ignore
→ recompute plan
```

Acceptance criteria:

- Adjustment is not applied silently.
- User must confirm.

#### FE-9 — Approval side drawer

Drawer contains:

```text
recommendation details
forecast evidence
cost tradeoff
ingredient impact
Gemini explanation
Approve/Edit/Reject
reason field
audit preview
```

Acceptance criteria:

- Edit/reject requires reason.
- Approve/edit/reject updates status and creates audit log.

---

## Workstream 4 — Integration/QA/Repo Cleanup Owner

### Mission

Keep the repo credible, prevent merge conflicts, remove demo-theater, coordinate integration, and prepare demo reliability.

### Files owned

```text
scripts/smoke_test_demo_flow.py
scripts/reset_demo_env.sh
README.md
.env.example
docs/demo/
docs/pitch/
apps/web/src/app/page.tsx
apps/web/src/navigation*
```

### Step-by-step tasks

#### INT-1 — Runtime correctness patch

Fix first:

```text
seed script total_base/wrong variable bug
DailyAgentState type mismatch
seed/docs outlet mismatch
hardcoded outlet assumptions
```

Acceptance criteria:

- App seeds without crash.
- Backend starts.
- Demo route loads.

#### INT-2 — Hide weak/non-core pages

Hide from visible navigation:

```text
synthetic dashboard pages
yearly trend charts
unfinished scenario pages
hardcoded demo pages
anything not tied to Daily Planning flow
```

Acceptance criteria:

- Presenter cannot accidentally click into fake-looking pages.
- Demo path is narrow and clean.

#### INT-3 — Replace fake chart references

Ensure no visible final demo uses:

```text
sine/cosine charts
pseudo-random yearly trends
hardcoded confidence score
```

Acceptance criteria:

- All visible metrics come from latest saved forecast run or model artifact.

#### INT-4 — Env and setup docs

Update:

```text
.env.example
README.md
docs/demo/runbook.md
```

Required commands:

```text
install dependencies
run migrations
seed old app data if needed
generate demo dataset
train model
generate forecast run
start backend
start frontend
run smoke test
```

Acceptance criteria:

- Another teammate can run demo setup from docs.

#### INT-5 — Backend smoke test script

Script:

```text
scripts/smoke_test_demo_flow.py
```

Checks:

```text
health endpoint
latest forecast run
generate plan
forecast lines exist
prep recommendations exist
replenishment exists
model badge data exists
manager note parse works
approval/edit/reject creates audit event
```

Acceptance criteria:

- Script exits non-zero on failure.
- Script prints clear pass/fail summary.

#### INT-6 — Manual frontend demo checklist

Create:

```text
docs/demo/manual_demo_checklist.md
```

Checklist:

```text
open Daily Planning
show action summary
open model evidence
open recommendation drawer
show uncertainty bar
show replenishment
parse manager note
apply adjustment
approve/edit plan
show audit log
```

Acceptance criteria:

- Team can rehearse same path consistently.

#### INT-7 — Merge coordinator

Responsibilities:

```text
review shared-file changes
resolve merge order
enforce naming freeze
stop duplicate route/schema definitions
run smoke test after merge
```

Acceptance criteria:

- No parallel edits to same shared contract file.
- Main branch is demo-stable after every integration merge.

---

## 6. Suggested Sequential Timeline

This timeline is designed to minimize merge conflicts.

## Phase 0 — Contract Freeze

**Goal:** prevent variable/API/schema chaos.

### Owner

Integration/QA Owner coordinates. All members review.

### Tasks

1. Create contract PR.
2. Freeze field names.
3. Freeze route names.
4. Freeze artifact file names.
5. Freeze response JSON examples.
6. Freeze UI sections.

### Must merge before

- Backend APIs
- Frontend UI integration
- ML artifact handoff

### Acceptance criteria

- Everyone agrees on canonical names.
- No one invents new versions of `forecast_id`, `predicted_qty`, `confidence`, etc.

---

## Phase 1 — Parallel Foundation Work

### Member 1 — ML Owner

Build:

```text
generate_demo_dataset.py
train_lightgbm.py
model artifacts
metrics
```

### Member 2 — Backend Owner

Build using mock artifacts first:

```text
tables
schemas
latest daily plan endpoint
optimizer
replenishment
audit endpoints
```

### Member 3 — Frontend Owner

Build against static/mock JSON matching frozen contract:

```text
Daily Planning Workspace
recommendation cards
model badge
drawer
manager-note panel
```

### Member 4 — Integration/QA Owner

Build:

```text
runtime bug fixes
hide weak routes
smoke test script skeleton
README setup updates
```

### Merge order

```text
1. Contract PR
2. Runtime cleanup PR
3. Backend schema/API PR
4. Frontend static UI PR
5. ML artifact PR
```

---

## Phase 2 — Backend + ML Integration

### Owner

Backend Owner + ML Owner.

### Tasks

1. Backend loads real `lightgbm_p50_v1.pkl`.
2. Backend loads `residual_bands_v1.json`.
3. Backend loads `model_metrics_v1.json`.
4. Regenerate endpoint creates saved forecast run.
5. Latest endpoint returns complete plan contract.
6. Baseline fallback works if artifact missing.

### Acceptance criteria

- `POST /api/daily-plan/regenerate` works.
- `GET /api/daily-plan/latest` returns p10/p50/p90 + prep + replenishment.
- UI can consume without extra mapping hacks.

---

## Phase 3 — Frontend + Backend Integration

### Owner

Frontend Owner + Backend Owner.

### Tasks

1. Replace mock data with API calls.
2. Confirm action summary uses latest forecast run.
3. Confirm model badge uses metrics from backend.
4. Confirm recommendation cards render p10/p50/p90.
5. Confirm approval drawer submits operator decision.
6. Confirm audit preview/created event works.

### Acceptance criteria

- Full flow works without manual database edits.
- No page makes direct model calls.
- All visible data comes from latest saved forecast run.

---

## Phase 4 — Gemini / Manager Note Integration

### Owner

Backend Owner + Frontend Owner.

### Tasks

1. Implement manager note parser endpoint.
2. Gemini returns structured adjustment only.
3. UI shows Apply / Edit / Ignore.
4. Apply adjustment triggers recomputed forecast/prep run.
5. Audit log records adjustment.

### Acceptance criteria

- Gemini does not silently change numbers.
- Adjustment is human-confirmed.
- Recomputed plan visibly changes prep/replenishment.

---

## Phase 5 — Repo Truthfulness and Demo Hardening

### Owner

Integration/QA Owner.

### Tasks

1. Remove fake charts from visible navigation.
2. Remove hardcoded confidence from visible UI.
3. Confirm all visible metrics are real from artifacts/API.
4. Run backend smoke test.
5. Run frontend demo checklist.
6. Freeze demo data.

### Acceptance criteria

- Presenter cannot accidentally click into weak pages.
- Smoke test passes.
- Demo flow rehearsed end-to-end.

---

## Phase 6 — Pitch and Q&A Alignment

### Owner

Integration/QA Owner + all members review.

### Tasks

1. Prepare final one-liner.
2. Prepare dataset answer.
3. Prepare LightGBM defense.
4. Prepare Gemini necessity answer.
5. Prepare MLOps champion/challenger answer.
6. Prepare limitations slide.
7. Prepare demo script.

### Acceptance criteria

- Every teammate can answer:

```text
What data did we use?
Why LightGBM?
Why Gemini?
Is this real or simulated?
Why not Excel?
How does this scale?
```

---

## 7. Branch and PR Strategy

### Branch names

```text
contract/freeze-planning-api
ml/demo-dataset-lightgbm
backend/forecast-run-optimizer
frontend/daily-planning-workspace
integration/demo-cleanup-smoke-tests
```

### PR size rule

Keep PRs small:

```text
Good:
- add model_runs table
- add latest daily plan endpoint
- add uncertainty bar component

Bad:
- rewrite forecast engine + UI + seed + Gemini in one PR
```

### Merge order rule

```text
1. contract/freeze-planning-api
2. integration/demo-cleanup-smoke-tests
3. backend/forecast-run-optimizer
4. frontend/daily-planning-workspace
5. ml/demo-dataset-lightgbm
6. integration final merge
```

If frontend needs to move before backend is ready, frontend must use mock JSON that exactly matches the contract.

---

## 8. Final Demo Flow

Presenter sequence:

```text
1. Open Tomorrow’s Daily Plan.
2. Show action summary first.
3. Point to compact model badge.
4. Open top recommendation card.
5. Explain p10/p50/p90 uncertainty bar.
6. Show recommended prep marker.
7. Show waste/stockout financial exposure.
8. Show prep-to-ingredient replenishment breakdown.
9. Show Gemini inline explanation.
10. Add manager note.
11. Gemini parses note into editable adjustment.
12. Apply adjustment.
13. Show recomputed prep + ingredient impact.
14. Approve/edit final plan.
15. Show audit log entry.
```

---

## 9. Acceptance Criteria for Final Build

The build is finals-ready only when all are true:

### Data / ML

- Demo dataset generated.
- LightGBM p50 model artifact exists.
- Residual p10/p90 bands exist.
- Model metrics exist.
- Latest forecast run can be generated.

### Backend

- Latest daily plan endpoint returns full contract.
- Regenerate endpoint works.
- Optimizer applies cost, batch size, capacity, freshness.
- BOM replenishment works.
- Approval/edit/reject creates audit log.
- Fallback baseline works if ML artifact fails.
- Admin training endpoint protected by token.

### Frontend

- Daily Planning Workspace loads.
- Action summary shown first.
- Recommendation cards show uncertainty bar.
- Model badge visible.
- Evidence drawer works.
- Replenishment breakdown visible.
- Gemini note parser flow works.
- Approval side drawer works.
- Audit preview/log visible.

### Repo Truthfulness

- No visible sine/cosine/random charts.
- No visible hardcoded confidence score.
- Weak/non-core pages hidden.
- Demo route is stable.
- Smoke test passes.

### Pitch

- Team can explain data honestly.
- Team can explain LightGBM choice.
- Team can explain Gemini role.
- Team can explain MLOps path.
- Team can explain limitations without sounding weak.

---

## 10. Biggest Merge Conflict Risks and Fixes

| Risk | Why It Happens | Prevention |
|---|---|---|
| Different names for p50/forecast | Teammates invent their own variable names | Naming freeze table; contract PR first |
| Frontend expects different JSON from backend | API shape not frozen | Static mock JSON based on frozen contract |
| ML artifacts not loadable by backend | Artifact paths/schema unclear | Artifact manifest JSON + backend loader test |
| Backend and ML both define features differently | Feature schema duplicated | ML owns `feature_schema.json`; backend reads it |
| Multiple people edit navigation/layout | UI cleanup and frontend build collide | Integration owner controls navigation/layout changes |
| Old heuristic accidentally still visible | Old endpoints still called by UI | Model badge + route audit + frontend API client cleanup |
| Smoke test breaks after merge | No integration checkpoint | Run smoke test after every integration merge |

---

## 11. What Not to Build Now

Do not spend finals time on:

```text
full production auth
Temporal.io
Supabase migration
feature store
full inventory ledger
supplier marketplace
RL / Thompson sampling
full POS integration
generic analytics dashboard
all historical pages
hourly forecasting
foundation model API integration
```

These are roadmap, not core finals build.

---

## 12. Final Recommendation

For the 4-person team, the cleanest execution split is:

```text
Member 1:
ML/Data pipeline and artifacts only.

Member 2:
Backend saved forecast run + optimizer + replenishment + audit APIs.

Member 3:
Daily Planning Workspace UI and demo interaction flow.

Member 4:
Repo cleanup, integration, smoke tests, setup docs, merge control, pitch support.
```

The highest priority build path is:

```text
1. Freeze contracts and names.
2. Build optimizer + prep/replenishment backend.
3. Generate ML artifacts.
4. Build Daily Planning UI against frozen contract.
5. Integrate latest saved forecast run.
6. Add Gemini note parser and approval audit.
7. Remove fake charts and hardcoded confidence.
8. Smoke test and rehearse demo.
```

The goal is not to build the broadest product. The goal is to make one workflow undeniable:

```text
forecast uncertainty
→ financially optimized prep
→ ingredient replenishment
→ Gemini explanation/context
→ human approval
→ audit trail
```

That is the finals-worthy Predictory.
