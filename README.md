# 🍞 Predictory — AI-Powered Bakery Intelligence Platform

> **Reduce waste. Prevent stockouts. Bake smarter.**

Predictory is an AI-assisted prep and replenishment copilot for multi-outlet bakery-cafe chains. It turns historical sales and inventory data into next-day action plans — by outlet, by SKU, by daypart.

---

## 🎓 Hackathon Submission

| Field | Details |
|---|---|
| **Team Name** | CHAT GPT |
| **Case Study** | #8 — AI for Inclusive MSME Growth |
| **Project Name** | Predictory — AI-Powered Bakery Intelligence Platform |
| **SDG Alignment** | 🌱 SDG 12 (Responsible Consumption) · 🏭 SDG 9 (Industry & Innovation) |

### 👥 Team Members

| ID | Role | Name |
|---|---|---|
| P1 | Infra Lead | LAU WEI ZHONG |
| P2 | Data Engineer | TAN JUN YONG |
| P3 | Planning Engine *(Team Leader)* | TAN KANG ZHENG |
| P4 | Frontend Engineer | TAN SZE YUNG |
| P5 | AI/LLM Engineer | NG HONG JON |

---

## 📎 Submission Links

| Resource | Link |
|---|---|
| 📄 **Project Report** | [PDF](./docs/Predictory_Report.pdf) · [Predictory_Report.md](./docs/Predictory_Report.md) |
| 🎬 **Demo Video** | ▶️ _[Insert YouTube Link Here]_ |

---

## 🚀 What Predictory Solves

Bakery-cafe chains already track sales and inventory, but daily production planning is still often manual. That leads to:

- 🗑️ Overproduction and end-of-day waste
- ❌ Stockouts during morning and lunch peaks
- 🏭 Inconsistent outlet allocation from central kitchen
- 💸 Excess ingredient purchasing
- ⏱️ Wasted labor and oven capacity

Predictory closes that gap by converting operational data into **next-day, outlet-level, daypart-aware action plans**.

---

## ✨ Core Features

| Feature | Description |
|---|---|
| 📊 **Executive Dashboard** | KPI cards, risk scores, and interactive forecast charts at a glance |
| 🔮 **Demand Forecasting** | Outlet × SKU × daypart forecasts with holiday, weather, and promo adjustments |
| 🥐 **Prep Planning** | AI-generated prep quantities with human-in-the-loop editing and approval |
| 📦 **Replenishment** | BOM-driven ingredient reorder actions with urgency classification |
| ⚠️ **Risk Centre** | Proactive waste hotspot and stockout alerts before service begins |
| 🤖 **AI Copilot** | Daily brief, prioritized actions, and what-if scenario simulation |
| 🌍 **Multilingual** | English · Bahasa Melayu · 简体中文 |

---

## 🧱 Tech Stack

| Layer | Technologies |
|---|---|
| 🖥️ **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, TanStack Query, Recharts |
| ⚙️ **Backend** | FastAPI, SQLAlchemy 2.x, Alembic, Pydantic v2, Uvicorn |
| 🧠 **AI Layer** | LiteLLM, LangGraph, Google Gemini 2.5 (via API) |
| 🗄️ **Database** | PostgreSQL *(prod)* · SQLite *(local demo)* |
| 📊 **Data** | Pandas, NumPy, python-dateutil |

---

## 🗂️ Repo Structure

```text
apps/
  api/        ← FastAPI backend (models, migrations, forecasting, copilot, tests)
  web/        ← Next.js frontend (dashboard, forecast, prep, risk, copilot)

docs/
  Predictory_Report.md   ← Full technical report
  Predictory_Report.pdf
  screenshot/            ← UI screenshots for report

Root docs:
  docs/prd.md
  docs/architecture.md
  docs/documentation.md
  TEAM_PLAN.md
```

---

## 🛠️ Local Setup

### Prerequisites

- 🐍 Python 3.12+
- 🟢 Node.js 20+
- 📦 `corepack` (bundled with Node.js 16.9+)

---

### Step 1 — Configure Environment

Create the root `.env` file (copy from `.env.example`):

```env
DATABASE_URL=sqlite:///./predictory.db
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001

GOOGLE_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini/gemini-2.5-flash

WEATHER_FETCH_ENABLED=true
WEATHER_TIMEOUT_SECONDS=2
HOLIDAY_DEFAULT_COUNTRY=MY
```

> 💡 **No Gemini key?** The app still works — copilot endpoints fall back to deterministic text output.  
> 🌤️ **Weather** uses [Open-Meteo](https://open-meteo.com/) — no API key needed.  
> 📅 **Holidays** are seeded via the seed script — no API key needed.

---

### Step 2 — Run the Backend

```powershell
cd apps/api

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

alembic upgrade head
python -m db.seed

uvicorn main:app --reload --port 8000
```

✅ **Check it's running:**
- Health check: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`

> ℹ️ `http://localhost:8000/` returning `{"detail":"Not Found"}` is expected — use `/health` or `/docs`.

---

### Step 3 — Run the Frontend

```powershell
cd apps/web

# Create env config
Set-Content .env.local "NEXT_PUBLIC_API_URL=http://localhost:8000"

# Enable pnpm if not already active
corepack enable
corepack prepare pnpm@latest --activate

# Install and run
pnpm install
pnpm dev
```

> Or use `corepack pnpm install` and `corepack pnpm dev` if `pnpm` isn't on PATH.

🌐 Frontend: **`http://localhost:3000`**

---

## 🎬 Recommended Demo Flow

Walk through in this order to tell the best story:

1. 🏠 `/dashboard` — Executive overview, KPI cards, interactive charts
2. 📈 `/forecast` — Select an outlet, show demand drivers (weather, holidays)
3. 🥐 `/prep-plan` — Generate plan, override a line, approve
4. 📦 `/replenishment` — Show urgency indicators and ingredient needs
5. ⚠️ `/risk-center` — Highlight the Bangsar waste and Mid Valley stockout alerts
6. 🤖 `/copilot` — Generate a daily brief and action plan
7. 🔮 `/scenario-planner` — Run a 30% demand spike scenario

---

## 🧪 Testing

**Backend:**
```powershell
.\.venv\Scripts\python -m pytest -q apps/api/tests
```

**Frontend:**
```powershell
cd apps/web
npm run typecheck
npm run lint
```

---

## 🔧 Troubleshooting

<details>
<summary><strong>Alembic fails — "Can't load plugin: sqlalchemy.dialects:driver"</strong></summary>

**Cause:** `DATABASE_URL` is missing or not set.  
**Fix:** Add to root `.env`:
```env
DATABASE_URL=sqlite:///./predictory.db
```
</details>

<details>
<summary><strong>Alembic fails — tables already exist</strong></summary>

**Fix:** Delete the old DB and re-migrate:
```powershell
Remove-Item .\predictory.db -Force -ErrorAction SilentlyContinue
Remove-Item .\apps\api\predictory.db -Force -ErrorAction SilentlyContinue
cd apps/api
alembic upgrade head
python -m db.seed
```
</details>

<details>
<summary><strong>Frontend can't connect to backend</strong></summary>

Check `apps/web/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
</details>

<details>
<summary><strong>pnpm not recognized</strong></summary>

```powershell
corepack enable
corepack prepare pnpm@latest --activate
# or: npm install -g pnpm
```
</details>

<details>
<summary><strong>Next.js build fails with "spawn EPERM" on Windows/OneDrive</strong></summary>

Use dev mode only — this is a local Windows/OneDrive file-locking issue:
```powershell
pnpm dev   # ✅ use this
pnpm build # ❌ may fail locally
```
</details>

---

## 🤖 AI Disclosure

This project was developed with a multi-layered AI stack, which is fully disclosed below as required by the hackathon rules.

| Category | Tool | How It Was Used |
|---|---|---|
| 🧠 **Production AI** | Google Gemini 2.5 (via LiteLLM) | Powers the in-app Daily Brief, Daily Actions, and scenario explanations |
| 🛠️ **Development** | Google Gemini (Web), Antigravity | Project orchestration, UI design, terminal automation, code review |
| 💻 **Coding** | GitHub Copilot, OpenAI Codex | Code generation, boilerplate, debugging across React/FastAPI |
| 🔍 **Research** | Perplexity AI, ChatGPT (GPT-4o) | Competitor analysis, SDG alignment, Malaysia food waste statistics |
| 🎨 **Assets** | NotebookLM (summaries), image generation tools | Pitch deck infographics, tech stack visuals |
| 📋 **Collaboration** | Notion AI | Team documentation and meeting notes |

> ⚠️ **Note:** Google Gemini is also embedded in the application backend as the AI inference provider via LiteLLM. Its use is both a development tool AND a core product component.

---

## 📚 Reference Docs

- 📋 [Product Requirements (PRD)](./docs/prd.md)
- 🏗️ [Architecture Notes](./docs/architecture.md)
- 📖 [Documentation](./docs/documentation.md)
- 👥 [Team Plan](./TEAM_PLAN.md)
- 📄 [Project Report](./docs/Predictory_Report.md)
- 🔌 [API Contracts](./apps/api/CONTRACTS.md)
- 🤖 [Copilot Examples](./apps/api/copilot/EXAMPLES.md)
- 🌱 [Seed Script](./apps/api/db/seed.py)

---

<p align="center">Made with ☕ and 🤖 by Team <strong>CHAT GPT</strong> · Hackathon 2026</p>
