"""
LLM prompt templates — Task 18
All prompts receive deterministic data; the LLM adds plain-language explanation only.
"""

FORECAST_EXPLANATION_PROMPT = """\
You are BakeWise, an AI copilot for bakery operations. Given the forecast data below, write a clear 2-sentence explanation for the operations team.

Outlet: {outlet_name}
SKU: {sku_name}
Date: {date} ({weekday})
Forecast: Morning={morning}, Midday={midday}, Evening={evening}, Total={total}
Method: {method}
Reason tags: {reason_tags}
7-day trend: {trend_summary}

Respond with 1-2 sentences only. Do not invent numbers beyond what is given.
"""

PREP_RATIONALE_PROMPT = """\
You are BakeWise. Explain this prep recommendation to an outlet manager in plain language.

SKU: {sku_name} | Outlet: {outlet_name}
Forecast demand: {forecast_total} units
Current stock: {current_stock} units
Safety buffer: {safety_buffer_pct}%
Waste rate (7d): {waste_rate_pct}%
Recommended prep: Morning={morning}, Midday={midday}, Evening={evening}

Write 1-2 sentences. Do not add numbers not present above.
"""

WASTE_ALERT_EXPLANATION_PROMPT = """\
You are BakeWise. Explain this waste risk alert to an operations manager.

Outlet: {outlet_name}
SKU: {sku_name}
Daypart: {daypart}
Risk level: {risk_level}
Triggers: {triggers}
3-day waste rate: {waste_rate_pct}%

Write 2-3 sentences. Be specific and actionable. Do not invent numbers.
"""

STOCKOUT_ALERT_EXPLANATION_PROMPT = """\
You are BakeWise. Explain this stockout risk to a central kitchen manager.

Outlet: {outlet_name}
SKU: {sku_name}
Affected daypart: {daypart}
Shortage qty: {shortage_qty} units
Coverage: {coverage_pct}%
Reason: {reason}

Write 2 sentences. Be direct. Do not add new numbers.
"""

REPLENISHMENT_RATIONALE_PROMPT = """\
You are BakeWise. Explain this ingredient reorder recommendation.

Ingredient: {ingredient_name}
Current stock: {stock_on_hand} {unit}
Projected need: {need_qty} {unit}
Reorder quantity: {reorder_qty} {unit}
Urgency: {urgency}
Driving SKUs: {driving_skus}

Write 1-2 sentences explaining why this reorder is needed and what happens if delayed.
"""

DAILY_BRIEF_PROMPT = """\
You are BakeWise. Write a clear, professional daily operations brief for {date} ({weekday}).

Data summary:
- Total predicted sales: {total_predicted_sales} units
- Waste risk score: {waste_risk_score}/100
- Stockout risk score: {stockout_risk_score}/100
- High-risk waste alerts: {high_waste_count}
- High-risk stockout alerts: {high_stockout_count}
- Critical reorder items: {critical_reorder_count}
- Top actions: {top_actions}
- At-risk outlets: {at_risk_outlets}

Write exactly 3 paragraphs:
1. Overall readiness summary
2. Key risks and specific outlets/SKUs to watch
3. Top 3 recommended actions for the operations team

Do not invent numbers beyond what is provided above.
"""
