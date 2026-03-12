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
- For copilot LLMs, you can use `GEMINI_API_KEY` / `GOOGLE_API_KEY` for Google AI Studio, or `VERTEXAI_PROJECT` + `VERTEXAI_LOCATION` for Vertex AI.
- Copilot endpoint examples and sample payloads are in [`apps/api/copilot/EXAMPLES.md`](./apps/api/copilot/EXAMPLES.md).

### 2. Run the backend (PowerShell)

```powershell
cd apps/api

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

alembic upgrade head
python -m db.seed
uvicorn main:app --reload --port 8000
```

Backend checks:
- Health: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`

Important:
- `http://localhost:8000/` may show `{\"detail\":\"Not Found\"}`. This is expected because no root `/` route is defined.

### 3. Run the frontend (PowerShell)

```powershell
cd apps/web

pnpm install
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000"

# Start dev server (default Next.js port behavior)
pnpm dev
```

Frontend URL:
- Usually `http://localhost:3000`
- If 3000 is already in use, Next.js will auto-pick another port (for example 3001 or 3002). Use the URL printed in terminal.

Optional (force a specific frontend port):

```powershell
pnpm dev -- -p 3002
```

Then open: `http://localhost:3002/dashboard`

### 4. Verify end-to-end quickly

1. Backend terminal is running `uvicorn` on port 8000.
2. Frontend terminal is running `pnpm dev` on the printed port.
3. Open frontend dashboard (`/dashboard`) and confirm data loads.

### 5. Common issues

- **Backend shows `Not Found` at `/`**
  - Use `/health` or `/docs` instead.
- **Frontend does not open on 3000**
  - Port 3000 may be occupied by another process (for example Postgres).
  - Use terminal output URL or force a port with `pnpm dev -- -p 3002`.
- **Frontend can load but API calls fail**
  - Check `apps/web/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`.

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
