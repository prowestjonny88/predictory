# Copilot API Examples

These examples are for frontend integration and local testing.

Supported optional copilot languages:

- `en`
- `ms`
- `zh-CN`

If `language` is omitted, the backend defaults to `en`. Invalid language values use the English prompt.

## Provider Config

Copilot uses Gemini through LiteLLM:

- `GEMINI_API_KEY=...`
- optional: `GEMINI_MODEL=gemini/gemini-3-flash-preview`

If the provider is missing or unavailable, prose endpoints return `503`. Runtime endpoints do not substitute deterministic prose for provider failures.

## `POST /api/v1/copilot/explain-plan`

Request:

```json
{
  "outlet_id": 1,
  "sku_id": 1,
  "plan_date": "2026-05-06",
  "context_type": "forecast",
  "language": "ms"
}
```

Response:

```json
{
  "explanation": "LLM-generated explanation grounded in the persisted forecast run.",
  "context_type": "forecast",
  "outlet_name": "KLCC Mall",
  "sku_name": "Butter Croissant"
}
```

Missing grounding data returns `404`.

## `POST /api/v1/copilot/daily-brief`

Request:

```json
{
  "brief_date": "2026-05-06",
  "language": "zh-CN"
}
```

Response:

```json
{
  "brief": "Three-paragraph LLM summary grounded in the persisted forecast, alerts, and replenishment plan.",
  "date": "2026-05-06"
}
```

Provider unavailable:

```json
{
  "detail": "LLM provider unavailable: GEMINI_API_KEY is not configured"
}
```

## `POST /api/v1/copilot/run-scenario`

Request:

```json
{
  "scenario_text": "cut croissant prep at Bangsar Street by 15%",
  "target_date": "2026-05-06",
  "language": "en"
}
```

Response:

```json
{
  "scenario": "cut croissant prep at Bangsar Street by 15%",
  "baseline": {},
  "modified": {},
  "delta": {},
  "recommendation": "Rules-based advisory text.",
  "interpretation": "Rules-based scenario interpretation."
}
```

Scenario parsing is rules-based by design.

## `POST /api/v1/copilot/daily-actions`

Request:

```json
{
  "target_date": "2026-05-06",
  "top_n": 5,
  "language": "ms"
}
```

Response:

```json
{
  "date": "2026-05-06",
  "brief": "Operations are broadly ready for service.\n\nMain risks are grounded in backend alerts.\n\nAct on the ranked prep and reorder actions first.",
  "top_actions": [
    {
      "action_type": "prep",
      "action_text": "Reduce Butter Croissant prep at Bangsar Street by 10%",
      "urgency": "high",
      "estimated_impact": "Reduce waste pressure using backend alert evidence.",
      "target": {
        "outlet_id": 2,
        "outlet_name": "Bangsar Street",
        "sku_id": 4,
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

Valid `source_type` values are `rules_based` and `llm_rephrased`.
