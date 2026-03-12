# Copilot API Examples

These examples are for frontend integration and local testing.

## Provider config

LiteLLM provider selection is environment-driven:

- Google AI Studio / Gemini API key
  - `GEMINI_API_KEY=...`
  - optional: `GEMINI_MODEL=gemini/gemini-2.5-flash`
- Vertex AI Gemini
  - `VERTEXAI_PROJECT=your-project`
  - `VERTEXAI_LOCATION=us-central1`
  - optional: `GEMINI_MODEL=vertex_ai/gemini-1.5-pro`
- Explicit override
  - `LITELLM_MODEL=...`

## `POST /api/v1/copilot/explain-plan`

Request:

```json
{
  "outlet_id": 1,
  "sku_id": 1,
  "plan_date": "2026-03-12",
  "context_type": "forecast"
}
```

Response:

```json
{
  "explanation": "Forecast for Butter Croissant at Roti Lane KLCC on 2026-03-12: total 94 units across the day, with the strongest pull in the morning. The projection is based on recent sales momentum plus the normal weekday pattern for this outlet and SKU.",
  "context_type": "forecast",
  "outlet_name": "Roti Lane KLCC",
  "sku_name": "Butter Croissant"
}
```

## `POST /api/v1/copilot/daily-brief`

Request:

```json
{
  "brief_date": "2026-03-12"
}
```

Response:

```json
{
  "brief": "Daily brief for 2026-03-12 (Thursday).\n\nTotal predicted sales are 1123 units, with waste risk at 48/100 and stockout risk at 40/100.\n\nTop actions: Reduce Butter Croissant at Roti Lane Bangsar; Stock up Butter Croissant at Roti Lane Mid Valley; Place 1 critical ingredient reorder(s).",
  "date": "2026-03-12"
}
```

## `POST /api/v1/copilot/run-scenario`

Request:

```json
{
  "scenario_text": "cut croissant prep at Bangsar by 15%",
  "target_date": "2026-03-12"
}
```

Response:

```json
{
  "scenario": "cut croissant prep at Bangsar by 15%",
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
  "recommendation": "Proceed with caution for Butter Croissant at Roti Lane Bangsar. Recommended reduction: 10% to balance waste and availability.",
  "interpretation": "Reducing prep for Butter Croissant at Roti Lane Bangsar by 15% could remove 1 waste alert(s) but may introduce about 0 additional stockout risk(s)."
}
```
