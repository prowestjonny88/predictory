// ── Master data ─────────────────────────────────────────────────────────────

export interface Outlet {
  id: number;
  code: string;
  name: string;
  city: string;
  is_active: boolean;
}

export interface SKU {
  id: number;
  sku_id: string;
  name: string;
  category: string;
  price: number;
  shelf_life_hours: number;
  is_bestseller: boolean;
  is_active: boolean;
}

export interface Ingredient {
  id: number;
  ingredient_id: string;
  name: string;
  unit: string;
  cost_per_unit: number;
  lead_time_hours: number;
  reorder_point: number;
}

// ── Forecasting ──────────────────────────────────────────────────────────────

export interface ForecastLine {
  id: number;
  forecast_run_id: number;
  sku_id: number;
  sku_name?: string;
  daypart: "morning" | "afternoon" | "evening";
  predicted_qty: number;
  adjusted_qty: number | null;
  adjustment_pct: number | null;
}

export interface ForecastRun {
  id: number;
  outlet_id: number;
  outlet_name?: string;
  forecast_date: string;
  method: string;
  created_at: string;
  lines: ForecastLine[];
}

// ── Prep Plan ────────────────────────────────────────────────────────────────

export interface PrepPlanLine {
  id: number;
  prep_plan_id: number;
  sku_id: number;
  sku_name?: string;
  daypart: string;
  forecast_qty: number;
  prep_qty: number;
  edited_units: number | null;
  buffer_pct: number | null;
  status: "pending" | "accepted" | "edited";
}

export interface PrepPlan {
  id: number;
  outlet_id: number;
  outlet_name?: string;
  plan_date: string;
  status: "draft" | "approved";
  approved_at: string | null;
  approved_by: string | null;
  lines: PrepPlanLine[];
}

// ── Replenishment ────────────────────────────────────────────────────────────

export type UrgencyLevel = "critical" | "high" | "medium" | "low";

export interface ReplenishmentPlanLine {
  id: number;
  replenishment_plan_id: number;
  ingredient_id: number;
  ingredient_name?: string;
  outlet_id: number;
  outlet_name?: string;
  current_stock: number | null;
  required_qty: number;
  order_qty: number;
  urgency: UrgencyLevel;
  is_ordered: boolean;
}

export interface ReplenishmentPlan {
  id: number;
  plan_date: string;
  created_at: string;
  lines: ReplenishmentPlanLine[];
}

// ── Alerts ───────────────────────────────────────────────────────────────────

export type RiskLevel = "critical" | "high" | "medium" | "low";

export interface WasteAlert {
  sku_id: number;
  sku_name?: string;
  outlet_id: number;
  outlet_name?: string;
  risk_level: RiskLevel;
  reason: string;
  waste_rate_pct?: number;
  triggers?: string[];
  days_below_threshold?: number;
}

export interface StockoutAlert {
  sku_id: number;
  sku_name?: string;
  outlet_id: number;
  outlet_name?: string;
  risk_level: RiskLevel;
  reason: string;
  coverage_pct?: number;
  message?: string;
}

// ── Daily plan ────────────────────────────────────────────────────────────────

export interface AtRiskOutlet {
  outlet_id: number;
  outlet_name?: string;
  risk_level: RiskLevel;
  message?: string;
  reason?: string;
}

export interface DailyPlanSummary {
  total_predicted_sales: number;
  waste_risk_score: number;
  stockout_risk_score: number;
  top_actions: string[];
  at_risk_outlets: AtRiskOutlet[];
}

export interface DailyPlan {
  plan_date: string;
  prep_plan: PrepPlan | null;
  replenishment_plan: ReplenishmentPlan | null;
  waste_alerts: WasteAlert[];
  stockout_alerts: StockoutAlert[];
  summary: DailyPlanSummary;
}

// ── Copilot ────────────────────────────────────────────────────────────────────

export interface ScenarioResult {
  scenario_text: string;
  target_date: string;
  baseline_waste_alerts: number;
  baseline_stockout_alerts: number;
  projected_waste_alerts: number;
  projected_stockout_alerts: number;
  explanation: string;
  affected_skus: string[];
}

export interface ImportResult {
  detected_type: string;
  rows_inserted?: number;
  rows_processed?: number;
  errors: string[];
}

export interface HealthResponse {
  status: string;
  db_status?: string;
}
