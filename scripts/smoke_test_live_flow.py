#!/usr/bin/env python
"""Smoke-test Predictory against already imported live operational data."""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
SMOKE_TARGET_DATE = os.getenv("SMOKE_TARGET_DATE") or (date.today() + timedelta(days=1)).isoformat()
REQUIRE_LLM = os.getenv("SMOKE_REQUIRE_LLM") == "1"


class SmokeFailure(RuntimeError):
    pass


def _root_url() -> str:
    if API_BASE_URL.endswith("/api/v1"):
        return API_BASE_URL[: -len("/api/v1")]
    return API_BASE_URL.rsplit("/api/", 1)[0]


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, Any]:
    url = path if path.startswith("http") else f"{API_BASE_URL}{path}"
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=180) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw
        return exc.code, payload
    except URLError as exc:
        raise SmokeFailure(f"Could not reach {url}: {exc}") from exc


def _get(path: str, query: dict[str, Any] | None = None) -> Any:
    suffix = path if not query else f"{path}?{urlencode(query)}"
    status, payload = _request("GET", suffix)
    if status >= 400:
        raise SmokeFailure(f"GET {suffix} failed with {status}: {payload}")
    return payload


def _post(path: str, body: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> Any:
    suffix = path if not query else f"{path}?{urlencode(query)}"
    status, payload = _request("POST", suffix, body)
    if status >= 400:
        raise SmokeFailure(f"POST {suffix} failed with {status}: {payload}")
    return payload


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def main() -> int:
    checks: list[str] = []

    health = _request("GET", f"{_root_url()}/health")[1]
    _assert(isinstance(health, dict) and health.get("status") == "ok", f"Health check failed: {health}")
    checks.append("health")

    readiness = _get("/forecast-readiness", query={"target_date": SMOKE_TARGET_DATE})
    _assert(readiness.get("ready") is True, f"Readiness blockers remain: {readiness}")
    checks.append("readiness")

    generated = _post("/forecast-runs/generate", query={"target_date": SMOKE_TARGET_DATE})
    forecast_run_id = generated.get("forecast_run_id")
    _assert(bool(forecast_run_id), f"Forecast generation did not return a run id: {generated}")
    checks.append("LightGBM forecast generation")

    latest = _get("/forecast-runs/latest", query={"forecast_date": SMOKE_TARGET_DATE})
    _assert(latest.get("forecast_run_id") == forecast_run_id, f"Latest forecast mismatch: {latest}")
    _assert(latest.get("engine_name") == "lightgbm_mlops_prototype", f"Unexpected engine: {latest}")
    checks.append("latest forecast")

    lines = _get(f"/forecast-runs/{forecast_run_id}/lines")
    _assert(isinstance(lines, list) and lines, "Forecast lines are empty")
    first_line = lines[0]
    _assert(first_line.get("method") == "lightgbm_p50_v1", f"Unexpected forecast method: {first_line}")
    checks.append("forecast lines")

    daily_plan = _get("/api/daily-plan/latest", query={"date": SMOKE_TARGET_DATE})
    _assert(daily_plan.get("forecast_run_id") == forecast_run_id, f"Daily plan uses a different run: {daily_plan}")
    _assert(daily_plan.get("engine_name") == "lightgbm_mlops_prototype", f"Unexpected daily plan engine: {daily_plan}")
    actions = daily_plan.get("top_actions") or []
    _assert(actions, f"Daily plan top_actions missing: {daily_plan}")
    first_action = actions[0]
    _assert(first_action.get("p10") <= first_action.get("p50") <= first_action.get("p90"), f"Unordered uncertainty bands: {first_action}")
    _assert(first_action.get("financial_exposure"), f"Financial exposure missing: {first_action}")
    checks.append("daily planning")

    prep = _get("/prep-plans/latest", query={"date": SMOKE_TARGET_DATE})
    _assert(prep.get("id") and prep.get("lines"), f"Prep plan is missing lines: {prep}")
    checks.append("prep plan")

    replenishment = _get("/replenishment/latest", query={"date": SMOKE_TARGET_DATE})
    _assert(replenishment.get("lines"), f"Replenishment lines are empty: {replenishment}")
    checks.append("replenishment")

    parse = _post(
        "/copilot/parse-manager-note",
        body={
            "forecast_run_id": forecast_run_id,
            "note": "Increase morning Pastry prep at KLCC Mall by 10%",
        },
    )
    _assert((parse.get("parsed_adjustment") or {}).get("requires_confirmation") is True, f"Parse response invalid: {parse}")
    checks.append("manager note parsing")

    brief_status, brief_payload = _request(
        "POST",
        "/copilot/daily-brief",
        {"brief_date": SMOKE_TARGET_DATE},
    )
    if REQUIRE_LLM or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        _assert(brief_status == 200, f"Copilot daily brief failed with {brief_status}: {brief_payload}")
        checks.append("Copilot daily brief")
    else:
        _assert(brief_status == 503, f"Copilot should fail closed without provider config: {brief_payload}")
        checks.append("Copilot fail-closed")

    print(f"PASS Predictory live smoke flow for {SMOKE_TARGET_DATE}")
    for check in checks:
        print(f"[PASS] {check}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
