from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import InventorySnapshot, Outlet, RecipeBOM, SKU, SalesFact, WeatherSnapshot
from services.lightgbm_inference import DAYPARTS
from services.model_loader import ModelArtifactError, get_model_artifacts


@dataclass
class ReadinessStatus:
    ready: bool
    target_date: date
    blockers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "target_date": self.target_date.isoformat(),
            "blockers": self.blockers,
        }


class ReadinessError(RuntimeError):
    def __init__(self, blockers: list[str]):
        self.blockers = blockers
        super().__init__("; ".join(blockers))


def check_runtime_readiness(target_date: date, db: Session) -> ReadinessStatus:
    blockers: list[str] = []

    try:
        get_model_artifacts().validate_for_inference()
    except ModelArtifactError as exc:
        blockers.append(str(exc))

    outlets = db.query(Outlet).filter(Outlet.is_active == True).all()
    skus = db.query(SKU).filter(SKU.is_active == True).all()
    if not outlets:
        blockers.append("No active outlets are available. Import outlets before running forecasts.")
    if not skus:
        blockers.append("No active SKUs are available. Import products before running forecasts.")

    sales_count = (
        db.query(func.count(SalesFact.id))
        .filter(SalesFact.sale_date < target_date)
        .scalar()
        or 0
    )
    if sales_count <= 0:
        blockers.append("No historical sales exist before the target date.")

    inventory_count = (
        db.query(func.count(InventorySnapshot.id))
        .filter(InventorySnapshot.snapshot_date < target_date)
        .scalar()
        or 0
    )
    if inventory_count <= 0:
        blockers.append("No inventory snapshots exist before the target date.")

    bom_count = db.query(func.count(RecipeBOM.id)).scalar() or 0
    if bom_count <= 0:
        blockers.append("No recipe BOM rows exist. Import recipes before planning replenishment.")

    for outlet in outlets:
        has_weather = (
            db.query(WeatherSnapshot.id)
            .filter(WeatherSnapshot.outlet_id == outlet.id, WeatherSnapshot.target_date == target_date)
            .first()
            is not None
        )
        if not has_weather:
            blockers.append(f"No weather snapshot for outlet '{outlet.code}' on {target_date}.")
        for sku in skus:
            has_bom = db.query(RecipeBOM.id).filter(RecipeBOM.sku_id == sku.id).first() is not None
            if not has_bom:
                blockers.append(f"No recipe BOM rows exist for SKU '{sku.code}'.")
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
                    blockers.append(
                        f"No {daypart} sales history for outlet '{outlet.code}' and SKU '{sku.code}'."
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
                blockers.append(
                    f"No inventory history for outlet '{outlet.code}' and SKU '{sku.code}'."
                )

    return ReadinessStatus(ready=not blockers, target_date=target_date, blockers=blockers)


def require_runtime_readiness(target_date: date, db: Session) -> None:
    status = check_runtime_readiness(target_date, db)
    if not status.ready:
        raise ReadinessError(status.blockers)
