# BakeWise

BakeWise is an AI prep and replenishment copilot for bakery-cafe chains. This `predictory` repo currently contains a FastAPI backend plus a Next.js frontend for day-ahead forecasting, prep planning, replenishment, waste alerts, stockout alerts, and copilot-style explanations.

## What the product does

- Forecasts demand by outlet and daypart
- Recommends next-day prep quantities by SKU
- Converts prep plans into ingredient replenishment needs
- Flags likely waste and stockout risks before service
- Generates AI-assisted daily briefs and what-if scenarios

## Repo structure

```text
apps/
  api/        FastAPI backend, SQLAlchemy models, Alembic migrations, tests
  web/        Next.js frontend

Root docs:
  prd_v_1_bake_wise_bakery_copilot.md
  tech_stack_architecture_v_1_bake_wise.md
  TEAM_PLAN.md
```

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, TanStack Query |
| Backend | FastAPI, SQLAlchemy, Alembic |
| AI | LiteLLM, LangGraph |
| Data | PostgreSQL or local SQLite fallback |

## Quick start

### 1. Create the root env file

Copy the root [`.env.example`](./.env.example) to `.env` and fill in the values you want to use.

Notes:
- `DATABASE_URL` supports Neon/Postgres or the local SQLite fallback shown in the example file.
- The backend loads environment variables from the repo root.

### 2. Run the backend

```bash
cd apps/api

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

alembic upgrade head
python -m db.seed
uvicorn main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 3. Run the frontend

```bash
cd apps/web

npm install
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local
npm run dev
```

Frontend: `http://localhost:3000`

## Useful backend endpoints

- `GET /health`
- `GET /api/v1/outlets`
- `GET /api/v1/skus`
- `GET /api/v1/api/daily-plan/{date}`
- `POST /api/v1/plans/prep/run`
- `POST /api/v1/plans/replenishment/run`
- `POST /api/v1/copilot/daily-brief`
- `POST /api/v1/copilot/run-scenario`

## Tests

```bash
cd apps/api
pytest -q
```

## Main frontend routes

| Route | Purpose |
|---|---|
| `/dashboard` | KPI overview, top actions, risk summary |
| `/forecast` | Outlet and daypart demand forecast |
| `/prep-plan` | Prep recommendations and approval flow |
| `/replenishment` | Ingredient reorder recommendations |
| `/risk-center` | Waste and stockout alerts |
| `/copilot` | Daily brief and AI explanation flows |
| `/scenario-planner` | What-if scenario simulation |

## Reference docs

- [PRD](./prd_v_1_bake_wise_bakery_copilot.md)
- [Architecture](./tech_stack_architecture_v_1_bake_wise.md)
- [Team plan](./TEAM_PLAN.md)
