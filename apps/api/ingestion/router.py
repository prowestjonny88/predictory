"""
Ingestion router — Task 3
POST /imports/upload — in-memory CSV parse + direct DB commit
"""
import io
import csv
import re
from datetime import date, datetime
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

DAYPARTS = {"morning", "midday", "evening"}

DAYPART_ALIASES = {
    "morning": "morning",
    "am": "morning",
    "midday": "midday",
    "afternoon": "midday",
    "noon": "midday",
    "lunch": "midday",
    "evening": "evening",
    "night": "evening",
    "pm": "evening",
}

HEADER_ALIASES = {
    "item": "sku_name",
    "items": "sku_name",
    "product": "sku_name",
    "products": "sku_name",
    "productname": "sku_name",
    "transactionno": "transaction_no",
    "transactionid": "transaction_no",
    "quantity": "units_sold",
    "qty": "units_sold",
    "date": "sale_date",
    "datetime": "sale_datetime",
    "timestamp": "sale_datetime",
    "branch": "outlet_code",
    "store": "outlet_code",
    "storecode": "outlet_code",
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
            key = re.sub(r"[^a-z0-9]+", "", k.strip().lower())
            key = HEADER_ALIASES.get(key, k.strip().lower())
            normalized[key] = (v or "").strip()
        rows.append(normalized)
    return rows


def _detect_type(headers: set) -> str:
    if {"sale_date", "units_sold", "daypart"}.issubset(headers):
        return "sales"
    if {"sale_datetime", "sku_name", "daypart"}.issubset(headers):
        return "sales"
    if {"snapshot_date", "units_on_hand", "snapshot_time"}.issubset(headers):
        return "inventory"
    if {"sku_name", "category", "price"}.issubset(headers):
        return "products"
    return "unknown"


def _require_columns(data_type: str, headers: set[str]):
    if data_type == "sales":
        must_have = {"sale_date", "daypart", "units_sold"}
        missing = sorted(must_have - headers)
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing required columns for sales: {missing}",
            )
        if "sku_code" not in headers and "sku_name" not in headers:
            raise HTTPException(
                status_code=422,
                detail="Sales CSV must include either sku_code or sku_name/items column",
            )
        return

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


def _parse_date(value: str) -> date:
    value = value.strip()
    if not value:
        raise ValueError("sale_date is required")

    try:
        return date.fromisoformat(value)
    except ValueError:
        pass

    dt_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for fmt in dt_formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value).date()
    except ValueError as exc:
        raise ValueError(f"Invalid date/datetime value: {value}") from exc


def _normalize_sales_rows(rows: list[dict]) -> list[dict]:
    normalized_rows: list[dict] = []
    for row in rows:
        out = dict(row)

        if not out.get("sale_date") and out.get("sale_datetime"):
            out["sale_date"] = _parse_date(out["sale_datetime"]).isoformat()

        if not out.get("units_sold"):
            out["units_sold"] = "1"

        daypart_raw = (out.get("daypart") or "").strip().lower()
        mapped_daypart = DAYPART_ALIASES.get(daypart_raw, daypart_raw)
        out["daypart"] = mapped_daypart

        if mapped_daypart not in DAYPARTS:
            dt_val = out.get("sale_datetime", "").strip()
            if dt_val:
                try:
                    dt = datetime.fromisoformat(dt_val)
                    hour = dt.hour
                    if hour < 11:
                        out["daypart"] = "morning"
                    elif hour < 16:
                        out["daypart"] = "midday"
                    else:
                        out["daypart"] = "evening"
                except ValueError:
                    out["daypart"] = mapped_daypart
            else:
                out["daypart"] = mapped_daypart

        normalized_rows.append(out)

    return normalized_rows


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


def _import_sales(
    rows: list[dict],
    db: Session,
    default_outlet_code: str | None = None,
    auto_create_skus: bool = False,
) -> tuple[int, list[str]]:
    outlets = {o.code: o.id for o in db.query(Outlet).all()}
    all_skus = db.query(SKU).all()
    skus = {s.code: s.id for s in all_skus}
    sku_names = {s.name.lower(): s.id for s in all_skus}
    sku_prices = {s.id: s.price for s in all_skus}
    committed = 0
    errors = []
    sales_cache: dict[tuple[int, int, date, str], SalesFact] = {}
    seen_upload_keys: set[tuple[int, int, date, str]] = set()

    default_outlet_id = None
    if default_outlet_code:
        default_outlet_id = outlets.get(default_outlet_code.strip())
        if not default_outlet_id:
            raise HTTPException(
                status_code=422,
                detail=f"default_outlet_code '{default_outlet_code}' was not found",
            )
    elif len(outlets) == 1:
        default_outlet_id = next(iter(outlets.values()))

    for i, row in enumerate(rows):
        try:
            outlet_code = row.get("outlet_code", "").strip()
            outlet_id = outlets.get(outlet_code) if outlet_code else default_outlet_id

            sku_code = row.get("sku_code", "").strip()
            raw_sku_name = row.get("sku_name", "").strip()
            sku_name = raw_sku_name.lower()
            sku_id = skus.get(sku_code) if sku_code else sku_names.get(sku_name)

            if not sku_id and auto_create_skus and raw_sku_name:
                new_code = _next_available_code(raw_sku_name, set(skus.keys()))
                new_sku = SKU(
                    code=new_code,
                    name=raw_sku_name,
                    category="Imported",
                    price=0.0,
                    freshness_hours=8,
                    safety_buffer_pct=0.10,
                    is_bestseller=False,
                    is_active=True,
                )
                db.add(new_sku)
                db.flush()
                sku_id = new_sku.id
                skus[new_code] = sku_id
                sku_names[sku_name] = sku_id
                sku_prices[sku_id] = new_sku.price

            if not outlet_id or not sku_id:
                errors.append(
                    f"Row {i+2}: unknown outlet_code or sku_code/sku_name "
                    f"(got outlet_code='{outlet_code}', sku_code='{sku_code}', sku_name='{row.get('sku_name', '').strip()}')"
                )
                continue

            daypart = DAYPART_ALIASES.get(row.get("daypart", "").strip().lower(), row.get("daypart", "").strip().lower())
            if daypart not in DAYPARTS:
                errors.append(f"Row {i+2}: invalid daypart '{daypart}'")
                continue

            units_sold = int(float(row.get("units_sold", "0")))
            if units_sold < 0:
                errors.append(f"Row {i+2}: units_sold must be >= 0")
                continue

            revenue_raw = row.get("revenue", "").strip()
            if revenue_raw == "":
                sku_price = sku_prices.get(sku_id, 0.0)
                revenue = round(units_sold * sku_price, 2)
            else:
                revenue = float(revenue_raw)

            sale_date = _parse_date(row["sale_date"])
            key = (outlet_id, sku_id, sale_date, daypart)

            sf = sales_cache.get(key)
            if sf is None:
                sf = (
                    db.query(SalesFact)
                    .filter(
                        SalesFact.outlet_id == outlet_id,
                        SalesFact.sku_id == sku_id,
                        SalesFact.sale_date == sale_date,
                        SalesFact.daypart == daypart,
                    )
                    .first()
                )
                if sf is None:
                    sf = SalesFact(
                        outlet_id=outlet_id,
                        sku_id=sku_id,
                        sale_date=sale_date,
                        daypart=daypart,
                        units_sold=0,
                        revenue=0.0,
                    )
                    db.add(sf)
                sales_cache[key] = sf

            if key in seen_upload_keys:
                sf.units_sold += units_sold
                sf.revenue = round(sf.revenue + revenue, 2)
            else:
                sf.units_sold = units_sold
                sf.revenue = revenue
                seen_upload_keys.add(key)
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
    default_outlet_code: str | None = None,
    auto_create_skus: bool = False,
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

    if data_type in {"auto", "sales"}:
        rows = _normalize_sales_rows(rows)

    headers = set(rows[0].keys())

    detected = data_type if data_type in SUPPORTED_TYPES else _detect_type(headers)
    if detected == "unknown":
        raise HTTPException(
            status_code=422,
            detail=f"Cannot detect data type. Expected columns for sales/inventory/products. Got: {list(headers)[:8]}",
        )

    _require_columns(detected, headers)

    if detected == "sales":
        committed, errors = _import_sales(
            rows,
            db,
            default_outlet_code=default_outlet_code,
            auto_create_skus=auto_create_skus,
        )
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
