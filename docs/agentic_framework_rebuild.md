# Predictory Agent Council v1

Predictory keeps numerical decisions grounded in deterministic backend tools:

- LightGBM calculates demand bands.
- The prep optimizer calculates prep and financial exposure.
- BOM and replenishment logic calculate ingredient need and shortage.
- Risk and audit services remain backend-owned.

The Agent Council sits around those tools. Tool-backed agents turn backend evidence into structured arguments, the Judge Agent selects from server-generated candidate prep quantities, and the manager confirms before any prep line is edited.

## Current v1 Flow

1. A manager opens Daily Planning.
2. They click `Agent Council` on one selected recommendation.
3. The backend loads the selected prep line and forecast evidence.
4. The backend generates candidate prep quantities: optimizer/current prep, expected demand, stockout guardrail, waste guardrail, and optional manager-note adjusted prep.
5. Specialist agents emit grounded arguments from backend evidence.
6. The Judge Agent may synthesize, but it must choose one server-generated candidate.
7. If the Judge response is invalid or unavailable, the backend falls back to the optimizer/current candidate and records that fallback in the trace.
8. Nothing mutates until the manager confirms.
9. Confirm applies `prep_edit_only`, refreshes replenishment, and writes a compact audit summary.

## Hard Rules

- LLMs do not forecast demand.
- LLMs do not calculate prep, stockout exposure, waste exposure, ingredient shortage, or reorder quantity.
- Review endpoints are read-only.
- Confirm recomputes candidates server-side and never trusts client-provided candidate lists.
- `forecast_override_recompute` is not implemented in v1.
- No Agent Council DB tables are added in v1; full trace is returned by API response, while audit stores a compact summary.

## Endpoints

- `POST /api/v1/copilot/council/review`
- `POST /api/v1/copilot/council/review-with-note`
- `POST /api/v1/copilot/council/confirm`

## Demo Note

Use a specific manager note after selecting a matching recommendation:

```text
Increase Pastry at KLCC Mall morning by 15% because a school group is visiting.
```

