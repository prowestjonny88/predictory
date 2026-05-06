# Predictory - AI-Powered Bakery Intelligence Platform

Predictory is an AI-assisted prep and replenishment copilot for multi-outlet bakery-cafe chains. It converts imported operational data and trained LightGBM artifacts into next-day action plans by outlet, SKU, and daypart.

## Runtime Contract

Predictory does not synthesize production values when required data is missing. Forecast, planning, dashboard, replenishment, and Copilot pages may show loading, empty, or error states, but runtime paths must not invent forecast, prep, uncertainty, replenishment, financial exposure, or Copilot values.

API failures are explicit:

- `422` means required business data has not been imported or is invalid.
- `503` means the model bundle or a required external provider is unavailable.

## Core Features

| Feature | Description |
|---|---|
| Daily Planning | Forecast-backed prep recommendations, approval, edit, reject, and audit flow. |
| Demand Forecasting | LightGBM outlet x SKU x daypart forecasts with trained residual p10/p50/p90 bands. |
| Prep Planning | Optimizer-backed prep quantities with human-in-the-loop adjustments. |
| Replenishment | BOM-driven ingredient need, shortage, reorder quantity, urgency, and driving SKUs. |
| AI Copilot | Gemini-powered explanations, daily brief support, and manager note parsing. |
| Multilingual | English, Bahasa Melayu, and Simplified Chinese response support. |

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| Backend | FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Uvicorn |
| AI Layer | LiteLLM with Google Gemini API |
| Database | SQLite for local development; PostgreSQL for deployment |
| ML/Data | LightGBM, Pandas, NumPy, scikit-learn |

## Repo Structure

```text
apps/
  api/        FastAPI backend, migrations, forecasting, planning, copilot, tests
  web/        Next.js frontend

backend/models/              LightGBM model, feature schema, metrics, residual bands
scripts/ml_pipeline/         Reproducible ML training pipeline
scripts/smoke_test_live_flow.py
```

## Local Setup

### 1. Configure Environment

Create the root `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env -Force
```

Use local development values:

```env
DATABASE_URL=sqlite:///./predictory.db
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini/gemini-2.5-flash
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ENVIRONMENT=development
ADMIN_API_TOKEN=change-me-local-admin-token
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

### 2. Run Backend

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
alembic upgrade head
py -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Check:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

### 3. Import Operational Data

Populate a clean database through `/api/v1/imports/upload` before running forecasts. Supported CSV types:

- `outlets`
- `products`
- `ingredients`
- `recipes`
- `sales`
- `inventory`
- `waste`
- `weather`
- `holidays`

Required references are strict: sales, inventory, waste, and recipe rows must reference outlets, SKUs, and ingredients that have already been imported.
CSV import requires `Authorization: Bearer <ADMIN_API_TOKEN>` unless local development explicitly sets `ALLOW_UNAUTHENTICATED_IMPORTS=true`.

Before generating a forecast, check:

```text
GET /api/v1/forecast-readiness?target_date=YYYY-MM-DD
```

### 4. Run Frontend

In another terminal:

```powershell
cd apps/web
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
npm.cmd install
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

Open:

```text
http://127.0.0.1:3000/daily-planning
```

The root route redirects to `/daily-planning`.

## Operator Flow

1. Import outlets, SKUs, ingredients, recipe BOM, sales history, inventory, waste, weather, and holidays.
2. Check forecast readiness for the planning date.
3. Generate a forecast run.
4. Review `/daily-planning` recommendations and model evidence.
5. Use manager notes only after confirming the parsed adjustment.
6. Approve or edit prep lines with an operator reason.
7. Review `/replenishment` for ingredient shortage and reorder actions.

## ML Runtime

The live backend uses the trained LightGBM bundle in `backend/models/`:

- `lightgbm_p50_v1.pkl`
- `feature_schema_v1.json`
- `encoded_feature_schema_step8.json`
- `residual_bands_v1.json`
- `model_metrics_v1.json`

Forecast generation builds encoded feature rows from database data for each outlet/SKU/daypart/date. The runtime engine is `lightgbm_mlops_prototype`, and forecast lines use method `lightgbm_p50_v1`. Residual artifacts provide p10/p50/p90 bands; missing artifacts fail closed.

## Testing

Backend:

```powershell
py -m compileall apps\api\admin apps\api\alerts apps\api\catalog apps\api\copilot apps\api\db apps\api\forecasting apps\api\ingestion apps\api\ops_data apps\api\planning apps\api\services
py -m pytest apps\api\tests -p no:cacheprovider
```

Frontend:

```powershell
cd apps/web
npm.cmd run typecheck
npm.cmd run build
```

Live smoke test, after data import:

```powershell
py scripts\smoke_test_live_flow.py
```

## Troubleshooting

### Readiness reports missing data

Import the blocker listed by `/api/v1/forecast-readiness`. Forecast and Daily Planning will not show numbers until readiness passes.

### Forecast endpoint returns `503`

Verify the files in `backend/models/` exist and are readable by the backend process.

### Copilot endpoint returns `503`

Verify the backend sees Gemini config:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -c "from copilot.router import _resolve_litellm_config; print(_resolve_litellm_config()[0])"
```

Then restart `uvicorn`; environment changes are not picked up by an already-running server process.

### Frontend cannot connect to backend

Check `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Reference Docs

- [Product Requirements](./docs/prd.md)
- [Architecture Notes](./docs/architecture.md)
- [Documentation](./docs/documentation.md)
- [Project Report](./docs/Predictory_Report.md)
- [API Contracts](./apps/api/CONTRACTS.md)
- [Copilot Examples](./apps/api/copilot/EXAMPLES.md)
