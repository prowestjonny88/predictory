# BakeWise

AI prep and replenishment copilot for bakery-cafe chains. Helps operators decide what to prep tomorrow, how much to replenish, and where waste will happen — before it happens.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, TanStack Query |
| Backend | FastAPI, SQLAlchemy, Alembic |
| AI | LiteLLM, LangGraph |
| Database | PostgreSQL |

---

## Project structure

```
apps/
  api/        FastAPI backend
  web/        Next.js frontend
```

---

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL running locally (or update the connection string)

---

## Run the backend (FastAPI)

```bash
cd apps/api

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy and edit)
cp .env.example .env            # or create .env manually

# Run database migrations
alembic upgrade head

# Seed demo data (optional)
python -m db.seed

# Start the API server
uvicorn main:app --reload --port 8000
```

API will be available at **http://localhost:8000**  
Interactive docs at **http://localhost:8000/docs**

---

## Run the frontend (Next.js)

```bash
cd apps/web

# Install dependencies
npm install

# Set the API URL (defaults to http://localhost:8000 if not set)
# Create a .env.local file:
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start the dev server
npm run dev
```

Frontend will be available at **http://localhost:3000**

---

## Build for production

```bash
cd apps/web
npm run build
npm start
```

---

## Export as static HTML

To generate plain HTML/CSS/JS files you can deploy to any static host:

```bash
cd apps/web

# Add output: "export" to next.config.mjs first, then:
npm run build
```

Output files will be in `apps/web/out/`. Upload that folder to Netlify, Vercel, S3, GitHub Pages, etc.

> Make sure `NEXT_PUBLIC_API_URL` points to your deployed FastAPI backend before building.

---

## Pages

| Route | Description |
|---|---|
| `/dashboard` | Executive overview — KPIs, top actions, waste & stockout alerts |
| `/forecast` | Outlet/daypart demand forecast with daypart summary cards |
| `/prep-plan` | Recommended prep quantities with manual override and approval |
| `/replenishment` | Ingredient reorder plan with urgency levels |
| `/risk-center` | Waste and stockout alert centre sorted by risk level |
| `/copilot` | AI daily brief generator and what-if scenario runner |