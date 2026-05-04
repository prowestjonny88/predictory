# Predictory Demo Runbook

This runbook is for the final integrated demo. The canonical user-facing path is Daily Planning.

## 1. Configure Environment

From the repo root:

```powershell
Copy-Item .env.example .env -Force
```

For local demo, set at minimum:

```env
DATABASE_URL=sqlite:///./predictory.db
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
ADMIN_API_TOKEN=change-me-local-admin-token
NEXT_PUBLIC_API_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000/api/v1
```

Gemini/OpenAI keys are optional. Copilot endpoints have deterministic fallback text when no provider is configured.

## 2. Backend

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

## 3. Frontend

In a second terminal:

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

## 4. Smoke Test

With the backend running:

```powershell
py scripts\smoke_test_demo_flow.py
```

Optional:

```powershell
$env:API_BASE_URL="http://localhost:8000/api/v1"
$env:SMOKE_TARGET_DATE="2026-05-06"
py scripts\smoke_test_demo_flow.py
```

The smoke test uses a future date by default so it does not disturb the primary visible demo date.

## 5. Verification Before Handoff

```powershell
py -m compileall apps\api
py -m pytest apps\api\tests -p no:cacheprovider

cd apps/web
npm.cmd run typecheck
npm.cmd run build
```

If `apps/web/tsconfig.tsbuildinfo` appears after frontend checks, restore it before commit:

```powershell
git restore apps/web/tsconfig.tsbuildinfo
```

## 6. Safe Reset

To reset local generated runtime files while preserving accepted ML artifacts and frontend demo data:

```powershell
.\scripts\reset_demo_env.ps1
```

Do not delete:

```text
backend/models/
apps/web/public/demo-data/
```

## 7. ML Artifact Predictions vs Live Backend Runs

The accepted ML-pipeline predictions are already committed in:

```text
apps/web/public/demo-data/
```

Those files are the LightGBM Step 12 forecast/optimization payload for `2022-10-01`.

The local backend still generates live forecast runs from the seeded SQLite operations data using `weighted_blend_backend`. That keeps the interactive manager workflow working: generate a plan, edit quantities, approve/reject, write audit events, and refresh replenishment. The backend model registry loads the accepted LightGBM artifacts and metrics, but direct LightGBM feature-row inference is not yet wired into `forecasting.engine`.
