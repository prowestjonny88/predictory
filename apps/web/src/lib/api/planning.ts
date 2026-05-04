import { demoLatestPlan } from "@/lib/demo-data";

export interface DailyPlanMetrics {
  wape: number;
  bias: number;
  p10_p90_coverage: number;
  estimated_mismatch_cost_delta_pct: number;
}

export interface FinancialExposure {
  stockout_exposure_rm: number;
  waste_exposure_rm: number;
}

export interface ReplenishmentLine {
  ingredient_id: string;
  ingredient_name: string;
  required_qty: number;
  current_stock: number;
  shortage_qty: number;
  reorder_qty: number;
  unit: string;
  urgency?: string;
}

export interface DailyPlanTopAction {
  id: string;
  plan_id?: number;
  outlet_id: string;
  outlet_name: string;
  sku_id: string;
  sku_name: string;
  sku_category: string;
  daypart: string;
  p10: number;
  p50: number;
  p90: number;
  opening_stock: number;
  recommended_prep: number;
  batch_size: number;
  waste_cost: number;
  stockout_cost: number;
  financial_exposure: FinancialExposure;
  reason_summary: string;
  replenishment: ReplenishmentLine[];
  status: string;
  explanation?: string;
}

export interface DailyPlanLatestResponse {
  forecast_run_id: string;
  model_run_id: string;
  model_version: string;
  engine_name: string;
  model_status: string;
  validation_window: string;
  metrics: DailyPlanMetrics;
  top_actions: DailyPlanTopAction[];
}

export interface RegeneratePlanRequest {
  date: string;
  reason: string;
}

export interface RegeneratePlanResponse {
  forecast_run_id: string;
  status: string;
  message: string;
}

export interface ManagerNoteRequest {
  forecast_run_id: string;
  note: string;
}

export interface ManagerNoteResponse {
  parsed_adjustment: {
    outlet_id: string;
    daypart: string;
    sku_category: string;
    suggested_adjustment_pct: number;
    reason: string;
    requires_confirmation: boolean;
  };
  explanation: string;
}

export interface ApplyAdjustmentRequest {
  forecast_run_id: string;
  confirmed: boolean;
  adjustment: ManagerNoteResponse["parsed_adjustment"];
}

export interface ApplyAdjustmentResponse {
  forecast_run_id: string;
  status: string;
  message: string;
  updated_line_ids: number[];
  audit_event_ids: number[];
  replenishment_plan_id: number | null;
}

export interface DecisionRequest {
  operator_action: "approved" | "edited" | "rejected";
  final_prep?: number;
  operator_reason?: string;
  role?: string;
}

export interface DecisionResponse {
  audit_event_ids: number[];
  status: string;
  final_prep?: number;
  replenishment_plan_id?: number | null;
}

export interface ExplainRecommendationResponse {
  explanation: string;
  evidence: Record<string, unknown>;
  source_type: "deterministic" | "llm_rephrased";
}

interface BackendMetrics {
  validation_metrics?: {
    wape?: number;
    bias?: number;
  };
  wape?: number;
  bias?: number;
  band_coverage_p10_p90?: number;
  p10_p90_coverage?: number;
  estimated_mismatch_cost_delta_pct?: number;
}

interface BackendForecastLine {
  outlet_id: number;
  outlet_name: string;
  sku_id: number;
  sku_name: string;
  morning: number;
  midday: number;
  evening: number;
  total: number;
  reason_tags?: string[];
}

interface BackendPrepLine {
  id: number;
  outlet_id: number;
  sku_id: number;
  daypart: string;
  recommended_units: number;
  edited_units: number | null;
  current_stock: number;
  status: string;
}

interface BackendReplenishmentLine {
  ingredient_id: number;
  ingredient_name: string;
  need_qty: number;
  stock_on_hand: number;
  reorder_qty: number;
  urgency: string;
  driving_skus: string[];
}

interface BackendDailyPlan {
  forecast_run_id: string;
  model_run_id: number | null;
  model_version: string;
  engine_name: string;
  model_status: string;
  validation_window: string;
  metrics: BackendMetrics;
  date: string;
  prep_plan_id: number | null;
  replenishment_plan_id: number | null;
  forecasts: BackendForecastLine[];
  prep_plan: BackendPrepLine[];
  replenishment_plan: BackendReplenishmentLine[];
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const V1 = `${API_URL}/api/v1`;

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

function normalizeMetrics(metrics: BackendMetrics): DailyPlanMetrics {
  return {
    wape: metrics.validation_metrics?.wape ?? metrics.wape ?? 0,
    bias: metrics.validation_metrics?.bias ?? metrics.bias ?? 0,
    p10_p90_coverage: metrics.band_coverage_p10_p90 ?? metrics.p10_p90_coverage ?? 0,
    estimated_mismatch_cost_delta_pct: metrics.estimated_mismatch_cost_delta_pct ?? -0.12,
  };
}

function daypartForecast(line: BackendForecastLine | undefined, daypart: string) {
  if (!line) return 0;
  const key = daypart.toLowerCase();
  if (key === "morning") return line.morning;
  if (key === "midday") return line.midday;
  if (key === "evening") return line.evening;
  return line.total;
}

function toBackendDailyPlan(payload: BackendDailyPlan): DailyPlanLatestResponse {
  const forecastByKey = new Map(
    payload.forecasts.map((line) => [`${line.outlet_id}:${line.sku_id}`, line])
  );
  const categoryBySkuName = (name: string) => {
    const lower = name.toLowerCase();
    if (lower.includes("croissant") || lower.includes("danish") || lower.includes("roll")) return "Pastry";
    if (lower.includes("muffin")) return "Muffin";
    if (lower.includes("bread") || lower.includes("loaf")) return "Bread";
    if (lower.includes("tart")) return "Dessert";
    return "Bakery";
  };

  const top_actions = payload.prep_plan
    .map((line) => {
      const forecast = forecastByKey.get(`${line.outlet_id}:${line.sku_id}`);
      const p50 = Math.round(daypartForecast(forecast, line.daypart));
      const p10 = Math.round(Math.max(0, p50 * 0.8));
      const p90 = Math.round(Math.max(p50, p50 * 1.25));
      const finalPrep = line.edited_units ?? line.recommended_units;
      const skuName = forecast?.sku_name ?? `SKU ${line.sku_id}`;
      const replenishment = payload.replenishment_plan
        .filter((repl) => repl.driving_skus?.includes(skuName))
        .map((repl) => ({
          ingredient_id: String(repl.ingredient_id),
          ingredient_name: repl.ingredient_name,
          required_qty: repl.need_qty,
          current_stock: repl.stock_on_hand,
          shortage_qty: Math.max(0, repl.need_qty - repl.stock_on_hand),
          reorder_qty: repl.reorder_qty,
          unit: "units",
          urgency: repl.urgency,
        }));
      const stockoutUnits = Math.max(0, p50 - line.current_stock - finalPrep);
      const wasteUnits = Math.max(0, finalPrep + line.current_stock - p10);

      return {
        id: String(line.id),
        plan_id: payload.prep_plan_id ?? undefined,
        outlet_id: String(line.outlet_id),
        outlet_name: forecast?.outlet_name ?? `Outlet ${line.outlet_id}`,
        sku_id: String(line.sku_id),
        sku_name: skuName,
        sku_category: categoryBySkuName(skuName),
        daypart: line.daypart,
        p10,
        p50,
        p90,
        opening_stock: line.current_stock,
        recommended_prep: finalPrep,
        batch_size: 5,
        waste_cost: 3.5,
        stockout_cost: 8.5,
        financial_exposure: {
          stockout_exposure_rm: Math.round(stockoutUnits * 8.5),
          waste_exposure_rm: Math.round(wasteUnits * 3.5),
        },
        reason_summary:
          p50 > 0
            ? `Prep ${finalPrep} units for ${line.daypart}; p50 demand is ${p50}, opening stock is ${line.current_stock}, and the range is ${p10}-${p90}.`
            : `Prep ${finalPrep} units for ${line.daypart}; backend plan generated this recommendation from saved demand context.`,
        replenishment,
        status: line.status,
      } satisfies DailyPlanTopAction;
    })
    .sort(
      (a, b) =>
        b.financial_exposure.stockout_exposure_rm +
        b.financial_exposure.waste_exposure_rm -
        (a.financial_exposure.stockout_exposure_rm + a.financial_exposure.waste_exposure_rm)
    )
    .slice(0, 18);

  return {
    forecast_run_id: payload.forecast_run_id,
    model_run_id: payload.model_run_id ? String(payload.model_run_id) : "",
    model_version: payload.model_version,
    engine_name: payload.engine_name,
    model_status: payload.model_status,
    validation_window: payload.validation_window,
    metrics: normalizeMetrics(payload.metrics),
    top_actions,
  };
}

export const planningApi = {
  latestPlan: async (date: string): Promise<DailyPlanLatestResponse> => {
    try {
      const payload = await apiFetch<BackendDailyPlan>(`${V1}/api/daily-plan/latest?date=${date}`);
      return toBackendDailyPlan(payload);
    } catch (_error) {
      return demoLatestPlan();
    }
  },

  regeneratePlan: (payload: RegeneratePlanRequest): Promise<RegeneratePlanResponse> =>
    apiFetch(`${V1}/api/daily-plan/regenerate?date=${payload.date}&reason=${encodeURIComponent(payload.reason)}`, {
      method: "POST",
    }),

  parseManagerNote: (payload: ManagerNoteRequest): Promise<ManagerNoteResponse> =>
    apiFetch(`${V1}/copilot/parse-manager-note`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  applyManagerNote: (payload: ApplyAdjustmentRequest): Promise<ApplyAdjustmentResponse> =>
    apiFetch(`${V1}/copilot/apply-note-adjustment`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  explainRecommendation: (recommendationId: string): Promise<ExplainRecommendationResponse> =>
    apiFetch(`${V1}/copilot/explain-recommendation`, {
      method: "POST",
      body: JSON.stringify({ recommendation_id: Number(recommendationId) }),
    }),

  submitDecision: async (
    action: DailyPlanTopAction,
    payload: DecisionRequest
  ): Promise<DecisionResponse> => {
    if (!action.plan_id) {
      return {
        audit_event_ids: [],
        status: payload.operator_action,
        final_prep: payload.final_prep,
        replenishment_plan_id: null,
      };
    }

    if (payload.operator_action === "edited") {
      return apiFetch(`${V1}/prep-plans/${action.plan_id}/edit`, {
        method: "POST",
        body: JSON.stringify({
          line_id: Number(action.id),
          final_prep: payload.final_prep ?? action.recommended_prep,
          operator_reason: payload.operator_reason ?? "Edited in Daily Planning Workspace",
          user_id: payload.role ?? "planner",
        }),
      });
    }

    if (payload.operator_action === "rejected") {
      return apiFetch(`${V1}/prep-plans/${action.plan_id}/reject`, {
        method: "POST",
        body: JSON.stringify({
          operator_reason: payload.operator_reason ?? "Rejected in Daily Planning Workspace",
          rejected_by: payload.role ?? "planner",
        }),
      });
    }

    return apiFetch(`${V1}/prep-plans/${action.plan_id}/approve`, {
      method: "POST",
      body: JSON.stringify({
        approved_by: payload.role ?? "planner",
        operator_reason: payload.operator_reason ?? "Approved in Daily Planning Workspace",
      }),
    });
  },
};
