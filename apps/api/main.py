from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(levelname)s:%(name)s:%(message)s",
)
for logger_name in ("copilot", "copilot.llm", "copilot.council"):
    logging.getLogger(logger_name).setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

from db.database import engine, Base, SessionLocal
from catalog.router import router as catalog_router
from ingestion.router import router as ingestion_router
from ops_data.router import router as ops_data_router
from forecasting.router import router as forecasting_router
from planning.router import router as planning_router
from alerts.router import router as alerts_router
from copilot.router import router as copilot_router
from copilot.council.router import router as council_router
from admin.router import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev convenience)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Predictory API",
    description="AI prep and replenishment copilot for bakery-cafe chains",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS ────────────────────────────────────────────────────────────────────
allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "*")
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]
environment = os.getenv("ENVIRONMENT", "development").lower()
if environment == "production" and ("*" in allowed_origins or not allowed_origins_raw.strip()):
    raise RuntimeError("Production requires explicit ALLOWED_ORIGINS; wildcard CORS is not allowed.")

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
app.include_router(council_router,     prefix="/api/v1", tags=["copilot"])
app.include_router(admin_router,       prefix="/api/v1", tags=["admin"])
