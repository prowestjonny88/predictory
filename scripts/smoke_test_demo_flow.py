#!/usr/bin/env python
"""Smoke-test the final Predictory demo API flow.

The script assumes the FastAPI backend is already running and seeded.
It intentionally uses a future target date by default so repeated smoke
runs do not alter the main visible demo date unless SMOKE_TARGET_DATE is set.
"""

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
SMOKE_TARGET_DATE = os.getenv("SMOKE_TARGET_DATE") or (date.today() + timedelta(days=2)).isoformat()


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
    suffix = path
    if query:
        suffix = f"{path}?{urlencode(query)}"
    status, payload = _request("GET", suffix)
    if status >= 400:
        raise SmokeFailure(f"GET {suffix} failed with {status}: {payload}")
    return payload


def _post(path: str, body: dict[str, Any] | None = None, query: dict[str, Any] | None = None) -> Any:
    suffix = path
    if query:
        suffix = f"{path}?{urlencode(query)}"
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

    model = _get("/admin/models/latest")
    _assert(model.get("model_version") == "lightgbm_p50_v1", f"Unexpected model metadata: {model}")
    _assert(model.get("metrics", {}).get("wape") is not None, "Model WAPE is missing")
    checks.append("model metadata")

    generated = _post("/forecast-runs/generate", query={"target_date": SMOKE_TARGET_DATE})
    forecast_run_id = generated.get("forecast_run_id")
    _assert(bool(forecast_run_id), f"Forecast generation did not return a run id: {generated}")
    checks.append("forecast generation")

    latest = _get("/forecast-runs/latest", query={"forecast_date": SMOKE_TARGET_DATE})
    _assert(latest.get("forecast_run_id") == forecast_run_id, f"Latest forecast mismatch: {latest}")
    checks.append("latest forecast")

    lines = _get(f"/forecast-runs/{forecast_run_id}/lines")
    _assert(isinstance(lines, list) and len(lines) > 0, "Forecast lines are empty")
    checks.append("forecast lines")

    daily_plan = _get("/api/daily-plan/latest", query={"date": SMOKE_TARGET_DATE})
    _assert(daily_plan.get("forecast_run_id"), f"Daily plan is missing forecast_run_id: {daily_plan}")
    _assert(daily_plan.get("data_source") in {"backend", "demo_fallback"}, f"Daily plan source missing: {daily_plan}")
    actions = daily_plan.get("top_actions") or []
    _assert(actions, f"Daily plan top_actions missing: {daily_plan}")
    first_action = actions[0]
    _assert(first_action.get("p10") <= first_action.get("p50") <= first_action.get("p90"), f"Uncertainty bands unordered: {first_action}")
    _assert(first_action.get("recommended_prep") is not None, f"Recommended prep missing: {first_action}")
    _assert(first_action.get("financial_exposure"), f"Financial exposure missing: {first_action}")
    _assert(first_action.get("replenishment") is not None, f"Replenishment impact missing: {first_action}")
    checks.append("latest daily plan contract")

    prep = _get("/prep-plans/latest", query={"date": SMOKE_TARGET_DATE})
    prep_lines = prep.get("lines") or []
    _assert(prep.get("id") and prep_lines, f"Prep plan is missing lines: {prep}")
    checks.append("prep plan")

    first_line = prep_lines[0]
    final_units = int(first_line.get("final_units", first_line.get("recommended_units", 0)))
    edit = _post(
        f"/prep-plans/{prep['id']}/edit",
        body={
            "line_id": first_line["id"],
            "final_prep": final_units,
            "operator_reason": "Smoke test no-op audit check",
            "user_id": "smoke-test",
        },
    )
    _assert(edit.get("audit_event_ids"), f"Prep edit did not create audit event: {edit}")
    checks.append("decision audit")

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
    parsed = parse.get("parsed_adjustment") or {}
    _assert(parsed.get("requires_confirmation") is True, f"Manager note confirmation flag missing: {parse}")
    checks.append("manager note parse")

    print(f"PASS Predictory smoke flow for {SMOKE_TARGET_DATE}")
    for check in checks:
        print(f"[PASS] {check}")
    print("Final result: DEMO READY")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SmokeFailure as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        raise SystemExit(1)
