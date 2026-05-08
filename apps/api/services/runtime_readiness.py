from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import InventorySnapshot, Outlet, RecipeBOM, SKU, SalesFact, WeatherSnapshot
from forecasting.weather import WeatherUnavailableError, get_or_refresh_weather_snapshot
from services.lightgbm_inference import DAYPARTS
from services.model_loader import ModelArtifactError, get_model_artifacts


@dataclass
class ReadinessStatus:
    ready: bool
    target_date: date
    blockers: list[str] = field(default_factory=list)
    grouped_blockers: dict[str, list[str]] = field(default_factory=dict)
    artifact_files_found: bool = False
    artifact_validated_for_inference: bool = False
    artifact_validation_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "target_date": self.target_date.isoformat(),
            "blockers": self.blockers,
            "grouped_blockers": self.grouped_blockers,
            "artifact_files_found": self.artifact_files_found,
            "artifact_validated_for_inference": self.artifact_validated_for_inference,
            "artifact_validation_error": self.artifact_validation_error,
        }


class ReadinessError(RuntimeError):
    def __init__(self, blockers: list[str]):
        self.blockers = blockers
        super().__init__("; ".join(blockers))


def check_runtime_readiness(target_date: date, db: Session) -> ReadinessStatus:
    blockers: list[str] = []
    grouped_blockers: dict[str, list[str]] = {
        "model_artifacts": [],
        "master_data": [],
        "sales_coverage": [],
        "inventory_coverage": [],
        "bom_coverage": [],
        "weather_coverage": [],
    }

    def add_blocker(group: str, message: str) -> None:
        blockers.append(message)
        grouped_blockers.setdefault(group, []).append(message)

    artifacts = get_model_artifacts()
    artifact_files_found = artifacts.is_loaded()
    artifact_validated = False
    artifact_error = None
    try:
        artifacts.validate_for_inference()
        artifact_validated = True
    except ModelArtifactError as exc:
        artifact_error = str(exc)
        add_blocker("model_artifacts", artifact_error)

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()
    if not outlets:
        add_blocker("master_data", "No active outlets are available. Import outlets before running forecasts.")
    if not skus:
        add_blocker("master_data", "No active SKUs are available. Import products before running forecasts.")

    sales_count = (
        db.query(func.count(SalesFact.id))
        .filter(SalesFact.sale_date < target_date)
        .scalar()
        or 0
    )
    if sales_count <= 0:
        add_blocker("sales_coverage", "No historical sales exist before the target date.")

    inventory_count = (
        db.query(func.count(InventorySnapshot.id))
        .filter(InventorySnapshot.snapshot_date < target_date)
        .scalar()
        or 0
    )
    if inventory_count <= 0:
        add_blocker("inventory_coverage", "No inventory snapshots exist before the target date.")

    bom_count = db.query(func.count(RecipeBOM.id)).scalar() or 0
    if bom_count <= 0:
        add_blocker("bom_coverage", "No recipe BOM rows exist. Import recipes before planning replenishment.")

    for outlet in outlets:
        has_weather = (
            db.query(WeatherSnapshot.id)
            .filter(WeatherSnapshot.outlet_id == outlet.id, WeatherSnapshot.target_date == target_date)
            .first()
            is not None
        )
        if not has_weather:
            try:
                get_or_refresh_weather_snapshot(outlet, target_date, db)
                has_weather = True
            except WeatherUnavailableError as exc:
                add_blocker(
                    "weather_coverage",
                    f"No weather snapshot for outlet '{outlet.code}' on {target_date}. {exc}",
                )
        for sku in skus:
            has_bom = db.query(RecipeBOM.id).filter(RecipeBOM.sku_id == sku.id).first() is not None
            if not has_bom:
                add_blocker("bom_coverage", f"No recipe BOM rows exist for SKU '{sku.code}'.")
            for daypart in DAYPARTS:
                has_sales = (
                    db.query(SalesFact.id)
                    .filter(
                        SalesFact.outlet_id == outlet.id,
                        SalesFact.sku_id == sku.id,
                        SalesFact.daypart == daypart,
                        SalesFact.sale_date < target_date,
                    )
                    .first()
                    is not None
                )
                if not has_sales:
                    add_blocker(
                        "sales_coverage",
                        f"No {daypart} sales history for outlet '{outlet.code}' and SKU '{sku.code}'.",
                    )
            has_inventory = (
                db.query(InventorySnapshot.id)
                .filter(
                    InventorySnapshot.outlet_id == outlet.id,
                    InventorySnapshot.sku_id == sku.id,
                    InventorySnapshot.snapshot_date < target_date,
                )
                .first()
                is not None
            )
            if not has_inventory:
                add_blocker(
                    "inventory_coverage",
                    f"No inventory history for outlet '{outlet.code}' and SKU '{sku.code}'.",
                )

    grouped_blockers = {key: value for key, value in grouped_blockers.items() if value}
    return ReadinessStatus(
        ready=not blockers,
        target_date=target_date,
        blockers=blockers,
        grouped_blockers=grouped_blockers,
        artifact_files_found=artifact_files_found,
        artifact_validated_for_inference=artifact_validated,
        artifact_validation_error=artifact_error,
    )


def require_runtime_readiness(target_date: date, db: Session) -> None:
    status = check_runtime_readiness(target_date, db)
    if not status.ready:
        raise ReadinessError(status.blockers)
