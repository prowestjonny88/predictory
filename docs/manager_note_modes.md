# Manager Note Modes

Manager Note lets an operator add local context in natural language. The current runtime is Gemini-only for parsing and fail-closed when the provider is unavailable or returns invalid output.

## Current Mode: `prep_edit_only`

Current flow:

```text
manager note
-> Gemini parses outlet / daypart / SKU category / adjustment
-> backend validates parsed values against the forecast context
-> user reviews and confirms
-> matching prep lines are edited
-> replenishment refreshes
-> audit events are recorded
```

This mode does not rerun LightGBM and does not create a forecast override. The UI must state that the forecast will not be rerun.

The apply response includes business-readable line changes:

```json
{
  "line_id": 123,
  "outlet_name": "KLCC Mall",
  "sku_name": "Butter Croissant",
  "daypart": "morning",
  "before_prep": 35,
  "after_prep": 39
}
```

## Future Mode: `forecast_override_recompute`

The future mode would be:

```text
manager note
-> validated forecast override
-> LightGBM forecast run with override context
-> optimizer rerun
-> replenishment refresh
-> audit events
```

This future mode is only a roadmap design. It must not be described as active behavior until implemented end to end.

## Source Policy

- `parse_source: "llm_validated"` means Gemini parsed the note and backend validation accepted it.
- No rules-based manager-note fallback is active.
- Provider failure returns `503`.
- Invalid or unknown outlet/daypart/category returns `422`.
- User confirmation is always required before mutation.
