export type LanguageCode = "en" | "ms" | "zh-CN";

export interface Outlet {
  id: number;
  code: string;
  name: string;
  address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  city?: string | null;
  is_active: boolean;
}

export interface SKU {
  id: number;
  code: string;
  sku_id?: string;
  name: string;
  category: string;
  price: number;
  freshness_hours: number;
  shelf_life_hours?: number;
  is_bestseller: boolean;
  safety_buffer_pct: number;
  is_active: boolean;
}

export interface Ingredient {
  id: number;
  name: string;
  code: string;
  ingredient_id?: string;
  unit: string;
  stock_on_hand?: number;
  reorder_point?: number;
  supplier_lead_time_hours?: number;
  lead_time_hours?: number;
  cost_per_unit: number;
}

export interface Inventory {
  id: number;
  outlet_id: number;
  sku_id: number;
  sku_name: string;
  snapshot_date: string;
  snapshot_time: string;
  units_on_hand: number;
}

export interface ForecastLine {
  id: number;
  outlet_id: number;
  sku_id: number;
  morning: number;
  midday: number;
  evening: number;
  total: number;
  method: string;
  confidence: number;
  manual_adjustment_pct: number | null;
  rationale_json: Record<string, unknown> | null;
  outlet_name?: string;
  sku_name?: string;
}

export interface ForecastRun {
  id: number;
  forecast_date: string;
  status: string;
  lines: ForecastLine[];
}

export interface ForecastSignal {
  label: string;
  source: string;
  status: string;
  adjustment_pct: number;
  details: string[];
}

export interface StockoutCensoringSummary {
  enabled: boolean;
  adjusted_history_days: number;
  adjusted_dates: string[];
  note: string;
}

export interface ForecastOverride {
  id: number;
  target_date: string;
  outlet_id: number;
  sku_id: number | null;
  sku_name?: string | null;
  override_type: "event" | "promo";
  title: string;
  notes: string | null;
  adjustment_pct: number;
  enabled: boolean;
  created_by: string | null;
}

export interface ForecastContext {
  target_date: string;
  outlet_id: number;
  sku_id: number | null;
  holiday: ForecastSignal | null;
  weather: ForecastSignal;
  stockout_censoring: StockoutCensoringSummary;
  active_overrides: ForecastOverride[];
  combined_adjustment_pct: number;
}

export interface ForecastOverridePayload {
  target_date: string;
  outlet_id: number;
  sku_id?: number | null;
  override_type: "event" | "promo";
  title: string;
  notes?: string | null;
  adjustment_pct: number;
  enabled: boolean;
  created_by?: string;
}

export interface DailyPlanForecastLine {
  outlet_id: number;
  outlet_name: string;
  sku_id: number;
  sku_name: string;
  morning: number;
  midday: number;
  evening: number;
  total: number;
  reason_tags: string[];
}

export interface DailyPlanPrepLine {
  id: number;
  outlet_id: number;
  sku_id: number;
  daypart: string;
  recommended_units: number;
  edited_units: number | null;
  current_stock: number;
  status: "pending" | "accepted" | "edited" | string;
}

export interface PrepPlanDetailLine {
  id: number;
  plan_id: number;
  outlet_id: number;
  sku_id: number;
  daypart: string;
  recommended_units: number;
  edited_units: number | null;
  current_stock: number;
  status: "pending" | "accepted" | "edited" | string;
}

export interface PrepPlanDetail {
  id: number;
  plan_date: string;
  status: "draft" | "approved" | string;
  approved_by: string | null;
  lines: PrepPlanDetailLine[];
}

export type UrgencyLevel = "critical" | "high" | "medium" | "low";
export type RiskLevel = "critical" | "high" | "medium" | "low";

export interface DailyPlanReplenishmentLine {
  ingredient_id: number;
  ingredient_name: string;
  need_qty: number;
  stock_on_hand: number;
  reorder_qty: number;
  urgency: UrgencyLevel;
  driving_skus: string[];
}

export interface DailyPlanAlert {
  outlet_name: string;
  sku_name: string;
  daypart: string;
  risk_level: RiskLevel;
  reason: string;
}

export interface DailyPlanSummary {
  total_predicted_sales: number;
  waste_risk_score: number;
  stockout_risk_score: number;
  top_actions: string[];
  at_risk_outlets: string[];
}

export interface DailyPlan {
  date: string;
  prep_plan_id: number | null;
  replenishment_plan_id: number | null;
  forecasts: DailyPlanForecastLine[];
  prep_plan: DailyPlanPrepLine[];
  replenishment_plan: DailyPlanReplenishmentLine[];
  waste_alerts: DailyPlanAlert[];
  stockout_alerts: DailyPlanAlert[];
  summary: DailyPlanSummary;
}

export interface WasteAlert {
  outlet_id: number;
  outlet_name: string;
  sku_id: number;
  sku_name: string;
  daypart: string;
  risk_level: RiskLevel;
  triggers: string[];
  reason: string;
  waste_rate: number;
  excess_prep_units: number;
}

export interface StockoutAlert {
  outlet_id: number;
  outlet_name: string;
  sku_id: number;
  sku_name: string;
  affected_daypart: string;
  risk_level: RiskLevel;
  shortage_qty: number;
  reason: string;
  coverage_pct: number;
}

export interface ExplainPlanRequest {
  context_type: "forecast" | "prep" | "waste" | "stockout" | "replenishment";
  outlet_id: number;
  sku_id: number;
  plan_date: string;
  language?: LanguageCode;
}

export interface ExplainPlanResponse {
  explanation: string;
  context_type: string;
  outlet_name: string;
  sku_name: string;
}

export interface DailyBriefResponse {
  brief: string;
  date: string;
}

export interface DailyBriefRequest {
  brief_date: string;
  language?: LanguageCode;
}

export interface ActionTarget {
  outlet_id: number | null;
  outlet_name: string | null;
  sku_id: number | null;
  sku_name: string | null;
  ingredient_id: number | null;
  ingredient_name: string | null;
}

export interface AgentAction {
  action_type: "prep" | "reorder" | "risk" | "rebalance";
  action_text: string;
  urgency: UrgencyLevel;
  estimated_impact: string;
  target: ActionTarget;
  evidence: string[];
  source_type: "deterministic" | "llm_rephrased";
}

export interface DailyActionsResponse {
  date: string;
  brief: string;
  fallback_mode: boolean;
  top_actions: AgentAction[];
  prep_actions: AgentAction[];
  reorder_actions: AgentAction[];
  risk_warnings: AgentAction[];
  rebalance_suggestions: AgentAction[];
}

export interface DailyActionsRequest {
  target_date: string;
  top_n?: number;
  language?: LanguageCode;
}

export interface ScenarioResult {
  scenario: string;
  baseline: Record<string, number | string>;
  modified: Record<string, number | string>;
  delta: Record<string, number | string>;
  recommendation: string;
  interpretation: string;
}

export interface ScenarioRequest {
  scenario_text: string;
  target_date?: string;
  language?: LanguageCode;
}

export interface PlanRunResult {
  plan_id: number;
  plan_date: string;
  status: string;
  lines_count: number;
}

export interface ImportResult {
  detected_type?: string;
  data_type?: string;
  rows_inserted?: number;
  rows_processed?: number;
  rows_parsed?: number;
  rows_committed?: number;
  errors: string[];
}

export interface HealthResponse {
  status: string;
  db_status?: string;
}
