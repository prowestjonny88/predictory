from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from db.database import engine, Base, SessionLocal
from catalog.router import router as catalog_router
from ingestion.router import router as ingestion_router
from ops_data.router import router as ops_data_router
from forecasting.router import router as forecasting_router
from planning.router import router as planning_router
from alerts.router import router as alerts_router
from copilot.router import router as copilot_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev convenience)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="BakeWise API",
    description="AI prep and replenishment copilot for bakery-cafe chains",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
def health_check():
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"error: {exc}"

    return {
        "status": "ok",
        "db": db_status,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


# ─── Routers ─────────────────────────────────────────────────────────────────
app.include_router(catalog_router,     prefix="/api/v1", tags=["catalog"])
app.include_router(ingestion_router,   prefix="/api/v1", tags=["ingestion"])
app.include_router(ops_data_router,    prefix="/api/v1", tags=["ops_data"])
app.include_router(forecasting_router, prefix="/api/v1", tags=["forecasting"])
app.include_router(planning_router,    prefix="/api/v1", tags=["planning"])
app.include_router(alerts_router,      prefix="/api/v1", tags=["alerts"])
app.include_router(copilot_router,     prefix="/api/v1", tags=["copilot"])
