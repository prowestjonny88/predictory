import os
from datetime import date as date_type, timedelta

import httpx
from sqlalchemy.orm import Session

from db.models import Outlet, WeatherSnapshot

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _weather_enabled() -> bool:
    return os.getenv("WEATHER_FETCH_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def _weather_timeout_seconds() -> float:
    try:
        return float(os.getenv("WEATHER_TIMEOUT_SECONDS", "2"))
    except ValueError:
        return 2.0


def _weather_adjustment_pct(rain_mm: float | None, temp_max_c: float | None) -> float:
    rain = rain_mm or 0.0
    temp = temp_max_c or 0.0
    if rain >= 10:
        return -5.0
    if rain >= 2:
        return -2.0
    if temp >= 35:
        return -1.0
    return 0.0


def _weather_label(rain_mm: float | None, temp_max_c: float | None) -> str:
    rain = rain_mm or 0.0
    temp = temp_max_c or 0.0
    if rain >= 10:
        return "Heavy rain"
    if rain >= 2:
        return "Light rain"
    if temp >= 35:
        return "Hot and dry"
    return "Stable weather"


def _build_or_update_snapshot(
    snapshot: WeatherSnapshot | None,
    *,
    outlet_id: int,
    target_date: date_type,
    summary: str,
    rain_mm: float | None,
    temp_max_c: float | None,
    adjustment_pct: float,
    status: str,
    source: str,
    raw_json: dict | None,
    db: Session,
) -> WeatherSnapshot:
    if snapshot is None:
        snapshot = WeatherSnapshot(
            outlet_id=outlet_id,
            target_date=target_date,
            summary=summary,
            rain_mm=rain_mm,
            temp_max_c=temp_max_c,
            adjustment_pct=adjustment_pct,
            status=status,
            source=source,
            raw_json=raw_json,
        )
        db.add(snapshot)
    else:
        snapshot.summary = summary
        snapshot.rain_mm = rain_mm
        snapshot.temp_max_c = temp_max_c
        snapshot.adjustment_pct = adjustment_pct
        snapshot.status = status
        snapshot.source = source
        snapshot.raw_json = raw_json
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _fetch_open_meteo(outlet: Outlet, target_date: date_type) -> dict:
    response = httpx.get(
        OPEN_METEO_URL,
        params={
            "latitude": outlet.latitude,
            "longitude": outlet.longitude,
            "daily": "weather_code,temperature_2m_max,precipitation_sum",
            "timezone": "Asia/Kuala_Lumpur",
            "start_date": target_date.isoformat(),
            "end_date": target_date.isoformat(),
        },
        timeout=_weather_timeout_seconds(),
    )
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily") or {}
    rain_mm = (daily.get("precipitation_sum") or [None])[0]
    temp_max_c = (daily.get("temperature_2m_max") or [None])[0]
    return {
        "summary": _weather_label(rain_mm, temp_max_c),
        "rain_mm": rain_mm,
        "temp_max_c": temp_max_c,
        "adjustment_pct": _weather_adjustment_pct(rain_mm, temp_max_c),
        "status": "applied" if _weather_adjustment_pct(rain_mm, temp_max_c) != 0 else "neutral",
        "source": "live",
        "raw_json": payload,
    }


def get_or_refresh_weather_snapshot(outlet: Outlet, target_date: date_type, db: Session) -> WeatherSnapshot:
    snapshot = (
        db.query(WeatherSnapshot)
        .filter(
            WeatherSnapshot.outlet_id == outlet.id,
            WeatherSnapshot.target_date == target_date,
        )
        .first()
    )

    if snapshot and snapshot.source == "live":
        return snapshot

    if outlet.latitude is None or outlet.longitude is None:
        return _build_or_update_snapshot(
            snapshot,
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Weather unavailable",
            rain_mm=None,
            temp_max_c=None,
            adjustment_pct=0.0,
            status="unavailable",
            source="fallback",
            raw_json={"reason": "Missing outlet coordinates"},
            db=db,
        )

    today = date_type.today()
    if target_date < today or target_date > today + timedelta(days=14):
        return _build_or_update_snapshot(
            snapshot,
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Weather unavailable",
            rain_mm=None,
            temp_max_c=None,
            adjustment_pct=0.0,
            status="unavailable",
            source="fallback",
            raw_json={"reason": "Target date outside Open-Meteo forecast window"},
            db=db,
        )

    if not _weather_enabled():
        return _build_or_update_snapshot(
            snapshot,
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Weather fetch disabled",
            rain_mm=None,
            temp_max_c=None,
            adjustment_pct=0.0,
            status="unavailable",
            source="fallback",
            raw_json={"reason": "WEATHER_FETCH_ENABLED is false"},
            db=db,
        )

    try:
        weather = _fetch_open_meteo(outlet, target_date)
        return _build_or_update_snapshot(
            snapshot,
            outlet_id=outlet.id,
            target_date=target_date,
            summary=weather["summary"],
            rain_mm=weather["rain_mm"],
            temp_max_c=weather["temp_max_c"],
            adjustment_pct=weather["adjustment_pct"],
            status=weather["status"],
            source=weather["source"],
            raw_json=weather["raw_json"],
            db=db,
        )
    except Exception as exc:
        return _build_or_update_snapshot(
            snapshot,
            outlet_id=outlet.id,
            target_date=target_date,
            summary="Weather unavailable",
            rain_mm=None,
            temp_max_c=None,
            adjustment_pct=0.0,
            status="unavailable",
            source="fallback",
            raw_json={"reason": str(exc)},
            db=db,
        )
