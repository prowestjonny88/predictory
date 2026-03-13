# Predictory — 2-Day Hackathon Team Plan

## Team of 5 · 2 Days · 30 Tasks · Demo MVP

> **Architecture:** No Docker. Use managed cloud services (Neon/Supabase for Postgres, Upstash for Redis, Vercel for frontend, Railway for backend). Run locally with `uvicorn` and `pnpm dev`.

---

## Team Roles & File Ownership (Merge-Conflict Prevention)

Each person owns **exclusive directories**. No two people edit the same files.

| Role | Code | Owns These Directories | Does NOT Touch |
|---|---|---|---|
| **P1 — Infra Lead** | `P1-INFRA` | `/apps/api/auth/`, `/apps/api/audit/`, `/apps/api/db/`, root configs, managed service setup, migrations, seed scripts | Any module code, frontend, copilot |
| **P2 — Data Engineer** | `P2-DATA` | `/apps/api/ingestion/`, `/apps/api/catalog/`, `/apps/api/ops_data/` | Forecasting, planning, copilot, frontend |
| **P3 — Planning Engine** | `P3-ENGINE` | `/apps/api/forecasting/`, `/apps/api/planning/`, `/apps/api/alerts/` | Ingestion, catalog, copilot, frontend |
| **P4 — Frontend Engineer** | `P4-FRONTEND` | `/apps/web/` (entire frontend) | Any backend Python code |
| **P5 — AI/LLM Engineer** | `P5-AI` | `/apps/api/copilot/`, `/apps/worker/` | Forecasting, planning, ingestion, frontend |

### Shared contract files (coordinate before editing)
- `/packages/types/` — API request/response schemas (P2 defines, P4 consumes, all review)
- `/apps/api/main.py` — FastAPI router registration (P1 sets up, others add their routers via import only)

---

## Timeline Overview

### Day 1: Build Core
| Block | Hours | P1-INFRA | P2-DATA | P3-ENGINE | P4-FRONTEND | P5-AI |
|---|---|---|---|---|---|---|
| Morning | 0–4h | Monorepo scaffold, Neon DB + Upstash Redis setup, DB schema + migrations | (blocked until schema) Start CSV parser logic | Forecast logic (can use mock data) | App shell, layout, sidebar, navigation | LiteLLM setup, prompt templates |
| Afternoon | 4–8h | Demo data seed script, run seeds | Ingestion API + CRUD endpoints | Prep, replenishment, waste, stockout logic | Executive overview + forecast screen | Explanation endpoints, daily brief |
| Evening | 8–12h | Vercel + Railway deploy, env vars | Acknowledgement API, test with mock data | Daily plan orchestration API (`/api/daily-plan/{date}`) | Prep plan + replenishment screens | What-if scenario agent |

### Day 2: Integrate & Polish
| Block | Hours | P1-INFRA | P2-DATA | P3-ENGINE | P4-FRONTEND | P5-AI |
|---|---|---|---|---|---|---|
| Morning | 12–16h | Deploy pipeline, final seed data on prod DB | Manual adjustment API, data validation fixes | Edge cases, tuning, tests | Risk center, explanation display, what-if screen | Daily planning agent, integration test |
| Afternoon | 16–18h | Demo walkthrough prep | Bug fixes | Bug fixes, recommendation tuning | UI polish, responsiveness | Agent testing, final integration |
| Final | 18–20h | Demo rehearsal | Demo rehearsal | Demo rehearsal | Final visual polish | Demo rehearsal |

---

## P1 — INFRA LEAD

### Task 1: Project Setup and Environment Configuration
**Priority:** HIGH · **Dependencies:** None · **Day 1 Morning**

**Measurable deliverables:**
- [ ] Monorepo initialized with `pnpm-workspace.yaml` listing `/apps/web`, `/apps/api`, `/apps/worker`
- [ ] `/apps/api` running FastAPI with `GET /health` returning `200 OK`
- [ ] `/apps/web` running Next.js dev server at `localhost:3000`
- [ ] Neon Postgres provisioned — connection string in `.env`, `SELECT 1` succeeds from FastAPI
- [ ] Upstash Redis provisioned — connection string in `.env`, ping succeeds
- [ ] `.env.example` committed with all required variable names (no secrets)
- [ ] FastAPI `/health` endpoint confirms DB + Redis connectivity

**Subtasks:**
1. Initialize monorepo structure (pnpm workspace + Git)
2. Set up FastAPI backend service (`/apps/api`)
3. Set up Next.js frontend service (`/apps/web`)
4. Provision Neon Postgres + Upstash Redis (free tiers), save connection strings
5. Health check endpoint confirming all services connected

---

### Task 2: Define Database Schema for Core Entities
**Priority:** HIGH · **Dependencies:** Task 1 · **Day 1 Morning**

**Measurable deliverables:**
- [ ] SQLAlchemy 2.x models for MVP entities: Outlet, SKU, Ingredient, RecipeBOM, SalesFact, InventorySnapshot, WasteLog, ForecastRun, ForecastLine, PrepPlan, PrepPlanLine, ReplenishmentPlan, ReplenishmentPlanLine
- [ ] Alembic initial migration runs cleanly against Neon: `alembic upgrade head` succeeds
- [ ] All foreign key relationships verified with sample INSERT statements
- [ ] Single `public` schema (skip multi-schema for MVP — adds complexity with no demo value)

**Subtasks:**
1. Configure SQLAlchemy + Alembic + Neon Postgres connection
2. Core master data models (Outlet, SKU, Ingredient)
3. Operational data models (SalesFact, InventorySnapshot, WasteLog)
4. Recipe/BOM + planning models (ForecastRun/Line, PrepPlan/Line, ReplenishmentPlan/Line)
5. Generate and apply Alembic migration

---

### Task 25: Develop Demo Data Generation Script
**Priority:** HIGH · **Dependencies:** Task 2 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] Script generates data for "Roti Lane Bakery" with exactly 5 outlets: KLCC, Bangsar, Mid Valley, Bukit Bintang, Damansara
- [ ] 8+ SKUs seeded including hero SKU "Butter Croissant"
- [ ] 30 days of historical sales data (~4,500+ SalesFact rows across 5 outlets × 8 SKUs × 3 dayparts × 30 days)
- [ ] Waste logs show clear overproduction pattern: Bangsar outlet has 15%+ waste rate on croissants
- [ ] Stockout pattern visible: Mid Valley has morning stockout 3+ days/week
- [ ] BOM data for all SKUs with 5+ ingredient types (butter, flour, eggs, milk, chocolate, etc.)
- [ ] Running seed script is idempotent (can be re-run safely)

**Subtasks:**
1. Define master data (outlets, SKUs, recipes/BOM)
2. Generate 30 days historical sales with realistic daypart patterns
3. Generate waste logs showing overproduction problems
4. Generate inventory snapshots and purchase records
5. Consolidate into executable seed script

---

### Task 30: Prepare Demo Script and Walkthrough
**Priority:** HIGH · **Dependencies:** Tasks 25, 26 · **Day 2 Final**

**Measurable deliverables:**
- [ ] Written demo script covering: executive overview → forecast → prep plan (with edit) → replenishment → risk alerts
- [ ] Demo flows end-to-end on **deployed URL** in under 5 minutes without errors
- [ ] Backup demo video recorded
- [ ] Pitch framing includes: "10–20% lower waste, 8–15% fewer stockouts, 50% less planning time"

---

## P2 — DATA ENGINEER

### Task 3: Develop Data Ingestion API for CSV Uploads
**Priority:** HIGH · **Dependencies:** Task 2 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `POST /imports/upload` accepts CSV file, parses it in-memory, returns parsed row count
- [ ] Column mapping logic correctly maps ≥3 CSV formats (sales, inventory, products)
- [ ] Validation catches: missing required fields, wrong data types
- [ ] Validated data committed directly to Postgres tables
- [ ] Upload of 1,000-row CSV completes in <5 seconds

> **MVP simplification:** Skip S3 storage and import job tracking. Parse CSV in-memory and insert directly. Good enough for demo.

**Subtasks:**
1. Create FastAPI upload endpoint with in-memory CSV parsing
2. Column mapping logic per data type (sales, inventory, products)
3. Data validation and direct commit to Postgres tables

---

### Task 4: Implement Core Data Retrieval APIs
**Priority:** HIGH · **Dependencies:** Task 3 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `GET /outlets` returns all outlets (verified with 5 Roti Lane outlets)
- [ ] `GET /skus` returns all SKUs with category and freshness info
- [ ] `GET /ingredients` returns all ingredients with stock levels
- [ ] `GET /recipes` returns BOM data joining SKUs to ingredients
- [ ] `GET /sales?outlet_id=X&sku_id=Y&start_date=Z&end_date=W` returns filtered sales with pagination
- [ ] `GET /inventory?outlet_id=X` returns current stock by SKU
- [ ] `GET /wastelogs?outlet_id=X&start_date=Z` returns filtered waste records
- [ ] All endpoints return valid JSON, correct HTTP status codes, and handle empty results gracefully

---

### Task 11: Implement Recommendation Acknowledgement API (FR8)
**Priority:** MEDIUM · **Dependencies:** Task 10 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `PATCH /plans/prep/{id}/lines/{line_id}` updates edited_units field — verified with PUT and re-GET
- [ ] `POST /plans/prep/{id}/approve` sets plan status to `approved` and records `approved_by` user
- [ ] Approved plan cannot be re-approved (returns 409 Conflict)
- [ ] Edit history stored: before_value and after_value in AuditEvent table

---

### Task 27: Refine Forecasting with Manual Adjustments
**Priority:** MEDIUM · **Dependencies:** Task 5 · **Day 2 Morning**

**Measurable deliverables:**
- [ ] `PATCH /forecasts/{run_id}/lines/{line_id}` accepts manual_adjustment_pct parameter
- [ ] Adjusted forecast = base forecast × (1 + manual_adjustment_pct/100)
- [ ] Event override API: `POST /forecasts/{run_id}/event-override` with type (holiday, promo, etc.)
- [ ] Adjustments logged in AuditEvent table

---

### Task 28 + 29: Data Onboarding Agent (Backend + Frontend)
**Priority:** LOW (STRETCH) · **Dependencies:** Tasks 3, 18 · **Day 2 Afternoon**

> **Stretch goal.** Demo uses seed data — only build this if all HIGH tasks are done by Day 2 morning.

**Measurable deliverables:**
- [ ] `POST /copilot/map-upload` suggests column mappings for uploaded CSV
- [ ] Simple upload modal shows preview + suggested mappings

---

## P3 — FORECAST & PLANNING ENGINE

### Task 5: Implement Baseline Demand Forecasting Logic (FR1)
**Priority:** HIGH · **Dependencies:** Task 4 · **Day 1 Morning–Afternoon**

**Measurable deliverables:**
- [ ] `forecast_demand(outlet_id, sku_id, date)` returns dict with keys: `morning`, `midday`, `evening`, `total`
- [ ] Weighted recent sales: last 7 days, weights [0.05, 0.05, 0.10, 0.10, 0.15, 0.20, 0.35]
- [ ] Same-weekday pattern: average of last 4 same-weekday sales
- [ ] Combined forecast = 0.4 × weighted_recent + 0.4 × weekday_pattern + 0.2 × 14-day moving average
- [ ] Daypart split based on historical daypart ratios for that SKU/outlet
- [ ] ForecastRun + ForecastLine records persisted in `planning` schema
- [ ] Forecast for croissants at KLCC outlet ± 10% of reasonable range given seed data
- [ ] Unit tests pass for all 3 forecast components + combined logic

**Subtasks:**
1. Historical sales data retrieval + preprocessing into Pandas DataFrame
2. Weighted recent sales trend + moving average components
3. Same-weekday pattern logic
4. Core `forecast_demand()` combining all components
5. Daypart breakdown + persistence (ForecastRun/ForecastLine)

---

### Task 6: Implement Prep Recommendation Engine Logic (FR2)
**Priority:** HIGH · **Dependencies:** Task 5 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `recommend_prep(outlet_id, sku_id, date)` returns per-daypart recommended units
- [ ] Core formula verified: `prep_qty = forecast_demand + (forecast_demand × safety_buffer_pct) - ready_stock`
- [ ] Safety buffer default = 10%, configurable per SKU
- [ ] Freshness window respected: items with <8h shelf life not prepped for evening if prepped morning
- [ ] Historical waste adjustment: if last 7-day waste rate >15%, reduce prep by 5%
- [ ] PrepPlan + PrepPlanLine records created in DB with `rationale_json` field populated
- [ ] Unit tests for: zero stock, full stock, short freshness, high waste history

**Subtasks:**
1. Core prep quantity calculation (forecast + buffer - stock)
2. Freshness window + prep lead time constraints
3. Historical waste rate adjustments
4. `recommend_prep_plan()` wrapper + DB persistence

---

### Task 7: Implement Ingredient Replenishment Logic (FR4)
**Priority:** HIGH · **Dependencies:** Task 6 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `recommend_replenishment(date)` returns list of ingredient reorder recommendations
- [ ] Formula verified: `ingredient_need = Σ(prep_qty × recipe_qty_per_unit) - ingredient_stock_on_hand`
- [ ] Urgency levels: `critical` (stock <50% of need), `high` (stock <80%), `medium` (stock <100%), `low` (stock sufficient)
- [ ] Supplier lead time factored: if lead time >24h and stock insufficient, urgency bumped up
- [ ] ReplenishmentPlan + ReplenishmentPlanLine records persisted with `rationale_json`
- [ ] Butter reorder correctly triggered when croissant prep plan requires >available stock

---

### Task 8: Implement Waste Risk Alert Logic (FR5)
**Priority:** HIGH · **Dependencies:** Task 6 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `detect_waste_risk(date)` returns list of waste risk alerts
- [ ] Alert triggered when: prep exceeds forecast by >15%
- [ ] Alert triggered when: last 3-day waste rate on SKU >10%
- [ ] Alert triggered when: evening daypart demand declined for ≥3 consecutive days
- [ ] Risk levels: `high` (≥2 triggers), `medium` (1 trigger), `low` (none)
- [ ] Bangsar croissant evening waste correctly flagged as HIGH risk given seed data
- [ ] Each alert includes structured `reason` field

---

### Task 9: Implement Stockout Risk Alert Logic (FR6)
**Priority:** HIGH · **Dependencies:** Tasks 6, 7 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `detect_stockout_risk(date)` returns list of stockout risk alerts
- [ ] Alert triggered when: morning forecast > (current stock + planned prep arriving before 7am)
- [ ] Alert triggered when: ingredient stock covers <80% of planned production
- [ ] Bestseller SKUs get priority flagging (lower threshold: 90% coverage = alert)
- [ ] Mid Valley morning croissant stockout correctly flagged given seed data
- [ ] Each alert includes `affected_daypart`, `shortage_qty`, `reason`

---

### Task 10: Develop Backend API for Daily Planning Data
**Priority:** HIGH · **Dependencies:** Tasks 5–9 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `GET /api/daily-plan/{date}` returns complete JSON response in <3 seconds
- [ ] Response contains exactly these sections: `forecasts`, `prep_plan`, `replenishment_plan`, `waste_alerts`, `stockout_alerts`, `summary`
- [ ] `summary` includes: `total_predicted_sales`, `waste_risk_score` (0-100), `stockout_risk_score` (0-100), `top_actions` (list of 5), `at_risk_outlets` (list)
- [ ] `POST /plans/prep/run` triggers prep plan generation and returns plan ID
- [ ] `POST /plans/replenishment/run` triggers replenishment plan and returns plan ID
- [ ] All responses use Pydantic v2 models for type safety

**Subtasks:**
1. Define FastAPI endpoint + Pydantic request/response models
2. Integrate forecast + prep recommendation calls
3. Integrate replenishment + risk alert calls
4. Consolidate structured JSON response with summary
5. POST endpoints for plan execution triggers

---

## P4 — FRONTEND ENGINEER

### Task 20: Basic Navigation and Layout (BUILD FIRST)
**Priority:** HIGH · **Dependencies:** None (ui-only) · **Day 1 Morning**

**Measurable deliverables:**
- [ ] Root `layout.tsx` with sidebar + header + main content area
- [ ] Sidebar navigation with 8 routes: `/dashboard`, `/forecast`, `/prep-plan`, `/replenishment`, `/risk-center`, `/scenario-planner`, `/imports`, `/settings`
- [ ] Active route highlighted in sidebar
- [ ] Header contains: outlet selector dropdown, date picker, Predictory logo
- [ ] All 8 routes render placeholder pages (no 404s)
- [ ] Layout responsive: sidebar collapses on mobile (<768px)

**Subtasks:**
1. Next.js App Router root layout
2. Sidebar component with shadcn/ui
3. Header with outlet/date selectors
4. Route placeholder pages

---

### Task 12: Executive Overview Screen (Screen 1)
**Priority:** HIGH · **Dependencies:** Task 10, 20 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `/dashboard` fetches from `GET /api/daily-plan/{date}` via TanStack Query
- [ ] 3 KPI cards displayed: Total Predicted Sales, Waste Risk Score, Stockout Risk Score
- [ ] KPI cards color-coded: green (<30), yellow (30-60), red (>60) for risk scores
- [ ] Top 5 Actions list with action text and target outlet
- [ ] Most At-Risk Outlets list showing outlet name + primary risk type
- [ ] Loading skeleton shown while data fetches
- [ ] Error state shown if API fails

**Subtasks:**
1. Page route + TanStack Query data fetching
2. KPI card components with color coding
3. Top actions + at-risk outlets lists
4. Loading/error states
5. Final layout assembly

---

### Task 13: Outlet/Daypart Forecast Screen (Screen 2)
**Priority:** HIGH · **Dependencies:** Task 10 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] `/forecast` shows outlet selector (dropdown with 5 Roti Lane outlets)
- [ ] Forecast table: rows = SKUs, columns = Morning / Midday / Evening / Total
- [ ] Daypart cards showing demand with trend arrows (↑↓→)
- [ ] Recharts sparkline or bar chart per SKU showing 7-day trend
- [ ] Selecting different outlet updates table data
- [ ] "Reason" tags shown per row (e.g., "Weekend boost", "Declining trend")

---

### Task 14: Prep Plan Screen (Screen 3)
**Priority:** HIGH · **Dependencies:** Tasks 11, 13 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `/prep-plan` shows table: SKU, Outlet, Morning/Midday/Evening prep qty, Current Stock, Delta vs Usual
- [ ] Each row has Accept (✓) and Edit (✏️) buttons
- [ ] Edit mode: inline number input, Save/Cancel buttons
- [ ] "Approve All" button sends `POST /plans/prep/{id}/approve`
- [ ] Approved items show green checkmark, edited items show orange indicator
- [ ] Delta column shows +/- vs 7-day average prep, color-coded

---

### Task 15: Central Kitchen Allocation View (FR3)
**Priority:** MEDIUM (STRETCH) · **Dependencies:** Task 14 · **Day 2 Morning**

> **Stretch goal.** If behind, skip and show allocation data as a summary row in the Prep Plan screen instead.

**Measurable deliverables:**
- [ ] View shows total production needed per SKU (sum across outlets)
- [ ] Breakdown table: SKU × Outlet allocation matrix
- [ ] Outlet-level imbalance flagged visually

---

### Task 16: Replenishment Plan Screen (Screen 4)
**Priority:** HIGH · **Dependencies:** Task 10 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `/replenishment` shows table: Ingredient, Need Qty, Stock On Hand, Reorder Qty, Urgency, Driving SKUs
- [ ] Urgency column color-coded: Critical=red, High=orange, Medium=yellow, Low=green
- [ ] "Driving SKUs" column shows which products require this ingredient
- [ ] "Mark as Ordered" button per row (local state toggle)
- [ ] Summary card at top: "X ingredients need reordering, Y are critical"

---

### Task 17: Risk and Waste Center Screen (Screen 5)
**Priority:** HIGH · **Dependencies:** Task 10 · **Day 2 Morning**

**Measurable deliverables:**
- [ ] `/risk-center` shows two sections: Waste Hotspots + Stockout Alerts
- [ ] Each alert card shows: SKU, Outlet, Daypart, Risk Level badge, Reason text
- [ ] Alerts sortable by risk level (High → Low)
- [ ] Outlet imbalance section with visual comparison
- [ ] Suggested actions section: "Reduce croissant prep at Bangsar by 14%"
- [ ] Total items displayed matches backend alert count

---

### Task 19: Integrate LLM Explanations into Frontend
**Priority:** HIGH · **Dependencies:** Tasks 18, 13, 14, 16, 17 · **Day 2 Morning**

**Measurable deliverables:**
- [ ] Each forecast row has expandable "Why?" drawer showing LLM explanation
- [ ] Each prep recommendation has tooltip with rationale
- [ ] Each risk alert card shows explanation paragraph
- [ ] Replenishment items show reason text
- [ ] Explanations load async (don't block main data)
- [ ] Graceful fallback if explanation API fails (show "Explanation unavailable")

---

### Task 22: What-if Planner Screen (Screen 6)
**Priority:** LOW (STRETCH) · **Dependencies:** Tasks 21, 20 · **Day 2 Afternoon**

> **Stretch goal.** First to cut if behind. Mention in pitch as "coming soon" feature.

**Measurable deliverables:**
- [ ] `/scenario-planner` has text input for scenario description
- [ ] 2–3 predefined quick scenarios as buttons
- [ ] Response panel shows baseline vs modified comparison

---

### Task 26: UI Polish and Demo-Ready Styling
**Priority:** HIGH · **Dependencies:** All frontend tasks · **Day 2 Afternoon**

**Measurable deliverables:**
- [ ] Consistent color palette across all screens (brand colors defined in Tailwind config)
- [ ] All tables have consistent column widths, hover states, alternating row colors
- [ ] All cards have consistent border radius, shadow, padding
- [ ] Typography hierarchy: H1=page title, H2=section title, H3=card title, body=data
- [ ] Responsive: all screens usable at 1024px and 1440px widths
- [ ] No UI console errors or warnings
- [ ] Screenshots of all 6+ screens captured for pitch deck

---

## P5 — AI/LLM ENGINEER

### Task 18: Implement Explainability Layer (FR7) - Backend
**Priority:** HIGH · **Dependencies:** Task 10 · **Day 1 Afternoon**

**Measurable deliverables:**
- [ ] LiteLLM configured with ≥1 provider (OpenAI or Anthropic) — test call succeeds
- [ ] `POST /copilot/explain-plan` accepts plan data, returns plain-language explanation
- [ ] `POST /copilot/daily-brief` accepts date, returns 3-paragraph summary of tomorrow's plan
- [ ] Prompt templates for: forecast explanation, prep rationale, waste alert reason, stockout alert reason, replenishment rationale (5 templates total)
- [ ] LLM never invents numbers — all data comes from deterministic inputs (verified by review)
- [ ] Explanation generation completes in <8 seconds per request

> **MVP simplification:** Skip Redis caching. Acceptable latency for demo. Add caching post-hackathon.

**Subtasks:**
1. Configure LiteLLM gateway + test connection
2. Develop 5 prompt templates
3. Core `generate_explanation()` function
4. FastAPI endpoints: explain-plan and daily-brief

---

### Task 21: What-if Scenario Agent (AI Layer 3) - Backend
**Priority:** MEDIUM · **Dependencies:** Task 18 · **Day 1 Evening**

**Measurable deliverables:**
- [ ] `POST /copilot/run-scenario` accepts scenario text, returns structured comparison
- [ ] LangGraph agent with 3 tool definitions: `run_scenario_simulation()`, `get_forecast()`, `get_prep_plan()`
- [ ] Agent correctly interprets: "cut croissant prep by 15% at KLCC" → modifies prep by -15% for that outlet/SKU
- [ ] Response includes: `baseline_waste`, `modified_waste`, `baseline_stockouts`, `modified_stockouts`, `recommendation`
- [ ] Agent completes within 15 seconds per scenario
- [ ] Human-in-the-loop: response is advisory only, does not modify actual plans

**Subtasks:**
1. Create `/copilot/run-scenario` endpoint
2. LangGraph agent core + tool definitions
3. Scenario interpretation + simulation execution
4. Impact analysis + response generation

---

### Task 23: Daily Planning Agent (AI Layer 4) - Backend
**Priority:** MEDIUM · **Dependencies:** Task 18 · **Day 2 Morning**

**Measurable deliverables:**
- [ ] `POST /copilot/daily-brief` generates structured action plan with sections: `prep_actions`, `reorder_actions`, `risk_warnings`, `rebalance_suggestions`
- [ ] Agent reads: latest forecast + stock + BOM + waste trends
- [ ] Top 5 actions prioritized by business impact
- [ ] Each action includes: action text, target outlet/SKU, estimated impact, urgency
- [ ] Agent output validated: all referenced outlets and SKUs exist in database
- [ ] Response time <10 seconds

---

### Task 24: Integrate Daily Planning Agent into Executive Overview
**Priority:** MEDIUM · **Dependencies:** Tasks 23, 12 · **Day 2 Morning**

**Measurable deliverables:**
- [ ] Executive overview "Top 5 Actions" section populated by Daily Planning Agent output
- [ ] Actions displayed with outlet name, action type icon, and urgency badge
- [ ] API contract documented: `GET /api/daily-plan/{date}` response includes `agent_actions` field
- [ ] Fallback: if agent fails, show deterministic top actions instead

---

## Cross-Team Integration Checkpoints

| When | What | Who Syncs |
|---|---|---|
| Day 1, Hour 2 | P1 shares Neon + Upstash connection strings in `.env` | P1 → All |
| Day 1, Hour 4 | P1 confirms DB schema migrated, seed data loaded | P1 → All |
| Day 1, Hour 6 | P3 shares forecast API contract (request/response JSON shapes) | P3 → P4 |
| Day 1, Hour 8 | P3 deploys `/api/daily-plan/{date}` — P4 can start consuming | P3 → P4 |
| Day 1, Hour 10 | P5 deploys `/copilot/explain-plan` — P4 can integrate explanations | P5 → P4 |
| Day 2, Hour 14 | Full integration test: all screens consuming real APIs | All |
| Day 2, Hour 16 | Deploy to Vercel (frontend) + Railway (backend) | P1 + P4 |
| Day 2, Hour 18 | Feature freeze — only bug fixes and visual polish | All |
| Day 2, Hour 19 | Demo dry run on deployed URL | All |

---

## Deployment Plan

| Service | Platform | Free Tier | Setup Time |
|---|---|---|---|
| **PostgreSQL** | Neon | 0.5 GB storage, branching | 2 min |
| **Redis** | Upstash | 10K commands/day | 2 min |
| **Frontend** | Vercel | Unlimited deploys | 5 min |
| **Backend API** | Railway | $5 credit/month | 10 min |
| **File uploads** | Local filesystem / Vercel Blob | MVP only | 0 min |

> No Docker needed. Each dev runs `uvicorn` (backend) and `pnpm dev` (frontend) locally.

---

## Summary: Task Assignment Matrix

| Task ID | Title | Assignee | Priority | Day |
|---|---|---|---|---|
| 1 | Project Setup & Environment | P1-INFRA | HIGH | D1 Morning |
| 2 | Database Schema | P1-INFRA | HIGH | D1 Morning |
| 25 | Demo Data Generation | P1-INFRA | HIGH | D1 Afternoon |
| 30 | Demo Script & Walkthrough | P1-INFRA | HIGH | D2 Final |
| 3 | CSV Ingestion API | P2-DATA | HIGH | D1 Afternoon |
| 4 | Data Retrieval APIs | P2-DATA | HIGH | D1 Afternoon |
| 11 | Recommendation Acknowledgement | P2-DATA | MEDIUM | D1 Evening |
| 27 | Manual Adjustment API | P2-DATA | MEDIUM | D2 Morning |
| 28 | Data Onboarding Agent (BE) | P2-DATA | LOW | D2 Afternoon (stretch) |
| 29 | Data Onboarding Agent (FE) | P2-DATA | LOW | D2 Afternoon (stretch) |
| 5 | Demand Forecasting Logic | P3-ENGINE | HIGH | D1 Morning |
| 6 | Prep Recommendation Engine | P3-ENGINE | HIGH | D1 Afternoon |
| 7 | Ingredient Replenishment Logic | P3-ENGINE | HIGH | D1 Afternoon |
| 8 | Waste Risk Alert Logic | P3-ENGINE | HIGH | D1 Evening |
| 9 | Stockout Risk Alert Logic | P3-ENGINE | HIGH | D1 Evening |
| 10 | Daily Planning Orchestration API | P3-ENGINE | HIGH | D1 Evening |
| 12 | Executive Overview Screen | P4-FRONTEND | HIGH | D1 Afternoon |
| 13 | Forecast Screen | P4-FRONTEND | HIGH | D1 Afternoon |
| 14 | Prep Plan Screen | P4-FRONTEND | HIGH | D1 Evening |
| 15 | Central Kitchen View | P4-FRONTEND | MEDIUM | D2 Morning (stretch) |
| 16 | Replenishment Screen | P4-FRONTEND | HIGH | D1 Evening |
| 17 | Risk & Waste Center | P4-FRONTEND | HIGH | D2 Morning |
| 19 | LLM Explanation Integration | P4-FRONTEND | HIGH | D2 Morning |
| 20 | Navigation & Layout | P4-FRONTEND | HIGH | D1 Morning |
| 22 | What-if Planner Screen | P4-FRONTEND | LOW | D2 Afternoon (stretch) |
| 26 | UI Polish & Demo Styling | P4-FRONTEND | HIGH | D2 Afternoon |
| 18 | Explainability Layer (BE) | P5-AI | HIGH | D1 Afternoon |
| 21 | What-if Scenario Agent | P5-AI | MEDIUM | D1 Evening |
| 23 | Daily Planning Agent | P5-AI | MEDIUM | D2 Morning |
| 24 | Agent → Executive Overview | P5-AI | MEDIUM | D2 Morning |

---

## What to Cut if Running Behind

If Day 1 evening ends and you're behind, drop these in order:
1. **Task 22** — What-if planner screen (skip entirely, demo without it)
2. **Task 15** — Central kitchen view (merge into prep plan as a summary row)
3. **Tasks 28, 29** — Data onboarding agent (use seed data only for demo)
4. **Task 27** — Manual adjustments (demo with fixed forecasts)
5. **Task 21** — What-if scenario agent (explain the concept in pitch, don't build)

The **minimum viable demo** needs only: Tasks 1, 2, 25, 5, 6, 7, 8, 9, 10, 12, 13, 14, 16, 17, 18, 20, 26, 30

---

## Git Branch Strategy (Merge-Conflict Prevention)

```
main
 ├── feat/p1-infra-setup        (P1 only)
 ├── feat/p1-schema-seeds       (P1 only)
 ├── feat/p2-ingestion-apis     (P2 only)
 ├── feat/p3-forecast-engine    (P3 only)
 ├── feat/p3-planning-engine    (P3 only)
 ├── feat/p4-layout-nav         (P4 only)
 ├── feat/p4-screens            (P4 only)
 ├── feat/p5-copilot-agents     (P5 only)
 └── feat/p5-langgraph-agents   (P5 only)
```

**Rules:**
1. Never edit files outside your owned directories
2. P1 merges first (infrastructure), then P2+P3+P5 (backend), then P4 (frontend)
3. Only `main.py` router registration is shared — P1 creates the structure, others add `include_router()` lines in their own merge
4. Integration branch `develop` used for Day 2 integration testing before final merge to `main`
