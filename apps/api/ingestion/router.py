"""
Ingestion router — Task 3
POST /imports/upload — in-memory CSV parse + direct DB commit
"""
import io
import csv
import re
from datetime import date
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from db.models import SalesFact, InventorySnapshot, SKU, Outlet

router = APIRouter()

SUPPORTED_TYPES = ("sales", "inventory", "products")

REQUIRED_COLUMNS = {
    "sales": {"sale_date", "daypart", "units_sold", "outlet_code", "sku_code"},
    "inventory": {"snapshot_date", "snapshot_time", "units_on_hand", "outlet_code", "sku_code"},
    "products": {"sku_name", "category", "price"},
}


class UploadResult(BaseModel):
    rows_parsed: int
    rows_committed: int
    data_type: str
    errors: list[str]


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        normalized: dict[str, str] = {}
        for k, v in row.items():
            if not k:
                continue
            normalized[k.strip().lower()] = (v or "").strip()
        rows.append(normalized)
    return rows


def _detect_type(headers: set) -> str:
    if {"sale_date", "units_sold", "daypart"}.issubset(headers):
        return "sales"
    if {"snapshot_date", "units_on_hand", "snapshot_time"}.issubset(headers):
        return "inventory"
    if {"sku_name", "category", "price"}.issubset(headers):
        return "products"
    return "unknown"


def _require_columns(data_type: str, headers: set[str]):
    required = REQUIRED_COLUMNS[data_type]
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns for {data_type}: {missing}",
        )


def _to_bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    v = value.strip().lower()
    if v in {"true", "1", "yes", "y"}:
        return True
    if v in {"false", "0", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _to_float(value: str, default: float | None = None) -> float:
    if value == "" and default is not None:
        return default
    return float(value)


def _to_int(value: str, default: int | None = None) -> int:
    if value == "" and default is not None:
        return default
    return int(value)


def _slug_code(name: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9]+", "", name).upper()
    return clean[:12] or "SKU"


def _next_available_code(base_name: str, existing_codes: set[str]) -> str:
    base = f"SKU-{_slug_code(base_name)}"
    if base not in existing_codes:
        return base

    suffix = 2
    while True:
        candidate = f"{base}-{suffix}"
        if candidate not in existing_codes:
            return candidate
        suffix += 1


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


def _import_products(rows: list[dict], db: Session) -> tuple[int, list[str]]:
    existing_skus = db.query(SKU).all()
    by_code = {s.code: s for s in existing_skus}
    by_name = {s.name.lower(): s for s in existing_skus}
    committed = 0
    errors = []

    for i, row in enumerate(rows):
        try:
            name = row.get("sku_name", "") or row.get("name", "")
            category = row.get("category", "")
            price_raw = row.get("price", "")
            code = row.get("sku_code", "") or row.get("code", "")

            if not name or not category or price_raw == "":
                errors.append(
                    f"Row {i+2}: sku_name, category, and price are required"
                )
                continue

            price = _to_float(price_raw)
            if price < 0:
                errors.append(f"Row {i+2}: price must be >= 0")
                continue

            freshness_hours = _to_int(row.get("freshness_hours", ""), default=8)
            if freshness_hours <= 0:
                errors.append(f"Row {i+2}: freshness_hours must be > 0")
                continue

            safety_buffer_pct = _to_float(row.get("safety_buffer_pct", ""), default=0.10)
            # Accept either ratio form (0.10) or percent form (10)
            if safety_buffer_pct > 1:
                safety_buffer_pct = safety_buffer_pct / 100.0
            if safety_buffer_pct < 0:
                errors.append(f"Row {i+2}: safety_buffer_pct must be >= 0")
                continue

            is_bestseller = _to_bool(row.get("is_bestseller", ""), default=False)
            is_active = _to_bool(row.get("is_active", ""), default=True)

            if not code:
                code = _next_available_code(name, set(by_code.keys()))

            sku = by_code.get(code) or by_name.get(name.lower())
            if sku:
                # Protect uniqueness when retagging code via name-based match.
                if sku.code != code and code in by_code:
                    errors.append(f"Row {i+2}: sku_code '{code}' already exists")
                    continue
                old_code = sku.code
                sku.code = code
                sku.name = name
                sku.category = category
                sku.price = price
                sku.freshness_hours = freshness_hours
                sku.safety_buffer_pct = safety_buffer_pct
                sku.is_bestseller = is_bestseller
                sku.is_active = is_active
                if old_code != code:
                    by_code.pop(old_code, None)
                by_code[code] = sku
                by_name[name.lower()] = sku
            else:
                sku = SKU(
                    code=code,
                    name=name,
                    category=category,
                    price=price,
                    freshness_hours=freshness_hours,
                    safety_buffer_pct=safety_buffer_pct,
                    is_bestseller=is_bestseller,
                    is_active=is_active,
                )
                db.add(sku)
                db.flush()
                by_code[code] = sku
                by_name[name.lower()] = sku

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

    if data_type != "auto" and data_type not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"data_type must be one of {SUPPORTED_TYPES} or 'auto'",
        )

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

    _require_columns(detected, headers)

    if detected == "sales":
        committed, errors = _import_sales(rows, db)
    elif detected == "inventory":
        committed, errors = _import_inventory(rows, db)
    else:
        committed, errors = _import_products(rows, db)

    return UploadResult(
        rows_parsed=len(rows),
        rows_committed=committed,
        data_type=detected,
        errors=errors[:20],
    )
