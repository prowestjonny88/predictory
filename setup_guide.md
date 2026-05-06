# Predictory Setup Guide

This guide is for teammates who want to run Predictory locally and try every major feature, including LightGBM forecasts, Daily Planning, Gemini Copilot, and Telegram forecast notifications.

## 1. Prerequisites

- Windows PowerShell
- Python 3.12
- Node.js 20+
- Git
- A Google AI Studio Gemini API key
- Optional: a Telegram bot token and one or more Telegram chat IDs

## 2. Clone and Enter the Repo

```powershell
git clone <repo-url>
cd predictory
```

Do not commit real secrets. Use `.env` locally only.

## 3. Configure Environment

Create a local `.env` from the example:

```powershell
Copy-Item .env.example .env -Force
```

Edit `.env`:

```env
DATABASE_URL=sqlite:///./predictory.db
GEMINI_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini/gemini-3-flash-preview
SECRET_KEY=change-me-in-production-use-openssl-rand-hex-32
ENVIRONMENT=development
ADMIN_API_TOKEN=change-me-local-admin-token
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

For Telegram, add:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

`TELEGRAM_CHAT_ID` can be comma-separated for multiple chats.

## 4. Install Backend

Use the API virtualenv explicitly. Do not start the backend with `py -m uvicorn`, because that may use global Python and miss packages such as `litellm`.

```powershell
cd apps/api
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Check Gemini and LiteLLM config:

```powershell
.\.venv\Scripts\python.exe -c "from copilot.router import _resolve_litellm_config; print(_resolve_litellm_config()[0])"
```

Expected:

```text
gemini/gemini-3-flash-preview
```

## 5. Run Backend

From `apps/api`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Check:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

If port `8000` is already in use:

```powershell
netstat -ano | Select-String ':8000'
Stop-Process -Id <PID> -Force
```

## 6. Install and Run Frontend

Open a second PowerShell terminal:

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

If port `3000` is already in use:

```powershell
netstat -ano | Select-String ':3000'
Stop-Process -Id <PID> -Force
```

## 7. Import Operational Data

Predictory fails closed when required data is missing. Import data before expecting forecast or planning numbers.

Supported import types:

- `outlets`
- `products`
- `ingredients`
- `recipes`
- `sales`
- `inventory`
- `waste`
- `weather`
- `holidays`

Import master data before dependent rows:

1. outlets
2. products
3. ingredients
4. recipes
5. sales
6. inventory
7. waste
8. weather
9. holidays

Upload CSVs through Swagger:

```text
http://127.0.0.1:8000/docs
POST /api/v1/imports/upload
```

Use:

```text
Authorization: Bearer change-me-local-admin-token
```

Or use PowerShell:

```powershell
$token = "change-me-local-admin-token"
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/api/v1/imports/upload?data_type=products" `
  -Method Post `
  -Headers @{ Authorization = "Bearer $token" } `
  -Form @{ file = Get-Item "C:\path\to\products.csv" }
```

For the provided transaction-style bakery sales file, import master data first, then sales. If your sales CSV does not include outlet codes, pass `default_outlet_code=<existing_outlet_code>`.

## 8. Check Readiness

Before running forecasts:

```text
GET http://127.0.0.1:8000/api/v1/forecast-readiness?target_date=YYYY-MM-DD
```

The response must show:

```json
{ "ready": true }
```

If it returns blockers, import the missing data category. Forecast and Daily Planning intentionally show no synthetic numbers while blockers remain.

## 9. Try the Core Features

### Forecast Evidence

1. Open `/forecast`.
2. Select date and outlet.
3. Click `Run Forecast`.
4. Confirm the page shows `lightgbm_mlops_prototype` / `lightgbm_p50_v1`.

### Daily Planning

1. Open `/daily-planning`.
2. Confirm readiness passes.
3. Review top prep recommendations.
4. Open model evidence and uncertainty details.
5. Try approve, reject, or edit flows with an operator reason.

### Replenishment

1. Open `/replenishment`.
2. Confirm ingredient need, stock, shortage, and reorder values appear.
3. Values should be backend-provided from BOM and inventory data.

### SKU Catalog

1. Open `/catalog`.
2. Confirm SKU and unit cost values.
3. If cost is unavailable, the UI should show unavailable instead of estimating.

### Dashboard and Risk Center

1. Open `/dashboard`.
2. Review full-plan summary KPIs.
3. Open `/risk-center`.
4. Review stockout and waste alerts.

### Approved Prep Sheet and Stock

1. Open `/prep-plan`.
2. Confirm approved prep sheet data.
3. Open `/stock`.
4. Confirm inventory-backed stock information.

### Scenario Planner

1. Open `/scenario-planner`.
2. Run a scenario.
3. Confirm it is labelled as heuristic scenario output.

## 10. Try Gemini Copilot

Gemini is used for explanations and manager-note parsing. It must not invent forecast, prep, cost, inventory, or replenishment numbers.

Try:

- Recommendation card: click `Why this amount?`
- Dashboard KPI explanation buttons
- Replenishment or risk explanation buttons
- Copilot page daily brief
- Manager note parser in Daily Planning

If Copilot returns:

```text
No module named 'litellm'
```

the backend is running with global Python. Restart it with:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

If Copilot returns:

```text
LLM provider returned an incomplete explanation
```

Gemini responded with incomplete text twice. Retry the action. The backend intentionally does not show broken or invented explanation text.

## 11. Try Manager Notes

In Daily Planning:

1. Enter a note like `Increase morning Pastry prep at KLCC Mall by 10%`.
2. Confirm Gemini parses outlet, daypart, category, adjustment, and reason.
3. Review the impact preview.
4. Confirm or ignore.

Current behavior is:

```text
application_mode = prep_edit_only
```

Manager notes edit prep lines only. They do not rerun LightGBM or create a forecast override.

## 12. Try Telegram Notifications

Telegram sends a forecast summary after forecast generation, if credentials are configured.

### Create Telegram Bot

1. Open Telegram.
2. Message `@BotFather`.
3. Run `/newbot`.
4. Copy the bot token into `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
```

### Get Chat ID

For a direct chat:

1. Send any message to your bot.
2. Visit:

```text
https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getUpdates
```

3. Copy `message.chat.id` into `.env`:

```env
TELEGRAM_CHAT_ID=your_chat_id
```

For a group chat:

1. Add the bot to the group.
2. Send a message in the group.
3. Call `getUpdates` and use the group `chat.id`.

Restart backend after changing `.env`.

### Test Telegram Manually

First generate at least one forecast run. Then:

```powershell
cd apps/api
.\.venv\Scripts\python.exe test_telegram.py
```

Expected terminal output:

```text
Triggering telegram notification for ForecastRun ID: <id>
Done! Check your Telegram.
```

Expected Telegram result: a Predictory forecast summary message with top forecasted products.

## 13. Run Verification

Backend:

```powershell
cd apps/api
.\.venv\Scripts\python.exe -m pytest tests -p no:cacheprovider
```

Frontend:

```powershell
cd apps/web
npm.cmd run typecheck
npm.cmd run build
```

Live smoke test after imports:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000/api/v1"
$env:SMOKE_TARGET_DATE="YYYY-MM-DD"
$env:SMOKE_REQUIRE_LLM="1"
py scripts\smoke_test_live_flow.py
```

## 14. Common Issues

### Frontend says failed to fetch

Check backend is running:

```text
http://127.0.0.1:8000/health
```

Check `apps/web/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Restart frontend after changing `.env.local`.

### Forecast or Daily Planning shows setup blockers

Call readiness and import the listed missing data:

```text
GET /api/v1/forecast-readiness?target_date=YYYY-MM-DD
```

### Gemini model mismatch

Use the LiteLLM-prefixed model name:

```env
GEMINI_MODEL=gemini/gemini-3-flash-preview
```

### Telegram does nothing

Check:

- `.env` has `TELEGRAM_BOT_TOKEN`
- `.env` has `TELEGRAM_CHAT_ID`
- backend was restarted after editing `.env`
- at least one forecast run exists
- the bot has permission to message the chat or group

