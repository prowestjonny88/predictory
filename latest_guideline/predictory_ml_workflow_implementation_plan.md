# Predictory ML Workflow & Implementation Plan

**Purpose:** convert all locked ML / data-pipeline / decision-engine decisions into a detailed implementation plan for the Predictory finals build.

**Product positioning:** **Predictory is the decision layer between yesterday's sales and tomorrow's bake.**

**Scope of this document:** ML workflow only — dataset construction, feature pipeline, LightGBM model, residual p10/p90 uncertainty, financial optimizer, replenishment link, Gemini grounding, MLOps-ready prototype, and engineering to-dos.

**Out of scope for this document:** repo cleanup, UI/UX final demo polish, pitch defense, and final execution plan. Those will be handled next in the sequence:

```text
A. Repo cleanup / technical debt
B. UI/UX final demo flow
C. Pitch and judging defense
D. Final execution plan
```

---

## 0. Locked Decisions Recap

These decisions were locked during the discussion and this plan follows them consistently.

### 0.1 Forecast / ML Direction

```text
MLOps-ready LightGBM prototype
```

Meaning:

- We are not using paid foundation-model APIs as the core.
- We are not claiming production accuracy from simulated/public data.
- We are demonstrating a working ML/MLOps-ready forecasting pipeline.
- In production, once real POS/ERP data is connected, the same pipeline retrains and validates on real outlet data.

### 0.2 Dataset Strategy

```text
French Bakery + FreshRetailNet grounding
```

Meaning:

```text
French Bakery dataset = real bakery demand foundation
FreshRetailNet = operational grounding / reference for stockout, weather, promo, inventory behavior
Python simulator = creates missing POS/ERP fields
LightGBM = trains on final Predictory-style feature table
```

Important:

```text
Do NOT directly join French Bakery rows with FreshRetailNet rows.
```

FreshRetailNet is used to guide realistic operational assumptions, not row-level merging.

### 0.3 Training Target

```text
target = estimated_true_demand
```

Not merely:

```text
target = actual_sales
```

Reason:

```text
actual_sales can be capped by stockout
estimated_true_demand better reflects unconstrained customer demand
```

### 0.4 Stockout Recovery

```text
Hybrid recovery with caps
```

Logic:

```text
If stockout timestamp exists:
  use velocity-based recovery

If stockout timestamp is missing:
  use historical uplift recovery

Always:
  cap the estimate to avoid absurd values
```

### 0.5 Forecast Output

```text
LightGBM p50 model now
+ residual p10/p90 bands from backtesting
+ true quantile models later
```

Reason:

- p50 model is easier and more stable.
- Residual bands provide p10/p90 without training three unstable quantile models immediately.
- Later, with real POS/ERP data, upgrade to true LightGBM quantile models.

### 0.6 Residual Band Granularity

```text
SKU category + daypart residual bands
+ global fallback
```

Example groups:

```text
Pastry + Morning
Bread + Morning
Cake + Evening
Sandwich + Midday
```

Fallback:

```text
If a group has too few validation residuals, use global residual distribution.
```

### 0.7 Optimizer Objective

```text
Minimize financial mismatch cost
```

Not simply unit accuracy.

The optimizer balances:

```text
waste cost if over-prep
stockout / lost margin cost if under-prep
```

### 0.8 SKU Economics

```text
Derive from price + assumed margin ratio, configurable later
```

Demo assumption:

```text
unit_cost = selling_price × assumed_cost_ratio
salvage_value = 0
waste_cost = unit_cost - salvage_value
stockout_cost = selling_price - unit_cost
```

Recommended default:

```text
assumed_cost_ratio = 0.40
```

### 0.9 Optimizer Constraints

```text
Batch size + capacity + freshness
```

Constraints in v1:

- Batch size rounding.
- Max daypart/outlet capacity.
- Freshness / carryover constraints.
- Optional minimum display quantity.

### 0.10 Demo Evidence

Show compact model health + business impact:

```text
Model health:
- WAPE
- Bias
- p10-p90 coverage
- Validation window

Decision impact:
- Estimated mismatch cost reduction
- Stockout exposure reduction
- Waste risk change
```

Use wording:

```text
Estimated impact on POS-style validation window
```

Do not say:

```text
Proven production waste reduction
```

### 0.11 Gemini Role

```text
Explanation + manager-note parser with human confirmation
```

Gemini should:

- Explain structured recommendations.
- Parse messy notes into structured assumptions.
- Require human confirmation before applying changes.

Gemini must not:

- Invent forecasts.
- Invent prep quantities.
- Calculate BOM requirements.
- Override optimizer output silently.

### 0.12 Human Flow

```text
Approve / edit / reject with reason
```

### 0.13 Hero Demo Workflow

```text
Prep + replenishment
with manager note scenario embedded
```

Hero flow:

```text
Forecast tomorrow demand
→ show p10/p50/p90
→ optimize prep quantities
→ convert prep into ingredient needs
→ flag shortage / waste / stockout risk
→ Gemini explains recommendation
→ manager adds note
→ Gemini parses note
→ system recomputes prep + replenishment
→ operator approves/edits/rejects final plan
```

### 0.14 Demo Cut Policy

```text
Hide weak/non-core pages
Demo only the hero workflow
```

### 0.15 First Major Build Priority

```text
Optimizer + prep/replenishment first
```

Rationale:

The decision layer is the product's core. The forecast model feeds it, but the winning demo is the end-to-end decision workflow.

---

## 1. Final ML System Architecture

### 1.1 High-Level Architecture

```text
French Bakery dataset
+ FreshRetailNet-grounded operational assumptions
+ Malaysian outlet/daypart simulation
        ↓
Predictory POS-style operational dataset
        ↓
Feature pipeline
        ↓
LightGBM p50 demand model
        ↓
Time-based validation residuals
        ↓
p10 / p50 / p90 demand forecast
        ↓
Financial mismatch optimizer
        ↓
Prep recommendation
        ↓
BOM ingredient expansion
        ↓
Replenishment recommendation
        ↓
Gemini grounded explanation
        ↓
Human approve / edit / reject
```

### 1.2 Separation of Responsibilities

| Layer | Responsibility | Should be ML/LLM? | Notes |
|---|---|---:|---|
| Data preparation | Clean and structure sales/inventory data | No | Deterministic ETL. |
| Demand forecast | Predict estimated true demand | ML | LightGBM p50 now. |
| Uncertainty | Convert p50 to p10/p90 | Statistical / backtest | Residual bands. |
| Prep optimization | Choose prep quantity | Deterministic math | Financial mismatch cost. |
| BOM replenishment | Calculate ingredient needs | Deterministic math | Prep × recipe. |
| Explanation | Explain recommendation | LLM | Gemini only explains structured evidence. |
| Approval | Human decision control | UI/workflow | Approve/edit/reject with reason. |
| Audit | Store decisions and changes | Deterministic logging | Needed for credibility. |

---

## 2. Dataset Construction Plan

### 2.1 Final Training Data Grain

One training row represents:

```text
date × outlet_id × sku_id × daypart
```

Example:

```text
2026-04-30 | Cheras Community Hub | Butter Croissant | Morning | estimated_true_demand = 80
2026-04-30 | Cheras Community Hub | Butter Croissant | Midday  | estimated_true_demand = 60
2026-04-30 | Cheras Community Hub | Butter Croissant | Evening | estimated_true_demand = 40
```

### 2.2 Final Dataset Size

```text
5 outlets × 12 SKUs × 3 dayparts × 180 days = 32,400 rows
```

This is the locked hackathon sweet spot:

- Enough rows for LightGBM prototype.
- Small enough to debug.
- Matches the 3-10 outlet bakery MSME target.
- Supports outlet/SKU/daypart interactions.

---

## 3. Data Sources and Roles

### 3.1 French Bakery Dataset

Role:

```text
Real bakery demand foundation
```

Use for:

- Product names / bakery SKUs.
- Quantity sold.
- Unit price.
- Timestamp-derived daypart patterns.
- Weekday/weekend demand rhythm.
- Item popularity.

Convert from:

```text
date, time, article, quantity, unit_price, ticket_number
```

Into base table:

```text
date, sku_raw_name, daypart, base_quantity_sold, unit_price
```

### 3.2 FreshRetailNet

Role:

```text
Operational grounding / reference
```

Use it to guide assumptions for:

- Stockout frequency.
- Stockout-censored demand behavior.
- Promo frequency and uplift ranges.
- Weather feature structure.
- Inventory/stock status logic.
- Hourly-to-daypart aggregation behavior.

Do not:

```text
Join FreshRetailNet rows directly to French Bakery rows.
```

### 3.3 Python Simulator

Role:

```text
Create missing POS/ERP operational fields
```

It generates:

- Multiple outlets.
- True demand.
- Prep quantity.
- Opening stock.
- Actual sales.
- Stockout units.
- Waste units.
- Ingredient stock.
- Replenishment events.
- Feature table fields.

### 3.4 Gemini / LLM

Role:

```text
Semantic/context augmentation only
```

Use for:

- Manager notes.
- Event descriptions.
- Product category mapping support.
- Explanation text.

Do not use for:

- Numeric time-series generation.
- Forecast numbers.
- Prep quantity.
- Ingredient calculations.

---

## 4. Demo Outlets

Use Malaysian realistic archetypes.

| Outlet | Archetype | Demand Behavior |
|---|---|---|
| Cheras Community Hub | Community/transit hub | Strong weekday morning rush; school-event spikes. |
| Setapak Town Center | Student/working-class corridor | Midday lift; price-sensitive demand. |
| Shah Alam Seksyen 7 | University/residential district | Afternoon peaks; weather-sensitive. |
| Kajang Town | Commuter town center | Morning commute demand; weekend bumps. |
| Klang Riverside | Industrial/port neighborhood | Early morning demand; steady staples. |

Implementation fields:

```text
outlet_id
outlet_name
outlet_type
base_multiplier
morning_multiplier
midday_multiplier
evening_multiplier
weather_sensitivity
premium_multiplier
capacity_by_daypart
```

Example outlet profile JSON:

```json
{
  "outlet_id": "cheras_hub",
  "outlet_name": "Cheras Community Hub",
  "outlet_type": "community_hub",
  "base_multiplier": 1.10,
  "daypart_multipliers": {
    "morning": 1.25,
    "midday": 1.05,
    "evening": 0.90
  },
  "weather_sensitivity": 0.25,
  "capacity_by_daypart": {
    "morning": 450,
    "midday": 380,
    "evening": 300
  }
}
```

---

## 5. Demo SKUs

Use French Bakery mapped SKUs.

Final 12 SKUs:

1. Traditional Baguette
2. Butter Croissant
3. Pain au Chocolat
4. Country Sourdough
5. Blueberry Muffin
6. Chocolate Cookie
7. Brownie
8. Fruit Tart
9. Cake Slice
10. Ham & Cheese Sandwich
11. Brioche
12. Coffee Bun / Sweet Bun

### 5.1 SKU Metadata

Each SKU should have:

```text
sku_id
sku_name
sku_category
selling_price
unit_cost_ratio
unit_cost
waste_cost
stockout_cost
freshness_hours
carryover_rate
batch_size
min_display_qty
```

Example:

```json
{
  "sku_id": "butter_croissant",
  "sku_name": "Butter Croissant",
  "sku_category": "Pastry",
  "selling_price": 8.50,
  "unit_cost_ratio": 0.40,
  "unit_cost": 3.40,
  "salvage_value": 0.00,
  "waste_cost": 3.40,
  "stockout_cost": 5.10,
  "freshness_hours": 12,
  "carryover_rate": 0.20,
  "batch_size": 5,
  "min_display_qty": 10
}
```

### 5.2 SKU Category Examples

```text
Bread:
- Traditional Baguette
- Country Sourdough

Pastry:
- Butter Croissant
- Pain au Chocolat
- Brioche
- Coffee Bun / Sweet Bun

Dessert:
- Blueberry Muffin
- Chocolate Cookie
- Brownie
- Fruit Tart
- Cake Slice

Savory:
- Ham & Cheese Sandwich
```

---

## 6. Dayparts

Locked dayparts:

```text
Morning
Midday
Evening
```

Suggested mapping from timestamp:

```text
Morning: 06:00-11:00
Midday: 11:00-16:00
Evening: 16:00-21:00
```

Implementation:

```python
def assign_daypart(hour: int) -> str:
    if 6 <= hour < 11:
        return "morning"
    if 11 <= hour < 16:
        return "midday"
    return "evening"
```

---

## 7. Dataset Generation Pipeline

### 7.1 Pipeline Overview

```text
Step 1: Load French Bakery raw transactions
Step 2: Normalize SKU names
Step 3: Assign daypart from time
Step 4: Aggregate to date × SKU × daypart
Step 5: Expand to 5 outlets
Step 6: Add calendar/weather/promo features
Step 7: Generate true demand
Step 8: Simulate naive human prep
Step 9: Apply opening stock carryover
Step 10: Calculate actual sales, waste, stockout
Step 11: Simulate ingredient stock/replenishment
Step 12: Generate lag and rolling features
Step 13: Write DB tables and CSV exports
```

---

## 8. Core Simulation Equations

### 8.1 True Demand

```text
true_demand =
  base_french_demand
  × outlet_factor
  × daypart_factor
  × promo_factor
  × weather_factor
  × holiday_factor
  × random_noise
```

Example:

```text
French croissant Saturday morning base = 100
Cheras outlet/daypart factor = 1.10
promo factor = 1.15
weather factor = 1.00
noise = 1.00

true_demand = 100 × 1.20 × 1.15 = 138
```

### 8.2 Historical Prep Simulation

Locked choice:

```text
naive human planner with outlet/SKU/daypart bias and noise
```

Formula:

```text
prep_qty =
  rolling_7d_actual_sales
  × outlet_bias
  × sku_bias
  × daypart_bias
  × random_noise
```

Example:

```text
rolling_7d_actual_sales = 100
outlet_bias = 1.05
sku_bias = 1.10
daypart_bias = 0.95
random_noise = 1.03

prep_qty ≈ 113
```

Reason:

This simulates human planning mistakes, producing both:

```text
overprep → waste
underprep → stockout
```

### 8.3 Opening Stock / Carryover

Locked choice:

```text
freshness-adjusted carryover by SKU
```

Formula:

```text
opening_stock_today = waste_units_yesterday × carryover_rate_by_sku
```

Example carryover rates:

```text
Croissant: 0.20
Baguette: 0.10
Cookie: 0.80
Cake Slice: 0.50
Brownie: 0.70
Sandwich: 0.00
Fruit Tart: 0.30
```

### 8.4 Available Units

```text
available_units = prep_qty + opening_stock
```

### 8.5 Actual POS Sales

```text
actual_sales = min(true_demand, available_units)
```

### 8.6 Stockout Units

```text
stockout_units = max(true_demand - available_units, 0)
stockout_flag = stockout_units > 0
```

### 8.7 Waste Units

```text
waste_units = max(available_units - true_demand, 0)
```

### 8.8 Identity Checks

Use these to validate simulator consistency:

```text
actual_sales + stockout_units = true_demand
actual_sales + waste_units = available_units
```

Allow minor rounding tolerance.

---

## 9. Stockout Recovery Logic

Even though the simulator knows `true_demand`, the production story needs stockout recovery.

### 9.1 Hybrid Recovery with Caps

```text
If stockout timestamp exists:
  estimate demand using velocity recovery

Else:
  estimate demand using historical uplift

Always:
  cap estimate using historical p90 / group cap
```

### 9.2 Velocity Recovery

Example:

```text
Outlet open 10 hours
Sold 80 units by hour 5
Sold out at hour 5

velocity_estimate = 80 × (10 / 5) = 160
```

### 9.3 Historical Uplift Recovery

Example:

```text
actual_sales = 80
historical_same_weekday_p50 = 100
historical_same_weekday_p90 = 130

historical_estimate = max(actual_sales, historical_p50)
```

### 9.4 Capping

Example:

```text
velocity_estimate = 160
historical_p90 = 130
cap = historical_p90 × 1.20 = 156

estimated_true_demand = min(160, 156) = 156
```

### 9.5 Implementation Function

```python
def recover_true_demand(
    actual_sales: float,
    stockout_flag: bool,
    stockout_hour: float | None,
    operating_hours: float,
    historical_p50: float,
    historical_p90: float,
    cap_multiplier: float = 1.20,
) -> float:
    if not stockout_flag:
        return actual_sales

    estimates = []

    if stockout_hour and stockout_hour > 0:
        velocity_estimate = actual_sales * (operating_hours / stockout_hour)
        estimates.append(velocity_estimate)

    historical_estimate = max(actual_sales, historical_p50)
    estimates.append(historical_estimate)

    raw_estimate = max(estimates)
    cap = historical_p90 * cap_multiplier

    return min(raw_estimate, cap)
```

---

## 10. Feature Table

### 10.1 LightGBM v1 Practical Feature Set

Locked features:

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

### 10.2 Avoid Leakage

Do not include these as features for the target day:

```text
actual_sales_today
true_demand_today
waste_units_today
stockout_units_today
future prep outcome
future approved quantity
```

These are outcomes, not known before forecast time.

### 10.3 Categorical Encoding

Recommended categorical features:

```text
outlet_id
sku_id
sku_category
outlet_type
daypart
weekday
```

Implementation options:

- Use pandas category dtype and LightGBM categorical support.
- Or one-hot encode for simplicity.

For hackathon reliability:

```text
One-hot encoding is simpler and easier to debug.
```

For production-readiness:

```text
LightGBM categorical features are cleaner if implemented correctly.
```

Recommendation:

```text
Use one-hot encoding in v1 unless team is confident with LightGBM categorical handling.
```

### 10.4 Feature Table Example

```text
date: 2026-04-30
outlet_id: cheras_hub
sku_id: butter_croissant
sku_category: Pastry
outlet_type: mall_office
daypart: morning
weekday: Thursday
is_weekend: 0
is_holiday: 0
rain_mm: 8.2
temperature: 31.0
promo_flag: 0
lag_1_sales: 52
lag_7_sales: 58
rolling_7d_mean: 55.4
rolling_14d_mean: 53.1
rolling_7d_std: 7.8
stockout_flag_prev: 1
recent_waste_rate: 0.06
unit_price: 8.50
estimated_true_demand: 64
```

---

## 11. Model Training Workflow

### 11.1 Model Type

V1:

```text
LightGBM p50 regression model
```

Target:

```text
estimated_true_demand
```

Output:

```text
p50 forecast
```

p10/p90 derived from validation residuals.

### 11.2 Time-Based Split

Do not use random train/test split.

Use time-based validation:

```text
Training window: first 150 days
Validation window: last 30 days
```

For 180-day dataset:

```text
Train: days 1-150
Validate: days 151-180
```

Optional rolling backtest:

```text
Fold 1: Train days 1-90, validate days 91-120
Fold 2: Train days 1-120, validate days 121-150
Fold 3: Train days 1-150, validate days 151-180
```

For finals, minimum acceptable:

```text
single last-30-days validation window
```

Preferred:

```text
rolling validation if time allows
```

### 11.3 Training Steps

```text
1. Build feature table.
2. Sort by date.
3. Split into train/validation by date.
4. Train LightGBM p50 model.
5. Predict validation p50.
6. Calculate residuals: actual_estimated_true_demand - predicted_p50.
7. Calculate residual bands by SKU category + daypart.
8. Calculate global residual fallback.
9. Save model artifact.
10. Save residual bands.
11. Save feature schema.
12. Save model metrics.
13. Insert model_runs row.
```

### 11.4 Residual Band Calculation

For each group:

```text
group = sku_category + daypart
```

Calculate:

```text
lower_error = 10th percentile residual
upper_error = 90th percentile residual
```

Then forecast:

```text
p10 = max(0, p50 + lower_error)
p90 = max(p50, p50 + upper_error)
```

Fallback:

```text
If group residual count < min_samples:
  use global lower_error / upper_error
```

Recommended default:

```text
min_samples = 50
```

### 11.5 Quantile Crossing Guardrail

Since p50 + residual bands should rarely cross, still enforce:

```text
p10 = max(0, p10)
p50 = max(p10, p50)
p90 = max(p50, p90)
```

### 11.6 Model Artifact Structure

```text
models/
  lightgbm_p50_v1.pkl
  residual_bands_v1.json
  feature_schema_v1.json
  model_metrics_v1.json
```

Example `residual_bands_v1.json`:

```json
{
  "global": {
    "lower_error_p10": -18.0,
    "upper_error_p90": 25.0,
    "n": 9720
  },
  "Pastry__morning": {
    "lower_error_p10": -16.0,
    "upper_error_p90": 28.0,
    "n": 860
  },
  "Bread__morning": {
    "lower_error_p10": -12.0,
    "upper_error_p90": 20.0,
    "n": 900
  }
}
```

---

## 12. Validation Metrics

Locked metrics:

```text
WAPE
Bias
p10-p90 coverage
Estimated business impact
```

### 12.1 WAPE

```text
WAPE = sum(abs(actual - forecast)) / sum(actual)
```

Use:

```text
actual = estimated_true_demand
forecast = p50
```

### 12.2 Bias

```text
Bias = sum(forecast - actual) / sum(actual)
```

Interpretation:

```text
Positive bias = overforecasting
Negative bias = underforecasting
```

### 12.3 p10-p90 Coverage

```text
coverage = count(actual between p10 and p90) / total rows
```

Expected:

```text
For p10-p90 interval, ideal coverage is around 80%.
```

Since this is a prototype, show:

```text
p10-p90 coverage: 78%
```

or whatever actual validation produces.

### 12.4 Business Impact

Compare:

```text
naive human prep plan
vs
Predictory optimized prep plan
```

Calculate total mismatch cost:

```text
total_mismatch_cost = waste_cost × waste_units + stockout_cost × stockout_units
```

For baseline:

```text
baseline_cost = cost from historical naive prep
```

For Predictory:

```text
predictory_cost = cost from optimizer recommendation using predicted p10/p50/p90
```

Impact:

```text
cost_reduction_pct = (baseline_cost - predictory_cost) / baseline_cost
```

UI wording:

```text
Estimated mismatch cost ↓ 12% on POS-style validation window
```

Do not say:

```text
Proven 12% waste reduction in production
```

---

## 13. Optimizer Workflow

### 13.1 Inputs

For each forecast line:

```text
p10
p50
p90
opening_stock
selling_price
unit_cost
salvage_value
waste_cost
stockout_cost
batch_size
max_capacity
freshness_hours
min_display_qty
```

### 13.2 Cost Definitions

```text
waste_cost = unit_cost - salvage_value
stockout_cost = selling_price - unit_cost
```

Demo default:

```text
salvage_value = 0
unit_cost = selling_price × 0.40
```

### 13.3 Critical Ratio

```text
CR = stockout_cost / (stockout_cost + waste_cost)
```

Interpretation:

```text
High CR → stockout is expensive → prep closer to p90
Low CR → waste is expensive → prep closer to p10/p50
```

### 13.4 Convert CR to Target Demand

Using p10/p50/p90 interpolation:

```text
If CR <= 0.10:
  target_demand = p10

If 0.10 < CR <= 0.50:
  interpolate between p10 and p50

If 0.50 < CR <= 0.90:
  interpolate between p50 and p90

If CR > 0.90:
  target_demand = p90
```

Example:

```text
p10 = 80
p50 = 100
p90 = 125
stockout_cost = 5.10
waste_cost = 3.40
CR = 5.10 / (5.10 + 3.40) = 0.60

CR is between p50 and p90.
position = (0.60 - 0.50) / (0.90 - 0.50) = 0.25
target_demand = 100 + 0.25 × (125 - 100) = 106.25
```

### 13.5 Raw Prep

```text
raw_prep = max(target_demand - opening_stock, 0)
```

### 13.6 Batch Size Rounding

```text
rounded_prep = round_to_nearest_batch(raw_prep, batch_size)
```

Recommended:

```text
Use ceil to avoid under-prepping for high-margin items.
Use nearest for balanced items.
```

Simpler v1:

```text
rounded_prep = ceil(raw_prep / batch_size) × batch_size
```

### 13.7 Capacity Constraint

```text
final_prep = min(rounded_prep, max_capacity)
```

If capped:

```text
capacity_warning = true
capacity_gap = rounded_prep - max_capacity
```

### 13.8 Minimum Display Quantity

```text
final_prep = max(final_prep, min_display_qty)
```

Optional. Use only if demo needs shelf-presence logic.

### 13.9 Freshness Constraint

Use freshness/carryover metadata to avoid assuming all leftovers are reusable.

Example:

```text
If SKU freshness_hours <= 12:
  carryover_rate low
  waste_cost remains high
```

For v1, freshness mostly affects:

```text
carryover_rate
waste_cost explanation
```

### 13.10 Optimizer Output

```json
{
  "forecast_line_id": "...",
  "p10": 80,
  "p50": 100,
  "p90": 125,
  "opening_stock": 5,
  "critical_ratio": 0.60,
  "target_demand": 106,
  "raw_prep": 101,
  "batch_size": 5,
  "recommended_prep": 105,
  "capacity_warning": false,
  "reason_code": "stockout_cost_above_waste_cost",
  "rationale": "Stockout cost is higher than waste cost, so prep is above median demand."
}
```

---

## 14. BOM and Replenishment Workflow

### 14.1 Practical BOM

Locked choice:

```text
4-6 ingredients per SKU
```

Example:

```text
Butter Croissant:
- flour: 0.08 kg / unit
- butter: 0.04 kg / unit
- sugar: 0.01 kg / unit
- yeast: 0.003 kg / unit
- egg wash: 0.02 unit / unit
```

### 14.2 Ingredient Need

```text
ingredient_required = recommended_prep × ingredient_qty_per_unit
```

Example:

```text
recommended_prep = 105 croissants
butter_per_unit = 0.04 kg
butter_required = 105 × 0.04 = 4.2 kg
```

### 14.3 Replenishment Need

```text
reorder_qty = max(required_qty - current_stock, 0)
```

Example:

```text
butter_required = 4.2 kg
current_butter_stock = 2.6 kg
reorder_qty = 1.6 kg
```

### 14.4 Simple Replenishment Simulation

Locked choice:

```text
Simulated ingredient stock with daily consumption and simple replenishment
```

Formula:

```text
next_day_stock = opening_stock - ingredient_used + replenishment_received
```

Simple reorder assumption:

```text
If stock < next_day_required × coverage_threshold:
  create replenishment recommendation
```

Recommended default:

```text
coverage_threshold = 1.0 day
```

Optionally:

```text
coverage_threshold = 1.5 days for critical ingredients like butter/flour
```

### 14.5 Replenishment Output

```json
{
  "ingredient": "Butter",
  "required_qty": 4.2,
  "current_stock": 2.6,
  "reorder_qty": 1.6,
  "unit": "kg",
  "urgency": "high",
  "driving_skus": ["Butter Croissant", "Brioche", "Cake Slice"],
  "reason": "Current butter stock covers only 62% of tomorrow's recommended production."
}
```

---

## 15. Gemini Grounding Workflow

### 15.1 Explanation Input JSON

Gemini receives structured data only.

Example:

```json
{
  "outlet": "Cheras Community Hub",
  "sku": "Butter Croissant",
  "daypart": "Morning",
  "forecast": {
    "p10": 80,
    "p50": 100,
    "p90": 125
  },
  "optimizer": {
    "recommended_prep": 105,
    "opening_stock": 5,
    "critical_ratio": 0.60,
    "waste_cost": 3.40,
    "stockout_cost": 5.10,
    "reason_code": "stockout_cost_above_waste_cost"
  },
  "replenishment": [
    {
      "ingredient": "Butter",
      "required_qty": 4.2,
      "current_stock": 2.6,
      "reorder_qty": 1.6,
      "unit": "kg"
    }
  ],
  "model_status": {
    "engine": "LightGBM p50 + residual uncertainty",
    "status": "MLOps prototype",
    "validation_window": "last 30 POS-style demo days"
  }
}
```

### 15.2 Explanation Output

Gemini should produce:

```text
Prepare 105 butter croissants for Cheras Community Hub morning. Expected demand is around 100 units, with a high-demand scenario of 125. Because croissant stockouts lose more margin than small leftovers cost, the optimizer recommends preparing slightly above expected demand. This plan requires 4.2 kg of butter, but current stock is only 2.6 kg, so order at least 1.6 kg before production.
```

### 15.3 Manager Note Parser

Input:

```text
School group visiting Cheras community center tomorrow morning, expect more pastries.
```

Gemini structured output:

```json
{
  "outlet": "cheras_hub",
  "daypart": "morning",
  "sku_category": "Pastry",
  "suggested_adjustment_pct": 15,
  "reason": "school group visit",
  "requires_confirmation": true
}
```

UI asks:

```text
Apply +15% pastry demand adjustment to Cheras Community Hub morning?
[Apply] [Edit] [Ignore]
```

Only after confirmation:

```text
recompute forecast adjustment / optimizer / replenishment
```

### 15.4 LLM Guardrail Prompt Principles

Prompt must include:

```text
Use only the provided structured numbers.
Do not invent forecasts, quantities, costs, or metrics.
If a number is missing, say it is unavailable.
Explain the recommendation in plain operator language.
Clearly separate model evidence from business assumption.
Do not present demo validation as production proof.
```

---

## 16. Storage and Artifacts

### 16.1 Locked Storage Choice

```text
Database tables + model artifacts
with CSV exports for debugging
```

### 16.2 Recommended Database Tables

```text
outlet_master
sku_master
ingredient_master
recipe_bom
sales_facts
inventory_snapshots
waste_logs
forecast_features
model_runs
forecast_runs
forecast_lines
prep_recommendations
replenishment_recommendations
approval_events
```

### 16.3 Minimum Required Tables for ML Demo

If time is limited, prioritize:

```text
outlet_master
sku_master
ingredient_master
recipe_bom
sales_facts
forecast_features
model_runs
forecast_runs
forecast_lines
prep_recommendations
replenishment_recommendations
approval_events
```

### 16.4 Model Artifacts

```text
models/lightgbm_p50_v1.pkl
models/residual_bands_v1.json
models/feature_schema_v1.json
models/model_metrics_v1.json
```

### 16.5 Debug Exports

```text
exports/feature_table.csv
exports/validation_predictions.csv
exports/prep_recommendations.csv
exports/replenishment_recommendations.csv
```

---

## 17. Training Trigger

Locked choice:

```text
Manual script + backend admin endpoint
```

### 17.1 Manual Script

```bash
python scripts/train_lightgbm.py
```

Responsibilities:

```text
build feature table
train LightGBM p50
run validation
calculate residual bands
save artifacts
insert model_runs row
export debug CSVs
```

### 17.2 Admin Endpoint

```http
POST /admin/models/train
```

Response:

```json
{
  "model_version": "lightgbm_p50_v1",
  "status": "challenger",
  "training_rows": 32400,
  "validation_window": "last_30_days",
  "wape": 0.168,
  "bias": -0.021,
  "p10_p90_coverage": 0.78,
  "artifact_path": "models/lightgbm_p50_v1.pkl",
  "residual_bands_path": "models/residual_bands_v1.json"
}
```

Important:

```text
Hide/protect admin endpoint in demo.
```

---

## 18. Forecast Generation in App

Locked choice:

```text
Hybrid: read latest forecast run by default, allow manual regenerate
```

### 18.1 Default Behavior

```text
UI loads latest forecast_run
UI displays saved forecast_lines and prep recommendations
```

### 18.2 Manual Regenerate

```http
POST /forecast-runs/generate
```

Behavior:

```text
load active model artifact
build tomorrow feature rows
predict p50
apply residual bands
save forecast_run
save forecast_lines
run optimizer
save prep_recommendations
run BOM expansion
save replenishment_recommendations
return forecast_run_id
```

### 18.3 Why Not Live on Page Load

Avoid:

```text
page load → slow model call → inconsistent output → demo risk
```

Use saved run for:

- Stability.
- Auditability.
- Performance.
- Explainability.

---

## 19. API Design

### 19.1 ML / Training APIs

```http
POST /admin/models/train
GET  /admin/models/latest
GET  /admin/models/{model_run_id}
```

### 19.2 Forecast APIs

```http
POST /forecast-runs/generate
GET  /forecast-runs/latest
GET  /forecast-runs/{forecast_run_id}
GET  /forecast-runs/{forecast_run_id}/lines
```

### 19.3 Prep / Replenishment APIs

```http
GET  /prep-plans/latest
GET  /prep-plans/{forecast_run_id}
POST /prep-plans/{plan_id}/approve
POST /prep-plans/{plan_id}/edit
POST /prep-plans/{plan_id}/reject
GET  /replenishment/latest
```

### 19.4 Gemini APIs

```http
POST /copilot/explain-recommendation
POST /copilot/parse-manager-note
POST /copilot/apply-note-adjustment
```

Important:

```text
parse-manager-note should only return suggested structured assumptions.
apply-note-adjustment should require explicit user confirmation.
```

---

## 20. UI Model Status Wording

Locked wording:

```text
Model status: MLOps prototype
Engine: LightGBM p50 + residual uncertainty
Validation: Validated on POS-style demo window
Production path: Ready for POS/ERP retraining
```

Do not say:

```text
Production validated
Real customer-trained model
Guaranteed accuracy
```

---

## 21. UI Evidence Block

Compact block:

```text
Model health
WAPE: 16.8%
Bias: -2.1%
p10-p90 coverage: 78%
Validation: last 30 POS-style demo days

Decision impact
Estimated mismatch cost: ↓ 12%
Stockout exposure reduced: RM 132
Waste risk: medium → low
```

Use actual validation numbers generated by the pipeline.

If numbers are not ready, use labels like:

```text
Pending validation run
```

Do not invent final numbers in production UI.

---

## 22. Implementation File Structure

Recommended backend structure:

```text
apps/api/
  ml/
    __init__.py
    build_features.py
    train_lightgbm.py
    predict.py
    residual_bands.py
    metrics.py
    registry.py
    schemas.py

  simulation/
    load_french_bakery.py
    sku_mapping.py
    outlet_profiles.py
    demand_simulator.py
    prep_simulator.py
    inventory_simulator.py
    bom_seed.py
    generate_demo_dataset.py

  optimization/
    prep_optimizer.py
    cost_models.py
    constraints.py

  replenishment/
    bom_expansion.py
    stock_projection.py
    reorder_rules.py

  copilot/
    prompts.py
    explanation.py
    note_parser.py

scripts/
  generate_demo_dataset.py
  train_lightgbm.py
  generate_forecast_run.py

models/
  lightgbm_p50_v1.pkl
  residual_bands_v1.json
  feature_schema_v1.json
  model_metrics_v1.json

exports/
  feature_table.csv
  validation_predictions.csv
  prep_recommendations.csv
```

If current repo already has similar folders, adapt names to existing conventions rather than forcing a full restructure.

---

## 23. Step-by-Step Implementation Plan

### Phase 1 — Data Foundation

#### Step 1.1 Load French Bakery Raw Data

To-do:

- Download/load French Bakery dataset.
- Parse `date`, `time`, `article`, `quantity`, `unit_price`.
- Clean article names.
- Drop irrelevant rows/items.
- Convert timestamps.

Output:

```text
raw_bakery_transactions dataframe
```

Acceptance criteria:

- No null dates.
- No negative quantities.
- Item names normalized.
- Unit price available for mapped SKUs.

#### Step 1.2 Map Raw Articles to 12 SKUs

To-do:

- Create mapping dictionary from raw French item names to 12 Predictory SKUs.
- Assign `sku_category`.
- Assign default selling price if missing.

Output:

```text
sku_master
normalized transaction table
```

Acceptance criteria:

- 12 SKUs present.
- Each SKU has category and price.
- Unmapped items either excluded or grouped intentionally.

#### Step 1.3 Assign Dayparts

To-do:

- Morning: 06:00-11:00.
- Midday: 11:00-16:00.
- Evening: 16:00-21:00.
- Aggregate to date × sku × daypart.

Output:

```text
base_bakery_demand
```

Acceptance criteria:

- Date × SKU × daypart rows exist.
- Quantities are non-negative.
- Daypart distribution looks plausible.

---

### Phase 2 — Multi-Outlet Simulation

#### Step 2.1 Create Outlet Profiles

To-do:

- Seed 5 outlets.
- Add outlet type and daypart multipliers.
- Add capacity by daypart.
- Add weather sensitivity.

Output:

```text
outlet_master
```

Acceptance criteria:

- 5 outlets exist.
- Each has clear archetype.
- Capacity exists for each daypart.

#### Step 2.2 Expand Base Demand to Outlets

To-do:

- Cross base demand rows with outlet profiles.
- Apply outlet/daypart multipliers.
- Apply SKU/outlet preferences.

Output:

```text
outlet_base_demand
```

Acceptance criteria:

- Row count approaches 32,400 after full generation.
- Cheras/Setapak/Shah Alam/Kajang/Klang patterns differ.

#### Step 2.3 Add Calendar / Weather / Promo

To-do:

- Add weekday, weekend flag.
- Add Malaysia holiday flag.
- Generate weather fields: `rain_mm`, `temperature`.
- Generate `promo_flag` with reasonable frequency.

Output:

```text
demand_context_table
```

Acceptance criteria:

- Weekday/weekend fields valid.
- Weather fields realistic enough.
- Promo frequency not excessive.

#### Step 2.4 Generate True Demand

To-do:

- Apply true demand formula.
- Add bounded noise.
- Round to integer units.
- Ensure no negative demand.

Output:

```text
true_demand table
```

Acceptance criteria:

- `true_demand >= 0`.
- Outlet/daypart/SKU differences visible.
- No absurd spikes unless controlled event/promo exists.

---

### Phase 3 — Operational Simulation

#### Step 3.1 Simulate Historical Prep

To-do:

- Calculate rolling 7-day actual sales after enough history.
- For first 7 days, use base demand or category average.
- Apply outlet/SKU/daypart biases and noise.
- Round to batch size.

Output:

```text
prep_qty
```

Acceptance criteria:

- Prep differs from true demand.
- Both waste and stockout cases exist.
- No oracle behavior.

#### Step 3.2 Apply Opening Stock Carryover

To-do:

- Use freshness-adjusted carryover by SKU.
- `opening_stock_today = previous_leftover × carryover_rate`.
- For first day, use small seeded stock.

Output:

```text
opening_stock
```

Acceptance criteria:

- Perishable items have low carryover.
- Cookies/brownies have higher carryover.
- Opening stock is non-negative.

#### Step 3.3 Calculate Sales, Waste, Stockout

To-do:

- Calculate available units.
- Calculate actual sales.
- Calculate waste.
- Calculate stockout units/flag.

Output:

```text
sales_facts
waste_logs
stockout flags
```

Acceptance criteria:

- Identity checks pass.
- Stockout rate is plausible.
- Waste rate is plausible.

#### Step 3.4 Estimate True Demand

To-do:

- In simulated data, store true demand.
- Also implement hybrid recovery method to show production path.
- Generate `estimated_true_demand`.

Output:

```text
estimated_true_demand
```

Acceptance criteria:

- For no stockout: estimated true demand = actual sales or close.
- For stockout: estimated true demand >= actual sales.
- Estimates are capped.

---

### Phase 4 — BOM and Ingredient Inventory

#### Step 4.1 Seed Practical BOM

To-do:

- Create 4-6 ingredients per SKU.
- Define quantity per unit.
- Use realistic units: kg, units, liters.

Output:

```text
recipe_bom
ingredient_master
```

Acceptance criteria:

- Each SKU has BOM.
- Butter/flour/yeast/sugar/egg appear across multiple SKUs.
- Ingredient units are consistent.

#### Step 4.2 Simulate Ingredient Stock

To-do:

- Seed opening ingredient stock.
- Subtract ingredient consumption from historical prep.
- Add simple replenishment received events.
- Keep stock non-negative where possible; log shortages if negative risk.

Output:

```text
ingredient_inventory_snapshots
```

Acceptance criteria:

- Ingredient stock changes over time.
- Shortage/reorder cases appear.
- Replenishment demo feels earned, not staged.

---

### Phase 5 — Feature Pipeline

#### Step 5.1 Build Feature Table

To-do:

- Generate features for each date × outlet × SKU × daypart.
- Lag features use prior actual/estimated demand only.
- Rolling features use historical windows only.
- Add context and metadata features.

Output:

```text
forecast_features
exports/feature_table.csv
```

Acceptance criteria:

- No future leakage.
- Features match feature schema.
- Missing lags handled.
- Row count ≈ 32,400 minus warmup if dropping early days.

#### Step 5.2 Validate Feature Table

To-do:

- Check nulls.
- Check date order.
- Check target distribution.
- Check categorical values.
- Check feature leakage.

Acceptance criteria:

- Training script runs without manual cleanup.
- Debug export is inspectable.

---

### Phase 6 — Model Training

#### Step 6.1 Train LightGBM p50

To-do:

- Split train/validation by date.
- Train p50 model.
- Save artifact.

Output:

```text
models/lightgbm_p50_v1.pkl
```

Acceptance criteria:

- Model trains in < few minutes.
- Predictions are non-negative after clipping.
- Validation metrics generated.

#### Step 6.2 Calculate Residual Bands

To-do:

- Predict validation p50.
- Calculate residuals.
- Group residuals by SKU category + daypart.
- Save p10/p90 residual errors.
- Save global fallback.

Output:

```text
models/residual_bands_v1.json
```

Acceptance criteria:

- Each major category/daypart has bands or fallback.
- p10/p90 coverage computed.

#### Step 6.3 Save Model Metrics

To-do:

- WAPE.
- Bias.
- p10-p90 coverage.
- Business impact.
- Training rows.
- Validation window.

Output:

```text
models/model_metrics_v1.json
model_runs table row
```

Acceptance criteria:

- UI can display model status.
- Metrics are labelled as demo/POS-style validation.

---

### Phase 7 — Forecast Run Generation

#### Step 7.1 Build Tomorrow Feature Rows

To-do:

- For selected forecast date, generate feature rows for all outlet × SKU × daypart combinations.
- Use latest historical lags/rolling windows.
- Add tomorrow weather/holiday/promo assumptions.

Output:

```text
tomorrow_feature_rows
```

Acceptance criteria:

- 5 × 12 × 3 = 180 forecast lines per forecast date.

#### Step 7.2 Predict p50 and Apply Residual Bands

To-do:

- Load model artifact.
- Predict p50.
- Use residual band by category/daypart.
- Apply global fallback if needed.
- Enforce p10 ≤ p50 ≤ p90.

Output:

```text
forecast_lines
```

Acceptance criteria:

- Every forecast line has p10, p50, p90.
- No negative forecasts.
- No quantile crossing.

#### Step 7.3 Save Forecast Run

To-do:

- Insert `forecast_runs` row.
- Insert `forecast_lines` rows.
- Attach model version.

Acceptance criteria:

- UI can read latest forecast run.
- Forecast run is stable across refresh.

---

### Phase 8 — Optimization and Replenishment

#### Step 8.1 Run Prep Optimizer

To-do:

- For each forecast line, calculate stockout/waste costs.
- Calculate critical ratio.
- Convert p10/p50/p90 into target demand.
- Subtract opening stock.
- Apply batch, capacity, freshness constraints.
- Save recommendation.

Output:

```text
prep_recommendations
```

Acceptance criteria:

- Recommendation is integer/batch-rounded.
- Capacity warnings generated where needed.
- Rationale exists for each recommendation.

#### Step 8.2 Run BOM Expansion

To-do:

- For approved/recommended prep quantities, calculate ingredient need.
- Aggregate across SKUs/outlets/dayparts as needed.
- Compare with current ingredient stock.
- Generate reorder suggestions.

Output:

```text
replenishment_recommendations
```

Acceptance criteria:

- Ingredient shortages shown.
- Driving SKUs listed.
- Quantities are numerically correct.

---

### Phase 9 — Gemini Explanation and Manager Notes

#### Step 9.1 Generate Explanation

To-do:

- Build rationale JSON.
- Call Gemini/LiteLLM with guardrailed prompt.
- Save explanation output.

Acceptance criteria:

- Explanation uses provided numbers only.
- No hallucinated quantities.
- Explanation is understandable for operator.

#### Step 9.2 Manager Note Parser

To-do:

- Input manager note.
- Gemini returns structured adjustment suggestion.
- UI asks user to apply/edit/ignore.
- If applied, regenerate affected forecast/optimizer lines.

Acceptance criteria:

- Gemini output is structured.
- Human confirmation required.
- Audit event stored.

---

### Phase 10 — Approval and Audit

#### Step 10.1 Approve / Edit / Reject

To-do:

- Add actions for prep recommendation.
- Store final quantity.
- Store reason.
- Store user/timestamp.

Output:

```text
approval_events
final_prep_plan
```

Acceptance criteria:

- Operator can approve/edit/reject.
- Changes are visible in audit history.
- Final plan differs from recommendation when edited.

---

## 24. Acceptance Criteria for the ML Workflow

The ML workflow is considered successful if:

1. Feature table contains ~32,400 rows at date × outlet × SKU × daypart grain.
2. LightGBM p50 model trains successfully.
3. p10/p90 residual bands are generated by SKU category + daypart with global fallback.
4. Forecast run produces 180 lines for tomorrow.
5. Every forecast line has valid p10 ≤ p50 ≤ p90.
6. Prep optimizer produces practical recommended prep quantities.
7. BOM replenishment produces ingredient needs and shortage suggestions.
8. Model status block displays WAPE, bias, p10-p90 coverage, and estimated business impact.
9. Gemini explanation uses only structured data.
10. Manager note parser requires human confirmation.
11. Operator can approve/edit/reject recommendations with reason.
12. No claim is made that simulated validation equals production accuracy.

---

## 25. Engineering To-Do Checklist

### Data Simulation To-Dos

- [ ] Load French Bakery raw dataset.
- [ ] Normalize article names.
- [ ] Map items to 12 SKUs.
- [ ] Assign SKU categories.
- [ ] Assign unit prices and cost ratios.
- [ ] Assign dayparts.
- [ ] Aggregate date × SKU × daypart base demand.
- [ ] Seed 5 Malaysian outlet archetypes.
- [ ] Expand demand across outlets.
- [ ] Generate weather/holiday/promo fields.
- [ ] Generate true demand.
- [ ] Simulate naive human prep.
- [ ] Simulate freshness-adjusted carryover.
- [ ] Calculate actual sales, stockout, waste.
- [ ] Implement hybrid stockout recovery.
- [ ] Seed practical BOM.
- [ ] Simulate ingredient stock and replenishment.
- [ ] Export feature table.

### ML Training To-Dos

- [ ] Build feature table from DB/dataframe.
- [ ] Ensure no future leakage.
- [ ] Encode categorical features.
- [ ] Train LightGBM p50.
- [ ] Validate on last 30 days.
- [ ] Calculate WAPE and bias.
- [ ] Calculate residual bands by SKU category + daypart.
- [ ] Calculate global residual fallback.
- [ ] Calculate p10-p90 coverage.
- [ ] Calculate estimated business impact.
- [ ] Save model artifact.
- [ ] Save residual bands.
- [ ] Save feature schema.
- [ ] Save metrics.
- [ ] Insert model_runs row.

### Forecast Generation To-Dos

- [ ] Build tomorrow feature rows.
- [ ] Load latest active model.
- [ ] Predict p50.
- [ ] Apply residual bands.
- [ ] Enforce p10 ≤ p50 ≤ p90.
- [ ] Save forecast_run.
- [ ] Save forecast_lines.
- [ ] Expose latest forecast API.
- [ ] Add manual regenerate endpoint.

### Optimizer To-Dos

- [ ] Implement cost model.
- [ ] Implement critical ratio calculation.
- [ ] Implement p10/p50/p90 interpolation.
- [ ] Implement opening stock subtraction.
- [ ] Implement batch rounding.
- [ ] Implement capacity cap.
- [ ] Implement freshness/carryover behavior.
- [ ] Generate rationale JSON.
- [ ] Save prep recommendations.

### Replenishment To-Dos

- [ ] Implement BOM expansion.
- [ ] Aggregate ingredient needs.
- [ ] Compare with ingredient stock.
- [ ] Generate reorder suggestions.
- [ ] Show driving SKUs.
- [ ] Save replenishment recommendations.

### Gemini To-Dos

- [ ] Write explanation prompt.
- [ ] Write manager-note parser prompt.
- [ ] Add strict “do not invent numbers” guardrails.
- [ ] Save explanation output.
- [ ] Add apply/edit/ignore flow for parsed notes.
- [ ] Recompute affected recommendations after confirmed note.

### API To-Dos

- [ ] `POST /admin/models/train`
- [ ] `GET /admin/models/latest`
- [ ] `POST /forecast-runs/generate`
- [ ] `GET /forecast-runs/latest`
- [ ] `GET /forecast-runs/{id}/lines`
- [ ] `GET /prep-plans/latest`
- [ ] `POST /prep-plans/{id}/approve`
- [ ] `POST /prep-plans/{id}/edit`
- [ ] `POST /prep-plans/{id}/reject`
- [ ] `GET /replenishment/latest`
- [ ] `POST /copilot/explain-recommendation`
- [ ] `POST /copilot/parse-manager-note`

### UI To-Dos for ML Evidence

- [ ] Model status badge.
- [ ] p10/p50/p90 display.
- [ ] Recommended prep card.
- [ ] Why this prep explanation.
- [ ] Compact model health block.
- [ ] Business impact block.
- [ ] Ingredient reorder card.
- [ ] Manager note input.
- [ ] Apply/edit/ignore parsed note.
- [ ] Approve/edit/reject final plan.

---

## 26. Risks and Mitigations

### Risk 1 — Simulated Data Looks Fake

Mitigation:

- Use real French Bakery base demand.
- Use deterministic business equations.
- Avoid overclaiming accuracy.
- Use phrase: POS-style demo validation.

### Risk 2 — LightGBM Underperforms or Overfits

Mitigation:

- Keep current heuristic as fallback.
- Show MLOps prototype status, not production status.
- Prioritize optimizer and workflow.

### Risk 3 — p10/p90 Bands Look Arbitrary

Mitigation:

- Derive bands from validation residuals.
- Show p10-p90 coverage.
- Use category + daypart residuals.

### Risk 4 — Gemini Hallucinates Numbers

Mitigation:

- Pass structured JSON only.
- Prompt: do not invent numbers.
- Save rationale JSON separately.
- Gemini explains, optimizer calculates.

### Risk 5 — Demo Becomes Too Technical

Mitigation:

- Main UI shows action: prep/order/approve.
- Model metrics stay compact.
- Technical details in drawer/appendix.

### Risk 6 — Dataset Disclosure Challenge

Locked choice:

```text
Do not overexplain simulation in main pitch;
disclose clearly if asked.
```

Safe Q&A wording:

> For the prototype, we use real public bakery transaction data as the demand foundation and generate POS-style operational fields such as stockout, prep, waste, and BOM using deterministic equations. We do not claim this is production validation. In production, these fields are replaced by real POS/ERP data and the same pipeline retrains and backtests automatically.

---

## 27. Final ML Workflow Summary

The final ML workflow is:

```text
1. Start from French Bakery transaction data.
2. Normalize SKUs and aggregate into date × SKU × daypart.
3. Expand into 5 Malaysian outlet archetypes.
4. Add holiday/weather/promo/context features.
5. Generate estimated true demand through controlled simulation.
6. Simulate naive human prep, stockout, waste, and carryover.
7. Generate ingredient stock and BOM data.
8. Build feature table at date × outlet × SKU × daypart grain.
9. Train LightGBM p50 model.
10. Use validation residuals to create p10/p90 by SKU category + daypart.
11. Generate tomorrow forecast run with p10/p50/p90.
12. Convert forecast uncertainty into prep using financial mismatch optimizer.
13. Apply batch size, capacity, and freshness constraints.
14. Expand prep into ingredient requirements using BOM.
15. Generate replenishment recommendations.
16. Gemini explains structured evidence and parses manager notes with confirmation.
17. Operator approves, edits, or rejects with reason.
18. Store audit trail and model/run metadata.
```

This supports the final product promise:

```text
Predictory does not just forecast demand.
Predictory recommends the economically rational prep and replenishment decision under uncertainty.
```

---

## 28. What We Will Discuss Next

Now that the ML workflow is frozen into implementation form, the next topics should proceed as originally planned:

```text
A. Repo cleanup / technical debt
B. UI/UX final demo flow
C. Pitch and judging defense
D. Final execution plan
```

Next discussion should start with:

```text
A. Repo cleanup / technical debt
```

Key areas:

- Seed bugs.
- Fake charts.
- Hardcoded confidence.
- Stale stock.
- Alembic/create_all conflict.
- Dashboard performance.
- Pages to hide.
- Backend consistency.

