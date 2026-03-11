"""
Ingestion router — Task 3
POST /imports/upload — in-memory CSV parse + direct DB commit
"""
import io
import csv
from datetime import date
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import SalesFact, InventorySnapshot, SKU, Outlet

router = APIRouter()

SUPPORTED_TYPES = ("sales", "inventory", "products")


class UploadResult(BaseModel):
    rows_parsed: int
    rows_committed: int
    data_type: str
    errors: list[str]


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _detect_type(headers: set) -> str:
    if {"sale_date", "units_sold", "daypart"}.issubset(headers):
        return "sales"
    if {"snapshot_date", "units_on_hand", "snapshot_time"}.issubset(headers):
        return "inventory"
    if {"sku_name", "category", "price"}.issubset(headers):
        return "products"
    return "unknown"


def _import_sales(rows: list[dict], db: Session) -> tuple[int, list[str]]:
    outlets = {o.code: o.id for o in db.query(Outlet).all()}
    skus = {s.code: s.id for s in db.query(SKU).all()}
    committed = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            outlet_id = outlets.get(row.get("outlet_code", "").strip())
            sku_id = skus.get(row.get("sku_code", "").strip())
            if not outlet_id or not sku_id:
                errors.append(f"Row {i+2}: unknown outlet_code or sku_code")
                continue
            sf = SalesFact(
                outlet_id=outlet_id,
                sku_id=sku_id,
                sale_date=date.fromisoformat(row["sale_date"].strip()),
                daypart=row["daypart"].strip().lower(),
                units_sold=int(row["units_sold"]),
                revenue=float(row.get("revenue", 0)),
            )
            db.merge(sf)
            committed += 1
        except Exception as exc:
            errors.append(f"Row {i+2}: {exc}")

    db.commit()
    return committed, errors


def _import_inventory(rows: list[dict], db: Session) -> tuple[int, list[str]]:
    outlets = {o.code: o.id for o in db.query(Outlet).all()}
    skus = {s.code: s.id for s in db.query(SKU).all()}
    committed = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            outlet_id = outlets.get(row.get("outlet_code", "").strip())
            sku_id = skus.get(row.get("sku_code", "").strip())
            if not outlet_id or not sku_id:
                errors.append(f"Row {i+2}: unknown outlet_code or sku_code")
                continue
            inv = InventorySnapshot(
                outlet_id=outlet_id,
                sku_id=sku_id,
                snapshot_date=date.fromisoformat(row["snapshot_date"].strip()),
                snapshot_time=row.get("snapshot_time", "eod").strip().lower(),
                units_on_hand=int(row["units_on_hand"]),
            )
            db.add(inv)
            committed += 1
        except Exception as exc:
            errors.append(f"Row {i+2}: {exc}")

    db.commit()
    return committed, errors


@router.post("/imports/upload", response_model=UploadResult)
async def upload_csv(
    file: UploadFile = File(...),
    data_type: str = "auto",
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are accepted")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    rows = _parse_csv(content)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    headers = set(rows[0].keys())

    detected = data_type if data_type in SUPPORTED_TYPES else _detect_type(headers)
    if detected == "unknown":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot detect data type. Expected columns for sales/inventory/products. Got: {list(headers)[:8]}",
        )

    if detected == "sales":
        committed, errors = _import_sales(rows, db)
    elif detected == "inventory":
        committed, errors = _import_inventory(rows, db)
    else:
        committed, errors = 0, ["Product import not yet implemented — use seed script"]

    return UploadResult(
        rows_parsed=len(rows),
        rows_committed=committed,
        data_type=detected,
        errors=errors[:20],
    )
