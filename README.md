# Predictory

Predictory is an AI-assisted prep and replenishment copilot for multi-outlet bakery-cafe chains.

This repository contains a working prototype with:
- a FastAPI backend
- a Next.js frontend
- deterministic forecasting, prep, replenishment, and alert logic
- AI explanation, daily brief, daily actions, and scenario support
- multilingual UI and copilot output in English, Bahasa Melayu, and Simplified Chinese

## Project Details

### What Predictory solves

Bakery-cafe chains already track sales and inventory, but daily production planning is still often manual. That leads to:
- overproduction and end-of-day waste
- stockouts during morning and lunch peaks
- inconsistent outlet allocation
- excess ingredient purchasing
- wasted labor and oven capacity

Predictory addresses that gap by turning historical demand and operational data into next-day actions.

### Core product capabilities

- Forecast demand by outlet and daypart
- Recommend next-day prep quantities by SKU
- Convert prep plans into ingredient replenishment needs
- Flag likely waste risks before production starts
- Flag likely stockout risks before peak service windows
- Explain recommendations in plain language
- Let users edit and approve plans
- Support what-if scenario planning

### SDG alignment

- Primary: **SDG 12 - Responsible Consumption and Production**
- Secondary: **SDG 9 - Industry, Innovation and Infrastructure**

Predictory is primarily aligned to SDG 12 because it targets bakery waste reduction and more disciplined use of ingredients, labor, and production capacity.

## Current Scope

### Frontend routes

- `/dashboard`
- `/forecast`
- `/prep-plan`
- `/replenishment`
- `/risk-center`
- `/copilot`
- `/scenario-planner`

### Backend scope

The current backend includes:
- ingestion APIs
- catalog APIs
- forecast generation and forecast context
- prep plan generation and approval
- replenishment plan generation
- waste and stockout alert generation
- copilot explanation, daily brief, daily actions, and scenario endpoints

For the exact API contracts, see [apps/api/CONTRACTS.md](./apps/api/CONTRACTS.md).

## Demo Dataset

The repository includes a seeded demo bakery brand: **Roti Lane Bakery**.

Seeded demo characteristics:
- 5 outlets: KLCC, Bangsar, Mid Valley, Bukit Bintang, Damansara
- 8+ SKUs including Butter Croissant as the hero SKU
- 30 days of historical sales
- realistic waste and stockout patterns

Important seeded demo scenarios:
- **Bangsar** shows persistent croissant overproduction and elevated waste
- **Mid Valley** shows repeated morning croissant stockout behavior

The seed script lives in [apps/api/db/seed.py](./apps/api/db/seed.py).

## Tech Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, React 18, Tailwind CSS, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.x, Alembic |
| AI | LiteLLM, LangGraph |
| Data | PostgreSQL or local SQLite fallback |

## Repo Structure

```text
apps/
  api/        FastAPI backend, models, migrations, tests
  web/        Next.js frontend

docs/
  Predictory_Report.md
  Predictory_Report.pdf

Root docs:
  prd_v_1_predictory_bakery_copilot.md
  tech_stack_architecture_v_1_predictory.md
  TEAM_PLAN.md
```

## Local Setup

### Prerequisites

- Python 3.12+
- Node.js 20+ or newer
- npm
- `corepack` available with Node

### 1. Configure environment

Create the root `.env` file based on [`.env.example`](./.env.example).

Minimum local demo config:

```env
DATABASE_URL=sqlite:///./predictory.db
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002

GOOGLE_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini/gemini-2.5-flash

WEATHER_FETCH_ENABLED=true
WEATHER_TIMEOUT_SECONDS=2
HOLIDAY_DEFAULT_COUNTRY=MY
```

Notes:
- If you do not set a Gemini key, the app still works, but copilot endpoints will fall back to deterministic text.
- Weather uses Open-Meteo and does not require an API key.
- Holidays are seeded or CSV-driven and do not require an API key.

### 2. Run the backend

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
- `http://localhost:8000/` may return `{"detail":"Not Found"}`. That is expected.

### 3. Run the frontend

Create frontend env config:

```powershell
cd apps/web
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000"
```

If `pnpm` is not installed on your machine, activate it through `corepack`:

```powershell
corepack enable
corepack prepare pnpm@latest --activate
```

Then run:

```powershell
cd apps/web
pnpm install
pnpm dev
```

If `pnpm` is still not on PATH in the current shell, use:

```powershell
corepack pnpm install
corepack pnpm dev
```

Frontend URL:
- usually `http://localhost:3000`
- if 3000 is occupied, Next.js will choose another port and print it in the terminal

## Recommended Demo Flow

Use this order for a demo walkthrough:

1. `/dashboard`
2. `/forecast`
3. `/prep-plan`
4. `/replenishment`
5. `/risk-center`
6. `/copilot`
7. `/scenario-planner`

Best demo states:
- use the seeded Roti Lane data
- choose a date with visible alerts and action items
- show one generated copilot brief or action plan
- show one scenario result
- show one multilingual screen

## Troubleshooting

### Alembic fails with `Can't load plugin: sqlalchemy.dialects:driver`

Cause:
- `DATABASE_URL` is missing, and Alembic is falling back to the placeholder value in `alembic.ini`

Fix:
- set a real `DATABASE_URL` in the root `.env`
- for local demo use:

```env
DATABASE_URL=sqlite:///./predictory.db
```

### Alembic fails because tables already exist

Cause:
- an old local SQLite file already exists without proper Alembic migration history

Fix for local demo reset:

```powershell
Remove-Item .\predictory.db -Force -ErrorAction SilentlyContinue
Remove-Item .\apps\api\predictory.db -Force -ErrorAction SilentlyContinue
```

Then rerun:

```powershell
cd apps/api
alembic upgrade head
python -m db.seed
```

### Frontend cannot call backend

Check [apps/web/.env.local](./apps/web/.env.local):

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### `pnpm` is not recognized

Use:

```powershell
corepack enable
corepack prepare pnpm@latest --activate
```

Or fallback to:

```powershell
npm install -g pnpm
```

### Local Next.js production build fails with `spawn EPERM`

This has been observed as a local Windows/OneDrive environment issue. For demo usage:
- use `pnpm dev`
- rely on `pnpm typecheck` and `pnpm lint` for validation

## Testing

Backend:

```powershell
.\.venv\Scripts\python -m pytest -q apps/api/tests
```

Frontend:

```powershell
cd apps/web
npm run typecheck
npm run lint
```

## Key APIs

- `GET /health`
- `GET /api/v1/outlets`
- `GET /api/v1/skus`
- `GET /api/v1/forecast-context`
- `GET /api/v1/forecast-overrides`
- `POST /api/v1/forecast-overrides`
- `GET /api/v1/api/daily-plan/{date}`
- `POST /api/v1/plans/prep/run`
- `POST /api/v1/plans/replenishment/run`
- `POST /api/v1/copilot/daily-brief`
- `POST /api/v1/copilot/explain-plan`
- `POST /api/v1/copilot/run-scenario`
- `POST /api/v1/copilot/daily-actions`

See also:
- [apps/api/CONTRACTS.md](./apps/api/CONTRACTS.md)
- [apps/api/copilot/EXAMPLES.md](./apps/api/copilot/EXAMPLES.md)

## Multilingual Support

The demo currently supports:
- English (`en`)
- Bahasa Melayu (`ms`)
- Simplified Chinese (`zh-CN`)

Notes:
- UI language is switched in-app from the sidebar
- the selected language is persisted in `localStorage`
- raw business data such as SKU names, outlet names, quantities, and IDs remain language-neutral
- copilot prose can be requested in all three supported languages

## AI Disclosure

This project was developed with AI assistance.

### Confirmed use

- **OpenAI Codex / ChatGPT**
  - used for coding assistance
  - used for debugging support
  - used for implementation planning and architecture reasoning
  - used for technical writing and documentation drafting support

### Important note for external submission

If your team used additional AI tools such as:
- GitHub Copilot
- Claude
- Gemini
- Midjourney
- any other AI-assisted coding, writing, or image-generation tool

add them explicitly to this section before external submission or judging.

## Reference Docs

- [PRD](./prd_v_1_predictory_bakery_copilot.md)
- [Architecture](./tech_stack_architecture_v_1_predictory.md)
- [Team Plan](./TEAM_PLAN.md)
- [Project Report Draft](./docs/Predictory_Report.md)
- [Project Report PDF](./docs/Predictory_Report.pdf)
