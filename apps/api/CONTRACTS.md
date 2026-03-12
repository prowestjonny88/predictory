# Backend Contracts

This document freezes the backend request and response contracts that frontend work should use.

Notes:
- All backend routers are mounted under `/api/v1`.
- The planning router currently exposes daily plan at `/api/v1/api/daily-plan/{date}`.
- Copilot `daily-actions` remains a separate endpoint from `daily-plan`.
- Copilot prose endpoints accept an optional `language` field: `en`, `ms`, or `zh-CN`.
- Business-data endpoints remain language-neutral. Only copilot-generated prose is localized by the backend.

## P2 Contracts

### `POST /api/v1/imports/upload`

Query params:
- `data_type=auto|sales|inventory|products|holidays`

Multipart form:
- `file`: CSV upload

Response:

```json
{
  "rows_parsed": 2,
  "rows_committed": 2,
  "data_type": "products",
  "errors": []
}
```

Holiday CSV columns:
- Required: `holiday_date`, `name`
- Optional: `country_code`, `region_code`, `holiday_type`, `demand_uplift_pct`, `is_active`

### `GET /api/v1/outlets`

Response:

```json
[
  {
    "id": 1,
    "name": "Roti Lane KLCC",
    "code": "RL-KLCC",
    "address": "Suria KLCC, Kuala Lumpur",
    "is_active": true
  }
]
```

### `GET /api/v1/skus`

Response:

```json
[
  {
    "id": 1,
    "name": "Butter Croissant",
    "code": "SKU-CRO",
    "category": "Pastry",
    "freshness_hours": 8,
    "is_bestseller": true,
    "safety_buffer_pct": 0.1,
    "price": 8.5,
    "is_active": true
  }
]
```

### `GET /api/v1/ingredients`

Response:

```json
[
  {
    "id": 1,
    "name": "Butter",
    "code": "ING-BUT",
    "unit": "kg",
    "stock_on_hand": 180.0,
    "reorder_point": 50.0,
    "supplier_lead_time_hours": 24,
    "cost_per_unit": 28.0
  }
]
```

### `GET /api/v1/recipes`

Response:

```json
[
  {
    "id": 1,
    "sku_id": 1,
    "sku_name": "Butter Croissant",
    "ingredient_id": 1,
    "ingredient_name": "Butter",
    "quantity_per_unit": 0.06,
    "unit": "kg"
  }
]
```

### `GET /api/v1/sales`

Query params:
- `outlet_id`
- `sku_id`
- `start_date`
- `end_date`
- `limit`
- `offset`

Response:

```json
[
  {
    "id": 1,
    "outlet_id": 1,
    "sku_id": 1,
    "sale_date": "2026-03-12",
    "daypart": "morning",
    "units_sold": 25,
    "revenue": 212.5
  }
]
```

### `GET /api/v1/inventory`

Query params:
- `outlet_id`

Response:

```json
[
  {
    "id": 1,
    "outlet_id": 1,
    "sku_id": 1,
    "sku_name": "Butter Croissant",
    "snapshot_date": "2026-03-12",
    "snapshot_time": "eod",
    "units_on_hand": 10
  }
]
```

### `GET /api/v1/wastelogs`

Query params:
- `outlet_id`
- `start_date`
- `end_date`

Response:

```json
[
  {
    "id": 1,
    "outlet_id": 1,
    "sku_id": 1,
    "waste_date": "2026-03-12",
    "daypart": "evening",
    "units_wasted": 5,
    "reason": "End-of-day overproduction"
  }
]
```

### `PATCH /api/v1/plans/prep/{plan_id}/lines/{line_id}`

Request:

```json
{
  "edited_units": 12,
  "user_id": "ops-user"
}
```

Response:

```json
{
  "id": 1,
  "plan_id": 1,
  "outlet_id": 1,
  "sku_id": 1,
  "daypart": "morning",
  "recommended_units": 10,
  "edited_units": 12,
  "current_stock": 2,
  "status": "edited"
}
```

### `POST /api/v1/plans/prep/{plan_id}/approve`

Request:

```json
{
  "approved_by": "ops-manager"
}
```

Response:

```json
{
  "id": 1,
  "plan_date": "2026-03-12",
  "status": "approved",
  "approved_by": "ops-manager",
  "lines": []
}
```

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
  "method": "weighted_blend",
  "confidence": 0.8,
  "manual_adjustment_pct": 10,
  "rationale_json": {}
}
```

## P3 Contracts

### `POST /api/v1/forecasts/run`

Query params:
- `target_date`

Response:

```json
{
  "id": 1,
  "forecast_date": "2026-03-12",
  "status": "completed",
  "lines": []
}
```

### `GET /api/v1/forecasts`

Query params:
- `forecast_date`
- `outlet_id`

Response:

```json
[
  {
    "id": 1,
    "forecast_date": "2026-03-12",
    "status": "completed",
    "lines": []
  }
]
```

Notes:
- `ForecastLine.rationale_json` now includes demand-driver context such as `holiday_signal`, `weather_signal`, `manual_overrides`, `stockout_censoring`, `context_adjustment_pct`, and `final_total_before_daypart_split`.

### `GET /api/v1/forecast-context`

Query params:
- `target_date`
- `outlet_id`
- `sku_id` optional

Response:

```json
{
  "target_date": "2026-03-12",
  "outlet_id": 1,
  "sku_id": 1,
  "holiday": {
    "label": "Demo Festival Day",
    "source": "seeded_demo",
    "status": "flagged",
    "adjustment_pct": 0,
    "details": ["Festival"]
  },
  "weather": {
    "label": "Weather unavailable",
    "source": "fallback",
    "status": "unavailable",
    "adjustment_pct": 0,
    "details": ["Weather unavailable"]
  },
  "stockout_censoring": {
    "enabled": true,
    "adjusted_history_days": 1,
    "adjusted_dates": ["2026-03-09"],
    "note": "Recovered likely lost sales from low end-of-day stock history."
  },
  "active_overrides": [],
  "combined_adjustment_pct": 0
}
```

### `GET /api/v1/forecast-overrides`

Query params:
- `target_date`
- `outlet_id`
- `sku_id` optional

Response:

```json
[
  {
    "id": 1,
    "target_date": "2026-03-12",
    "outlet_id": 1,
    "sku_id": 1,
    "sku_name": "Butter Croissant",
    "override_type": "promo",
    "title": "Morning IG promo",
    "notes": "Limited pastry push",
    "adjustment_pct": 12,
    "enabled": true,
    "created_by": "planner"
  }
]
```

### `POST /api/v1/forecast-overrides`

Request:

```json
{
  "target_date": "2026-03-12",
  "outlet_id": 1,
  "sku_id": 1,
  "override_type": "promo",
  "title": "Morning IG promo",
  "notes": "Limited pastry push",
  "adjustment_pct": 12,
  "enabled": true,
  "created_by": "planner"
}
```

Response:

```json
{
  "id": 1,
  "target_date": "2026-03-12",
  "outlet_id": 1,
  "sku_id": 1,
  "sku_name": "Butter Croissant",
  "override_type": "promo",
  "title": "Morning IG promo",
  "notes": "Limited pastry push",
  "adjustment_pct": 12,
  "enabled": true,
  "created_by": "planner"
}
```

### `PATCH /api/v1/forecast-overrides/{override_id}`

Request:

```json
{
  "adjustment_pct": 8,
  "enabled": false
}
```

### `DELETE /api/v1/forecast-overrides/{override_id}`

Response:
- `204 No Content`

### `GET /api/v1/api/daily-plan/{date}`

Response:

```json
{
  "date": "2026-03-12",
  "prep_plan_id": 1,
  "replenishment_plan_id": 1,
  "forecasts": [
    {
      "outlet_id": 1,
      "outlet_name": "Roti Lane KLCC",
      "sku_id": 1,
      "sku_name": "Butter Croissant",
      "morning": 25.0,
      "midday": 15.0,
      "evening": 8.0,
      "total": 48.0,
      "reason_tags": ["recent_sales", "weekday_pattern"]
    }
  ],
  "prep_plan": [
    {
      "id": 1,
      "outlet_id": 1,
      "sku_id": 1,
      "daypart": "morning",
      "recommended_units": 27,
      "edited_units": null,
      "current_stock": 3,
      "status": "pending"
    }
  ],
  "replenishment_plan": [
    {
      "ingredient_id": 1,
      "ingredient_name": "Butter",
      "need_qty": 22.4,
      "stock_on_hand": 10.0,
      "reorder_qty": 12.4,
      "urgency": "high",
      "driving_skus": ["Butter Croissant"]
    }
  ],
  "waste_alerts": [
    {
      "outlet_name": "Roti Lane Bangsar",
      "sku_name": "Butter Croissant",
      "daypart": "evening",
      "risk_level": "high",
      "reason": "Recent waste rate is elevated."
    }
  ],
  "stockout_alerts": [
    {
      "outlet_name": "Roti Lane Mid Valley",
      "sku_name": "Butter Croissant",
      "daypart": "morning",
      "risk_level": "high",
      "reason": "Morning stock is below expected demand."
    }
  ],
  "summary": {
    "total_predicted_sales": 480.0,
    "waste_risk_score": 20,
    "stockout_risk_score": 28,
    "top_actions": [
      "Reduce Butter Croissant prep at Roti Lane Bangsar (waste risk high)"
    ],
    "at_risk_outlets": ["Roti Lane Bangsar", "Roti Lane Mid Valley"]
  }
}
```

### `POST /api/v1/plans/prep/run`

Query params:
- `target_date`

Response:

```json
{
  "plan_id": 1,
  "plan_date": "2026-03-12",
  "status": "draft",
  "lines_count": 120
}
```

### `POST /api/v1/plans/replenishment/run`

Query params:
- `target_date`

Response:

```json
{
  "plan_id": 1,
  "plan_date": "2026-03-12",
  "status": "draft",
  "lines_count": 8
}
```

## P5 Contracts

Keep detailed copilot request and response examples in [copilot/EXAMPLES.md](./copilot/EXAMPLES.md).

### `POST /api/v1/copilot/explain-plan`

Request:

```json
{
  "outlet_id": 1,
  "sku_id": 1,
  "plan_date": "2026-03-12",
  "context_type": "forecast",
  "language": "ms"
}
```

Response:

```json
{
  "explanation": "Forecast for Butter Croissant at Roti Lane KLCC is driven by recent sales and weekday pattern.",
  "context_type": "forecast",
  "outlet_name": "Roti Lane KLCC",
  "sku_name": "Butter Croissant"
}
```

### `POST /api/v1/copilot/daily-brief`

Request:

```json
{
  "brief_date": "2026-03-12",
  "language": "zh-CN"
}
```

Response:

```json
{
  "brief": "Three-paragraph daily summary.",
  "date": "2026-03-12"
}
```

### `POST /api/v1/copilot/run-scenario`

Request:

```json
{
  "scenario_text": "cut croissant prep at Bangsar by 15%",
  "target_date": "2026-03-12",
  "language": "en"
}
```

Response:

```json
{
  "scenario": "cut croissant prep at Bangsar by 15%",
  "baseline": {},
  "modified": {},
  "delta": {},
  "recommendation": "Advisory recommendation text.",
  "interpretation": "Heuristic scenario interpretation."
}
```

### `POST /api/v1/copilot/daily-actions`

Request:

```json
{
  "target_date": "2026-03-12",
  "top_n": 5,
  "language": "ms"
}
```

Response:

```json
{
  "date": "2026-03-12",
  "brief": "Three-paragraph action summary.",
  "fallback_mode": false,
  "top_actions": [],
  "prep_actions": [],
  "reorder_actions": [],
  "risk_warnings": [],
  "rebalance_suggestions": []
}
```

## Manual Smoke Checklist

Run after backend changes are merged:

1. Start backend and verify `GET /health`.
2. Upload one products CSV through `POST /api/v1/imports/upload`.
3. Upload one sales CSV through `POST /api/v1/imports/upload`.
4. Trigger `POST /api/v1/forecasts/run`.
5. Fetch `GET /api/v1/api/daily-plan/{date}` for a fresh date.
6. Edit and approve one prep plan line through:
   - `PATCH /api/v1/plans/prep/{plan_id}/lines/{line_id}`
   - `POST /api/v1/plans/prep/{plan_id}/approve`
7. With provider disabled, verify `POST /api/v1/copilot/daily-brief` returns deterministic fallback text.
8. With valid Gemini/LiteLLM credentials enabled, verify:
   - `POST /api/v1/copilot/daily-brief`
   - `POST /api/v1/copilot/daily-actions`
9. For `daily-actions`, confirm `fallback_mode` is `false` during the live-provider smoke.
