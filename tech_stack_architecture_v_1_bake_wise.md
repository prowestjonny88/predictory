# Tech Stack & Architecture v1 — BakeWise

## Document status
Recommended baseline architecture and stack for the BakeWise MVP and near-term production path.

## Goal
Choose a stack that is:
- fast enough for a 2-day prototype
- strong enough for pilot customers
- modular enough to evolve without a rewrite
- practical for AI + forecasting + analytics workloads
- low-risk and maintainable by a small team

---

# 1. Executive recommendation

## Architecture pattern
**Modular monolith + background workers + managed data services**

This is the right choice because:
- a full microservices setup is too heavy and fragile for a 2-day build
- a single codebase is faster to ship and easier to debug
- clear module boundaries let us split services later only if needed
- forecasting, recommendation logic, and agent workflows can run as background jobs without overcomplicating the core app

## Recommended stack summary

### Frontend
- **Next.js (App Router)**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui**
- **TanStack Query**
- **Zustand**
- **Recharts**

### Backend API
- **FastAPI (Python)**
- **Pydantic v2**
- **SQLAlchemy 2.x**
- **Alembic**

### Data + storage
- **PostgreSQL** as primary database
- **pgvector** enabled inside PostgreSQL for future semantic/RAG features
- **Redis** for cache, job queue support, and short-lived plan/session state
- **S3-compatible object storage** for CSV imports, exports, and generated assets

### Background processing
- **Celery + Redis**

### Forecasting / decision engine
- **Pandas / Polars**
- **NumPy**
- **StatsForecast or statsmodels**
- **scikit-learn**
- rule-based planning engine for prep/replenishment/waste logic

### AI / LLM layer
- **LiteLLM** as model gateway
- **OpenAI or Anthropic models** through LiteLLM
- **LangGraph** only for structured, human-in-the-loop agent workflows
- prompt + tool calling architecture, not free-form autonomous agents

### Auth / product analytics / monitoring
- **Auth.js** for authentication
- **PostHog** for product analytics
- **Sentry** for error monitoring
- **OpenTelemetry** for tracing-ready instrumentation

### DevOps / deployment
- **Docker**
- **Docker Compose** for local development
- **GitHub Actions** for CI/CD
- **Frontend deploy:** Vercel
- **Backend/workers deploy:** Railway, Render, or Fly.io initially
- **Long-term production path:** AWS ECS/Fargate + RDS + ElastiCache + S3

---

# 2. Why this is the right architecture

## 2.1 Why modular monolith, not microservices
We should not start with microservices.

### Why not microservices now
- too much deployment overhead
- harder local development
- more failure points
- slower iteration during hackathon and pilot stage
- more DevOps burden than product value

### Why modular monolith is better
We can keep a single backend codebase but structure it into domains:
- auth and RBAC
- outlet/catalog data
- ingestion
- forecasting
- planning engine
- AI copilot
- alerts and approvals
- audit logging

This gives us:
- speed now
- clean boundaries later
- minimal architecture churn

## 2.2 Why FastAPI instead of Node backend
The core product depends on:
- forecasting
- data manipulation
- planning logic
- model/LLM orchestration

Python is better for this than a Node-only backend because:
- stronger ecosystem for analytics and forecasting
- easier data science collaboration
- better library support for tabular logic
- cleaner path from prototype logic to productionized decision engine

We still use Next.js for the frontend because:
- fast UI iteration
- great developer experience
- easy deployment
- good fit for dashboard SaaS

## 2.3 Why PostgreSQL as the center of gravity
Postgres should be the source of truth because it is:
- mature
- reliable
- flexible enough for transactional and analytical workloads at our scale
- strong with JSONB when needed
- compatible with pgvector for future semantic features
- easier to maintain than splitting data stores too early

We do **not** need a separate vector DB, NoSQL DB, or data warehouse in v1.

---

# 3. System architecture overview

```text
                        +----------------------+
                        |   Web / Mobile UI    |
                        | Next.js + TypeScript |
                        +----------+-----------+
                                   |
                            HTTPS / REST
                                   |
                      +------------v-------------+
                      |       FastAPI API        |
                      |  Modular Monolith Core   |
                      +------------+-------------+
                                   |
        +--------------------------+---------------------------+
        |                          |                           |
+-------v--------+       +---------v---------+       +---------v---------+
| Forecast Engine|       | Planning Engine   |       | AI Copilot Layer  |
| demand models  |       | prep/replenishment|       | summaries/agents  |
+-------+--------+       +---------+---------+       +---------+---------+
        |                          |                           |
        +--------------------------+---------------------------+
                                   |
                        +----------v-----------+
                        |   PostgreSQL +       |
                        |   pgvector           |
                        +----------+-----------+
                                   |
                     +-------------+--------------+
                     |                            |
             +-------v--------+          +--------v--------+
             |     Redis      |          |   S3 Storage    |
             | cache / queue  |          | CSV / exports   |
             +-------+--------+          +--------+--------+
                     |                            |
                     +-------------+--------------+
                                   |
                           +-------v-------+
                           | Celery Worker |
                           | jobs / agents |
                           +---------------+
```

---

# 4. Core design principles

## 4.1 Human-in-the-loop
The system recommends and explains.
It does not autonomously place orders or execute procurement in v1.

## 4.2 Structured AI, not magic AI
LLMs should be used for:
- explanation
- summarization
- scenario comparison
- guided planning

Deterministic logic should be used for:
- forecast inputs
- prep calculations
- replenishment calculations
- risk scoring
- business-rule enforcement

## 4.3 Cloud-portable from day one
Everything should run in Docker.
That allows:
- local development via Docker Compose
- easy deployment to Railway/Render/Fly/Vercel now
- cleaner migration to AWS later

## 4.4 Avoid premature vendor lock-in
Use managed services where they speed us up, but keep the app architecture portable.
That means:
- Postgres, not provider-specific proprietary DB logic
- S3-compatible storage, not deeply custom storage patterns
- LiteLLM abstraction for model providers
- standard REST APIs, not exotic framework coupling

---

# 5. Recommended stack by layer

# 5.1 Frontend stack

## Framework
**Next.js (App Router) + React + TypeScript**

### Why
- mature ecosystem
- fast dashboard development
- excellent performance and routing
- straightforward deployment on Vercel
- good for both marketing pages and authenticated SaaS app

## UI
- **Tailwind CSS**
- **shadcn/ui**
- **Lucide icons**
- **Recharts** for charts

### Why
- fast prototyping without UI inconsistency
- clean modern SaaS look
- easy to build tables, cards, alerts, filters, and modals

## Client state and data fetching
- **TanStack Query** for server state
- **Zustand** for lightweight local UI state

### Why
- TanStack Query handles caching, invalidation, loading, and retries well
- Zustand is simple for selected outlet, date, and scenario state
- avoids overengineering with Redux

## Form handling
- **React Hook Form + Zod**

### Why
- efficient forms
- type-safe validation
- useful for upload mapping, manual overrides, approvals

---

# 5.2 Backend stack

## API framework
**FastAPI**

### Why
- very fast to develop
- strong typing with Pydantic
- excellent for data-heavy APIs
- easy OpenAPI docs
- good async support where needed

## Data models / ORM
- **SQLAlchemy 2.x**
- **Alembic** for migrations
- **Pydantic v2** for schema validation

### Why
- SQLAlchemy is stable and production-grade
- Alembic gives us controlled schema evolution
- Pydantic keeps request/response contracts explicit

## API style
**REST first**

### Why not GraphQL now
- adds complexity we do not need
- harder to keep contract discipline during fast iteration
- REST is enough for dashboards, uploads, forecasts, plans, approvals, and agent calls

---

# 5.3 Data stack

## Primary database
**PostgreSQL**

### Schema strategy
Use separate logical domains / schemas where helpful:
- `core` — outlets, users, orgs, SKUs, ingredients
- `ops` — sales, stock, waste, purchase history
- `planning` — forecasts, prep plans, replenishment plans, approvals
- `ai` — prompt logs, summaries, scenario runs, agent outputs
- `audit` — user actions, overrides, plan approvals

## Extensions
- **pgvector** for future retrieval use cases
- optional **pg_trgm** for fuzzy matching on imported SKUs and ingredients

### Why pgvector now even if not central yet
- future-proof for semantic retrieval over internal notes, mappings, and explanations
- helps if we later add document/knowledge grounding or smart matching
- low cost to enable upfront

## Cache / ephemeral state
**Redis**

Use Redis for:
- job broker
- short-lived cache of forecast computations
- rate limiting
- scenario/session state if needed

## Object storage
**S3-compatible storage**

Use for:
- CSV uploads
- cleaned import files
- exports
- generated reports or deck/demo assets if needed

---

# 5.4 Background jobs and async processing

## Worker system
**Celery + Redis**

### Why
- reliable and widely used
- fits Python stack well
- good for forecast jobs, import processing, agent workflows, and summary generation

## Job categories
- CSV ingestion and validation
- forecast recalculation
- prep/replenishment plan generation
- anomaly detection tasks
- agent summary generation
- nightly batch jobs

## Why background jobs matter
We do not want long-running forecast or agent requests blocking the main API.

---

# 5.5 Forecasting and planning stack

## Core libraries
- **Pandas** for easy tabular manipulation
- **Polars** where performance matters later
- **NumPy**
- **StatsForecast** or **statsmodels**
- **scikit-learn**

## Recommendation
Start with:
- **Pandas**
- **NumPy**
- **StatsForecast** for time-series baselines
- **scikit-learn** only where useful for feature-based models later

## Why this is robust
This gives us a progression path:
1. simple heuristic baseline
2. classical time-series models
3. richer ML features later
4. no rewrite of the surrounding planning architecture

## Planning engine
Do **not** embed prep/replenishment logic directly inside prompts.
Build a dedicated planning module with explicit functions such as:
- `forecast_demand()`
- `recommend_prep_plan()`
- `recommend_replenishment()`
- `detect_waste_risk()`
- `detect_stockout_risk()`
- `simulate_scenario()`

This becomes the stable brain of the product.

---

# 5.6 AI / LLM / agent stack

## Model gateway
**LiteLLM**

### Why
- one abstraction for multiple model providers
- easy switching between OpenAI / Anthropic / others
- protects us from provider lock-in
- cleaner logging and fallback logic

## Primary model usage
Use LLMs for:
- recommendation explanation
- daily planning summaries
- anomaly investigation narratives
- what-if scenario comparison
- CSV mapping assistance

## Agent orchestration
**LangGraph** for structured workflows only

### Why
- stateful graph execution
- good fit for human-in-the-loop planning flows
- better than free-form agent chains for repeatable ops use cases

### Important constraint
Only use agents where there is a clear workflow and toolset.
Do **not** use multi-agent systems everywhere.

## Agent/tool design
Each agent should use tools backed by deterministic services, for example:
- `get_forecast()`
- `get_prep_plan()`
- `get_replenishment_plan()`
- `get_waste_risks()`
- `run_scenario_simulation()`
- `map_csv_columns()`

The LLM should never invent planning outputs.
It should call tools and explain the result.

## Memory strategy
For v1:
- store conversation context and scenario history in Postgres
- avoid overcomplicated memory systems
- use pgvector only if we later add retrieval over playbooks, ops notes, or uploaded docs

---

# 6. Core backend modules

Design the FastAPI backend as a modular monolith with these packages:

## 6.1 `auth`
Responsibilities:
- users
- sessions
- roles
- organization membership
- permissions

## 6.2 `catalog`
Responsibilities:
- outlets
- SKUs
- ingredients
- categories
- recipe/BOM definitions

## 6.3 `ingestion`
Responsibilities:
- CSV upload intake
- schema mapping
- validation
- deduplication
- import job status

## 6.4 `ops_data`
Responsibilities:
- sales history
- inventory snapshots
- waste logs
- purchase history

## 6.5 `forecasting`
Responsibilities:
- training/inference on baseline demand models
- forecast generation by SKU/outlet/daypart
- confidence scoring
- forecast persistence

## 6.6 `planning`
Responsibilities:
- prep recommendations
- central kitchen allocation
- replenishment recommendations
- risk scoring
- scenario simulation

## 6.7 `copilot`
Responsibilities:
- explanation generation
- summary generation
- anomaly narrative generation
- what-if Q&A

## 6.8 `alerts`
Responsibilities:
- stockout alerts
- waste alerts
- exceptions
- future notification plumbing

## 6.9 `audit`
Responsibilities:
- user overrides
- approvals
- plan versioning
- traceability

This structure is stable and easy to split later if absolutely necessary.

---

# 7. Data model strategy

## 7.1 Key entities

### Organization
- id
- name
- country
- timezone
- plan tier

### User
- id
- org_id
- role
- email
- name

### Outlet
- id
- org_id
- name
- location
- opening_hours
- central_kitchen_enabled

### SKU
- id
- org_id
- name
- category
- shelf_life_hours
- prep_lead_time_minutes
- is_core_item

### Ingredient
- id
- org_id
- name
- unit
- lead_time_hours
- reorder_threshold

### RecipeBOM
- sku_id
- ingredient_id
- quantity_per_unit

### SalesFact
- id
- outlet_id
- sku_id
- sold_at
- quantity
- revenue

### InventorySnapshot
- id
- outlet_id
- sku_id
- captured_at
- quantity_on_hand

### IngredientInventorySnapshot
- id
- org_id
- ingredient_id
- captured_at
- quantity_on_hand

### WasteLog
- id
- outlet_id
- sku_id
- logged_at
- quantity_wasted
- reason

### PurchaseOrderHistory
- id
- org_id
- ingredient_id
- ordered_at
- quantity
- cost
- supplier_name

### ForecastRun
- id
- org_id
- date_for
- model_version
- status

### ForecastLine
- forecast_run_id
- outlet_id
- sku_id
- daypart
- predicted_units
- confidence_score

### PrepPlan
- id
- org_id
- date_for
- status
- created_by
- approved_by

### PrepPlanLine
- prep_plan_id
- outlet_id
- sku_id
- daypart
- recommended_units
- edited_units
- approved_units
- rationale_json

### ReplenishmentPlan
- id
- org_id
- date_for
- status

### ReplenishmentPlanLine
- replenishment_plan_id
- ingredient_id
- recommended_qty
- urgency
- rationale_json

### ScenarioRun
- id
- org_id
- name
- input_json
- output_json
- created_by

### AgentRun
- id
- org_id
- agent_type
- prompt
- tool_calls_json
- output_json
- status

### AuditEvent
- id
- org_id
- user_id
- action_type
- entity_type
- entity_id
- before_json
- after_json
- created_at

## 7.2 Why persist forecasts and plans
Do not compute everything only in-memory.
Persist forecasts, plan versions, edits, and approvals so that:
- results are reproducible
- demo flows look realistic
- overrides are auditable
- future analytics become possible

---

# 8. API design

## 8.1 Key API groups

### Auth
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

### Organization / outlets / catalog
- `GET /org`
- `GET /outlets`
- `GET /skus`
- `GET /ingredients`
- `GET /recipes`

### Data ingestion
- `POST /imports/upload`
- `POST /imports/{id}/map-columns`
- `POST /imports/{id}/validate`
- `POST /imports/{id}/commit`
- `GET /imports/{id}`

### Forecasting
- `POST /forecasts/run`
- `GET /forecasts/latest`
- `GET /forecasts/{run_id}`

### Planning
- `POST /plans/prep/run`
- `GET /plans/prep/{id}`
- `PATCH /plans/prep/{id}/lines/{line_id}`
- `POST /plans/prep/{id}/approve`
- `POST /plans/replenishment/run`
- `GET /plans/replenishment/{id}`

### Risk and alerts
- `GET /alerts/waste`
- `GET /alerts/stockout`
- `GET /alerts/outlet-imbalance`

### Copilot / agent endpoints
- `POST /copilot/explain-plan`
- `POST /copilot/analyze-anomaly`
- `POST /copilot/run-scenario`
- `POST /copilot/daily-brief`
- `POST /copilot/map-upload`

## 8.2 Why REST is enough
These endpoints align directly with product tasks.
They are easier to document, test, and stabilize than GraphQL for this stage.

---

# 9. Frontend architecture

## 9.1 App structure
Use route groups such as:
- `/dashboard`
- `/forecast`
- `/prep-plan`
- `/replenishment`
- `/risk-center`
- `/scenario-planner`
- `/imports`
- `/settings`

## 9.2 Component strategy
Create reusable primitives for:
- KPI cards
- alert banners
- plan tables
- editable recommendation cells
- rationale drawers
- outlet/date/daypart filters
- scenario comparison panels

## 9.3 Why not a heavy design system from scratch
Too slow and unnecessary.
shadcn/ui + Tailwind gives enough consistency and speed.

---

# 10. AI framework integration strategy

# 10.1 Should we train a model now?
**No custom model training for the baseline product.**

## Why not
- too little time
- not enough clean bakery-specific data
- too hard to validate in 2 days
- risky to base the pitch on unproven training claims

## Better approach
Use a layered AI architecture:
1. baseline deterministic forecasting and planning logic
2. optional classical time-series models
3. LLM layer for explanation and interactive planning

This is stronger and more honest.

# 10.2 Where AI adds real value

## Layer A — Structured forecasting
Use classical models and deterministic logic to create reliable predictions.

## Layer B — Decision synthesis
Use a planning engine to convert predictions into actions.

## Layer C — AI explanation
Use LLMs to explain actions in plain English.

## Layer D — Agent workflows
Use structured agents for:
- daily planning brief
- scenario comparison
- anomaly investigation
- CSV mapping assistance

## Layer E — Future learning loop
Once the product has real customer data, we can train improved demand and waste models using:
- outlet-level seasonality
- daypart patterns
- weather
- promotions
- holidays
- local events
- SKU substitution patterns

---

# 11. Agentic AI architecture

## 11.1 Recommendation
Use **narrow, tool-based agents**, not open-ended autonomous agents.

## 11.2 Agent types

### Agent 1 — Daily Planning Agent
Inputs:
- latest forecast
- latest stock state
- BOM
- waste trends

Outputs:
- tomorrow's prep plan summary
- tomorrow's replenishment summary
- top 5 risks
- top 5 actions

### Agent 2 — Scenario Agent
Inputs:
- baseline prep plan
- user modifications
- optional event flags

Outputs:
- comparison of scenarios
- projected waste/stockout differences
- recommended choice

### Agent 3 — Anomaly Agent
Inputs:
- waste spike or stockout incident
- recent sales and plan data

Outputs:
- likely causes
- operational explanation
- suggested corrective actions

### Agent 4 — Import Mapping Agent
Inputs:
- uploaded CSV headers
- expected schema

Outputs:
- probable column mapping
- confidence tags
- unresolved fields for manual approval

## 11.3 Agent orchestration pattern
Each agent should:
1. receive structured input
2. call deterministic tools
3. receive structured tool outputs
4. generate explanation/recommendation text
5. require human review for high-impact actions

## 11.4 Why this is robust
This minimizes hallucination and keeps business-critical logic under our control.

---

# 12. Security and compliance

## 12.1 Minimum baseline
- encrypted secrets management
- HTTPS everywhere
- row/org-level data isolation
- role-based access control
- audit logging for edits and approvals
- signed upload URLs for file uploads

## 12.2 Auth recommendation
**Auth.js** for speed and control.

### Roles to support
- Owner/Admin
- Operations Manager
- Outlet Manager
- Planner/Purchaser
- Viewer

## 12.3 Data protection
- encrypt data in transit
- rely on managed DB encryption at rest
- avoid storing raw payment data in v1
- keep LLM prompts scrubbed of unnecessary sensitive data where possible

## 12.4 Why this matters even for prototype
If you want to look credible to judges and future pilots, the architecture should show multi-tenant safety and auditability.

---

# 13. Observability and product analytics

## 13.1 Error monitoring
**Sentry**

Track:
- frontend errors
- backend exceptions
- worker failures
- AI tool-call failures

## 13.2 Product analytics
**PostHog**

Track:
- plan page views
- approval actions
- recommendation edits
- scenario runs
- import success rates

## 13.3 Tracing
**OpenTelemetry**

Use for:
- API latency
- job execution tracing
- LLM call tracing later

## 13.4 Why observability matters early
You are building a recommendation product.
If users do not trust it, you need to understand where friction happens.

---

# 14. CI/CD and engineering workflow

## 14.1 Repository strategy
Use a **monorepo**.

Suggested layout:
```text
/apps
  /web         # Next.js frontend
  /api         # FastAPI backend
  /worker      # Celery worker entrypoint
/packages
  /ui          # shared UI components if needed
  /types       # shared contracts / schemas
  /config      # linting / tsconfig / tooling
/infrastructure
  /docker
  /terraform   # optional later
```

## 14.2 Package managers and tooling
- **pnpm** for frontend workspace
- **uv** or **poetry** for Python dependency management
- **ruff** + **black** for Python lint/format
- **eslint** + **prettier** for frontend

## 14.3 CI with GitHub Actions
Pipelines:
- lint frontend
- typecheck frontend
- run Python tests
- build Docker images
- run database migrations on deploy

## 14.4 Testing strategy

### Frontend
- **Vitest** for unit tests
- **Playwright** for core flows later

### Backend
- **pytest**
- endpoint tests
- planning engine unit tests
- forecast logic tests

### Why this test split
Most product risk is in the planning logic.
Test the recommendation engine harder than the UI.

---

# 15. Deployment strategy

## 15.1 Recommended immediate deployment
### Frontend
- **Vercel**

### Backend + worker
- **Railway** or **Render** using Docker

### Data services
- **Managed Postgres**
- **Managed Redis**
- **S3-compatible storage**

## Why this is the best immediate choice
- fast setup
- low DevOps overhead
- easy environment variables and container deployment
- good enough for demo and first pilots

## 15.2 Long-term production path
When needed, move to AWS with minimal app changes:
- **ECS/Fargate** for API and workers
- **RDS PostgreSQL**
- **ElastiCache Redis**
- **S3**
- **CloudWatch + OpenTelemetry**
- **ALB** in front of services

Because the app is Dockerized and based on standard components, this migration is straightforward.

---

# 16. Data ingestion architecture

## 16.1 MVP ingestion method
CSV-first onboarding.

### Why
- fastest route to prototype and pilot
- avoids brittle live integration work during hackathon
- works well for bakery operators exporting from POS/inventory systems

## 16.2 Ingestion flow
1. user uploads CSV
2. file stored in S3-compatible storage
3. import job created in Postgres
4. mapping agent suggests field mappings
5. validation rules run
6. cleaned rows loaded into staging tables
7. approved rows moved into production tables
8. import summary shown to user

## 16.3 Future integration path
Later add connector modules for:
- POS exports/APIs
- inventory systems
- accounting data if useful
- supplier systems if needed

Do not design the core product around any single vendor integration.

---

# 17. Data freshness and processing cadence

## Recommended cadence for v1
- on-demand forecast generation after import
- nightly refresh for next-day planning
- manual rerun when user edits assumptions

## Why this is enough
Bakery planning is usually day-ahead and daypart-driven.
We do not need streaming architecture in v1.

---

# 18. Versioning strategy

## Model and plan versioning
Persist version fields for:
- forecast model version
- planning rules version
- prompt version
- plan version

## Why
This is essential for:
- auditability
- trust
- debugging
- comparing scenario outputs later

---

# 19. What we should explicitly avoid

Do **not** choose these for v1:
- microservices
- Kubernetes
- GraphQL-first API
- separate warehouse + lakehouse stack
- custom-trained LLMs
- autonomous agent systems that take irreversible actions
- vendor-specific lock-in for core business logic
- multiple databases without a clear reason

These choices add complexity without improving the core product.

---

# 20. Recommended baseline build slice for the next 2 days

If time is tight, the minimum real slice should be:

## Frontend
- dashboard
- forecast page
- prep plan page
- replenishment page
- risk center
- optional what-if page

## Backend
- upload CSV endpoint
- mock import parser
- forecast calculation endpoint
- prep/replenishment generation endpoint
- explanation endpoint

## Data
- Postgres schema for core entities
- sample bakery dataset
- seeded plan/forecast data

## AI
- LiteLLM setup
- one daily summary prompt
- one explanation prompt
- one scenario prompt

## Observability
- Sentry
- basic logs

That slice is enough for prototype + demo + pitch.

---

# 21. Final recommendation

## Architecture verdict
Use a **Dockerized modular monolith** with:
- Next.js frontend
- FastAPI backend
- Celery workers
- PostgreSQL + pgvector
- Redis
- S3-compatible storage
- LiteLLM + structured agent workflows

## Why this is the best long-term choice
It gives you:
- fast hackathon execution
- strong product realism
- clean AI integration
- low architecture churn
- a clear migration path to production-scale infrastructure without rewriting the core app

## The most important principle
**Keep business-critical forecasting and planning deterministic. Use AI to explain, assist, and simulate.**

That is the most stable and defensible technical foundation for BakeWise.

