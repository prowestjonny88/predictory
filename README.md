# Predictory - AI-Powered Bakery Intelligence Platform

Predictory is an AI-assisted prep and replenishment copilot for multi-outlet bakery-cafe chains. It converts historical sales, inventory, and operational context into next-day action plans by outlet, SKU, and daypart.

## Hackathon Submission

| Field | Details |
|---|---|
| Team Name | CHAT GPT |
| Case Study | #8 - AI for Inclusive MSME Growth |
| Project Name | Predictory - AI-Powered Bakery Intelligence Platform |
| SDG Alignment | SDG 12 Responsible Consumption; SDG 9 Industry and Innovation |

## Team Members

| ID | Role | Name |
|---|---|---|
| P1 | Infra Lead | LAU WEI ZHONG |
| P2 | Data Engineer | TAN JUN YONG |
| P3 | Planning Engine, Team Leader | TAN KANG ZHENG |
| P4 | Frontend Engineer | TAN SZE YUNG |
| P5 | AI/LLM Engineer | NG HONG JON |

## What Predictory Solves

Bakery-cafe chains already track sales and inventory, but daily production planning is still often manual. Predictory helps reduce overproduction, prevent stockouts, improve outlet allocation, and convert ingredient planning into auditable manager actions.

## Core Features

| Feature | Description |
|---|---|
| Daily Planning | Main demo surface for forecast-backed prep recommendations, approval, edit, reject, and audit flow. |
| Demand Forecasting | Outlet x SKU x daypart forecasts with operational context. |
| Prep Planning | Recommended prep quantities with human-in-the-loop adjustments. |
| Replenishment | BOM-driven ingredient needs, shortage, reorder quantity, urgency, and driving SKUs. |
| AI Copilot | Gemini-powered explanations, daily brief support, and manager note parsing. |
| Multilingual | English, Bahasa Melayu, and Simplified Chinese response support. |

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| Backend | FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Uvicorn |
| AI Layer | LiteLLM with Google Gemini API |
| Database | SQLite for local demo; PostgreSQL for deployment |
| ML/Data | LightGBM, Pandas, NumPy, scikit-learn |

## Repo Structure

```text
apps/
  api/        FastAPI backend, migrations, forecasting, planning, copilot, tests
  web/        Next.js frontend

backend/models/              Accepted ML artifacts
apps/web/public/demo-data/   Accepted frontend demo artifacts
docs/demo/                   Demo runbook and manual checklist
scripts/ml_pipeline/         Lightweight reproducible ML pipeline
scripts/smoke_test_demo_flow.py
```

## Local Setup

### 1. Configure Environment

Create the root `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env -Force
```

For local demo, use:

```env
DATABASE_URL=sqlite:///./predictory.db
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini/gemini-2.5-flash
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ENVIRONMENT=development
ADMIN_API_TOKEN=change-me-local-admin-token
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5500,http://127.0.0.1:5500
NEXT_PUBLIC_API_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000/api/v1
```

The backend is configured for Gemini only. OpenAI, Anthropic, Vertex, and generic `LITELLM_MODEL` placeholders are intentionally not used.

### 2. Run Backend

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
alembic upgrade head
py -m db.seed
uvicorn main:app --reload --port 8000
```

Check:

```text
http://localhost:8000/health
http://localhost:8000/docs
```

### 3. Run Frontend

In another terminal:

```powershell
cd apps/web
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000"
npm.cmd install
npm.cmd run dev
```

Open:

```text
http://localhost:3000/daily-planning
```

The root route redirects to `/daily-planning`.

### 4. Run Demo Smoke Test

With the backend running:

```powershell
py scripts\smoke_test_demo_flow.py
```

Optional overrides:

```powershell
$env:API_BASE_URL="http://localhost:8000/api/v1"
$env:SMOKE_TARGET_DATE="2026-05-06"
py scripts\smoke_test_demo_flow.py
```

## Recommended Demo Flow

1. `/daily-planning` - Review forecast, prep cards, model evidence, and recommended actions.
2. Recommendation drawer - Explain p10/p50/p90, operational reason, and ingredient impact.
3. Manager note panel - Parse a note, confirm the structured assumption, then apply the adjustment.
4. Approval drawer - Edit or approve the prep line with a reason and show the audit-backed result.
5. `/replenishment` - Show ingredient need, stock on hand, shortage, reorder quantity, urgency, and driving SKUs.
6. `/forecast` or `/prep-plan` - Use only as supporting detail if the audience asks for the underlying run or plan.

## ML Artifacts vs Live Backend Forecasts

The accepted ML pipeline predictions are committed as demo artifacts under `apps/web/public/demo-data/`. Those files contain the LightGBM Step 12 forecast and optimization payload for `2022-10-01`.

The live FastAPI demo still generates operational forecast runs from the local SQLite seed data. That path uses the backend `weighted_blend_backend` forecast engine so managers can create, edit, approve, reject, audit, and refresh replenishment against real database rows. The backend loads accepted ML artifacts for model registry and quality metrics, but full LightGBM feature-row inference is not yet wired into `forecasting.engine`.

Use the frontend fallback/demo payload when you need to show the exact accepted ML-pipeline predictions. Use the live backend route when you need to show the interactive API workflow.

For the current live demo, forecast generation is intentionally labeled as `weighted_blend_fallback` unless LightGBM feature-row inference is wired end to end. The offline LightGBM artifacts remain loaded as validation/model evidence. Daily Planning surfaces `data_source` so rehearsals can distinguish `backend` from `demo_fallback`, and the frontend must not fabricate uncertainty bands or financial exposure when backend fields are missing.

## Testing

Backend:

```powershell
py -m compileall apps\api
py -m pytest apps\api\tests -p no:cacheprovider
```

Frontend:

```powershell
cd apps/web
npm.cmd run typecheck
npm.cmd run build
```

Smoke test:

```powershell
py scripts\smoke_test_demo_flow.py
```

## Troubleshooting

### Backend tries to connect to `ep-xxxx.neon.tech`

Your `.env` is using the placeholder Postgres URL. For local testing, set:

```env
DATABASE_URL=sqlite:///./predictory.db
```

### Gemini copilot does not respond

Verify the backend sees the Gemini config:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -c "from copilot.router import _resolve_litellm_config; print(_resolve_litellm_config()[0])"
```

Expected:

```text
gemini/gemini-2.5-flash
```

Then restart `uvicorn`; environment changes are not picked up by an already-running server process.

### Frontend cannot connect to backend

Check `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Reference Docs

- [Product Requirements](./docs/prd.md)
- [Architecture Notes](./docs/architecture.md)
- [Documentation](./docs/documentation.md)
- [Project Report](./docs/Predictory_Report.md)
- [API Contracts](./apps/api/CONTRACTS.md)
- [Copilot Examples](./apps/api/copilot/EXAMPLES.md)
- [Demo Runbook](./docs/demo/runbook.md)
- [Manual Demo Checklist](./docs/demo/manual_demo_checklist.md)
