# LangGraph Daily Agent

The Daily Actions agent is a bounded LangGraph workflow for operations summaries. It does not calculate forecasts, prep quantities, cost exposure, or replenishment needs. Those values come from LightGBM, optimizer-backed prep planning, replenishment logic, and risk-alert services.

## Current Flow

```text
load_context
-> derive_candidate_actions
-> if candidate actions exist:
     rank_and_phrase_actions
   else:
     rules_brief_only
-> validate_and_finalize
-> END
```

`load_context` reads the latest forecast run, prep plan, replenishment plan, waste alerts, and stockout alerts for the target date.

`derive_candidate_actions` creates deterministic candidate actions from backend evidence.

`rank_and_phrase_actions` may ask Gemini to reorder and rephrase existing candidates. Gemini must preserve action IDs, entities, and numbers. If the response is unavailable or invalid, the graph returns rules-based actions.

`rules_brief_only` skips Gemini when there are no candidate actions.

`validate_and_finalize` drops actions with invalid outlet, SKU, or ingredient references and serializes the response.

## Response Status

Daily action responses include:

- `llm_status`: `not_needed`, `success`, or `failed`
- `used_fallback`: true when rules-based output replaced invalid or unavailable Gemini output
- `graph_trace`: debug-only node trace for engineering review

These fields are for debugging and evidence. They should not be presented as manager-facing AI capability claims.

## Future Human-In-The-Loop Design

A future graph can add an interrupt before mutation:

```text
derive actions
-> rank actions
-> if high risk, interrupt for manager approval
-> resume after confirmation
-> apply adjustment
-> refresh replenishment
-> write audit event
```

That interrupt flow is not implemented today. Current approvals and manager-note application remain outside the Daily Actions graph.
