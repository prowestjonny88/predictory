# Copilot API Examples

These examples are for frontend integration and local testing.

Supported optional copilot languages:
- `en`
- `ms`
- `zh-CN`

If `language` is omitted, the backend defaults to `en`.

## Provider config

Copilot uses Gemini through LiteLLM:

- `GEMINI_API_KEY=...`
- optional: `GEMINI_MODEL=gemini/gemini-2.5-flash`

If `GEMINI_API_KEY` is missing or the provider call fails, endpoints return deterministic fallback text rather than invented numbers.

## `POST /api/v1/copilot/explain-plan`

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
  "explanation": "Forecast for Butter Croissant at Roti Lane Cheras Community Hub on 2026-03-12: total 94 units across the day, with the strongest pull in the morning. The projection is based on recent sales momentum plus the normal weekday pattern for this outlet and SKU.",
  "context_type": "forecast",
  "outlet_name": "Roti Lane Cheras Community Hub",
  "sku_name": "Butter Croissant"
}
```

## `POST /api/v1/copilot/daily-brief`

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
  "brief": "Daily brief for 2026-03-12 (Thursday).\n\nTotal predicted sales are 1123 units, with waste risk at 48/100 and stockout risk at 40/100.\n\nTop actions: Reduce Butter Croissant at Roti Lane Setapak Town Center; Stock up Butter Croissant at Roti Lane Kajang Town; Place 1 critical ingredient reorder(s).",
  "date": "2026-03-12"
}
```

## `POST /api/v1/copilot/run-scenario`

Request:

```json
{
  "scenario_text": "cut croissant prep at Setapak Town Center by 15%",
  "target_date": "2026-03-12",
  "language": "en"
}
```

## `POST /api/v1/copilot/daily-actions`

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
  "brief": "Operations are broadly ready for service, but Setapak Town Center waste risk and Kajang Town stock coverage need attention.\n\nMain risks are concentrated around Butter Croissant waste at Roti Lane Setapak Town Center, morning stockout exposure at Roti Lane Kajang Town, and one critical ingredient reorder.\n\nTop actions: Reduce Butter Croissant prep at Roti Lane Setapak Town Center by 10%; Increase Butter Croissant morning coverage at Roti Lane Kajang Town by 10%; Reorder Butter now (critical urgency).",
  "fallback_mode": false,
  "top_actions": [
    {
      "action_type": "prep",
      "action_text": "Reduce Butter Croissant prep at Roti Lane Setapak Town Center by 10%",
      "urgency": "high",
      "estimated_impact": "Reduce waste pressure; recent 3-day waste rate is 15.3%.",
      "target": {
        "outlet_id": 2,
        "outlet_name": "Roti Lane Setapak Town Center",
        "sku_id": 1,
        "sku_name": "Butter Croissant",
        "ingredient_id": null,
        "ingredient_name": null
      },
      "evidence": [
        "3-day waste rate 15.3%",
        "Affected dayparts: evening"
      ],
      "source_type": "llm_rephrased"
    }
  ],
  "prep_actions": [],
  "reorder_actions": [],
  "risk_warnings": [],
  "rebalance_suggestions": []
}
```

Response:

```json
{
  "scenario": "cut croissant prep at Setapak Town Center by 15%",
  "baseline": {
    "waste_alerts": 6,
    "stockout_alerts": 5
  },
  "modified": {
    "waste_alerts": 5,
    "stockout_alerts": 5
  },
  "delta": {
    "waste_change": -1,
    "stockout_change": 0
  },
  "recommendation": "Proceed with caution for Butter Croissant at Roti Lane Setapak Town Center. Recommended reduction: 10% to balance waste and availability.",
  "interpretation": "Reducing prep for Butter Croissant at Roti Lane Setapak Town Center by 15% could remove 1 waste alert(s) but may introduce about 0 additional stockout risk(s)."
}
```
