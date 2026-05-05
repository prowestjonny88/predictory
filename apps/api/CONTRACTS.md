# Backend Contracts

All backend routers are mounted under `/api/v1`.

Runtime values must come from imported business data, trained LightGBM artifacts, persisted forecast runs, optimizer output, or live LLM provider responses. Missing data returns `422`; missing model artifacts or provider/service outages return `503`.

## Imports

### `POST /api/v1/imports/upload`

Query params:

- `data_type=auto|outlets|products|ingredients|recipes|sales|inventory|waste|weather|holidays`
- `default_outlet_code` for transaction-style sales uploads
- `auto_create_skus=true|false` for transaction-style sales uploads

Response:

```json
{
  "rows_parsed": 2,
  "rows_committed": 2,
  "data_type": "products",
  "errors": []
}
```

Required references are strict. Import outlets, products, and ingredients before importing sales, inventory, waste, or recipe rows that reference them.

## Readiness

### `GET /api/v1/forecast-readiness`

Query params:

- `target_date=YYYY-MM-DD`

Response:

```json
{
  "ready": false,
  "target_date": "2026-05-06",
  "blockers": [
    "No historical sales exist before the target date."
  ]
}
```

The forecast and planning frontend pages should call this endpoint before requesting forecast generation.

## Forecasts

### `POST /api/v1/forecasts/run`

Query params:

- `target_date=YYYY-MM-DD`

Success:

```json
{
  "id": 1,
  "forecast_run_id": "fr_20260506_001",
  "forecast_date": "2026-05-06",
  "status": "completed",
  "engine_name": "lightgbm_mlops_prototype",
  "model_version": "lightgbm_p50_v1",
  "lines": []
}
```

Failure:

- `422` if readiness blockers exist.
- `503` if the model, encoded schema, metrics, or residual bands are unavailable.

### `GET /api/v1/forecast-runs/latest`

Query params:

- `forecast_date=YYYY-MM-DD`

Returns the latest persisted run for the date. The Forecast tab should render persisted lines only.

### `PATCH /api/v1/forecasts/{run_id}/lines/{line_id}`

Request:

```json
{
  "manual_adjustment_pct": 10,
  "user_id": "planner"
}
```

Response:

```json
{
  "id": 1,
  "outlet_id": 1,
  "sku_id": 1,
  "morning": 11.0,
  "midday": 8.8,
  "evening": 6.6,
  "total": 26.4,
  "method": "lightgbm_p50_v1",
  "confidence": 0.8153703703703704,
  "manual_adjustment_pct": 10,
  "rationale_json": {
    "engine_name": "lightgbm_mlops_prototype",
    "method": "lightgbm_p50_v1",
    "uncertainty": {
      "morning": { "p10": 8.0, "p50": 11.0, "p90": 15.0, "source": "sku_outlet_daypart" }
    }
  }
}
```

## Planning

### `GET /api/v1/api/daily-plan/{date}`

Returns a backend-generated daily plan. If no compatible forecast run exists, the backend attempts to build one through the readiness and LightGBM path.

Important response fields:

```json
{
  "date": "2026-05-06",
  "data_source": "backend",
  "engine_name": "lightgbm_mlops_prototype",
  "forecast_run_id": "fr_20260506_001",
  "top_actions": [
    {
      "id": 1,
      "outlet_id": 1,
      "sku_id": 1,
      "daypart": "morning",
      "p10": 8.0,
      "p50": 11.0,
      "p90": 15.0,
      "recommended_prep": 12,
      "financial_exposure": {
        "stockout_exposure_rm": 20.5,
        "waste_exposure_rm": 4.2
      },
      "replenishment": {}
    }
  ]
}
```

### `POST /api/v1/prep-plans/{plan_id}/edit`

Manager edits must be persisted by the backend. Frontend clients should not mutate local plan state after an API failure.

### `POST /api/v1/prep-plans/{plan_id}/approve`

Approval writes decision audit events and refreshes replenishment against the persisted plan.

### `GET /api/v1/replenishment/latest`

Query params:

- `date=YYYY-MM-DD`

Returns backend-generated replenishment lines only.

## Copilot

Copilot prose endpoints require the configured LLM provider when prose generation is requested.

### `POST /api/v1/copilot/explain-plan`

Returns `404` if the requested grounding data does not exist.

### `POST /api/v1/copilot/daily-brief`

Returns `503` when the LLM provider is unavailable.

### `POST /api/v1/copilot/daily-actions`

Response:

```json
{
  "date": "2026-05-06",
  "brief": "Three-paragraph action summary.",
  "top_actions": [],
  "prep_actions": [],
  "reorder_actions": [],
  "risk_warnings": [],
  "rebalance_suggestions": []
}
```

`source_type` values:

- `rules_based`
- `llm_rephrased`

## Manual Smoke Checklist

1. Start backend and verify `GET /health`.
2. Import outlet, product, ingredient, recipe, sales, inventory, waste, weather, and holiday CSVs.
3. Verify `GET /api/v1/forecast-readiness?target_date=YYYY-MM-DD` returns `ready: true`.
4. Trigger `POST /api/v1/forecasts/run`.
5. Confirm the run uses `engine_name = lightgbm_mlops_prototype`.
6. Fetch `GET /api/v1/api/daily-plan/{date}` and confirm p10/p50/p90 are present.
7. Edit and approve one prep line with an operator reason.
8. Fetch replenishment and verify it uses the same forecast run context.
9. With Gemini/LiteLLM credentials enabled, verify daily brief and daily actions.
10. With the provider disabled, verify Copilot prose endpoints return `503`.
