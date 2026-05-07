export interface DailyPlanMetrics {
  wape: number;
  bias: number;
  p10_p90_coverage: number;
  estimated_mismatch_cost_delta_pct: number | null;
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

export interface DailyPlanSummary {
  scope: "full_plan" | "top_actions";
  total_predicted_sales: number;
  waste_risk_score: number;
  stockout_risk_score: number;
  top_actions: string[];
  at_risk_outlets: string[];
  total_recommended_prep_units: number;
  total_stockout_exposure_rm: number;
  total_waste_exposure_rm: number;
  ingredient_shortage_count: number;
  pending_action_count: number;
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
  priority_score: number;
  priority_reason: string;
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
  active_engine_name: string;
  model_status: string;
  model_artifact_status: string;
  model_artifact_available: boolean;
  forecast_source_label: string;
  validation_window: string;
  data_source: "backend";
  metrics: DailyPlanMetrics;
  summary: DailyPlanSummary;
  top_actions: DailyPlanTopAction[];
}

export interface ForecastReadiness {
  ready: boolean;
  target_date: string;
  blockers: string[];
  grouped_blockers?: Record<string, string[]>;
  artifact_files_found?: boolean;
  artifact_validated_for_inference?: boolean;
  artifact_validation_error?: string | null;
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
  language?: "en" | "ms" | "zh-CN";
}

export interface ManagerNoteResponse {
  parsed_adjustment: {
    outlet_id: string;
    daypart: string;
    sku_category: string;
    suggested_adjustment_pct: number;
    reason: string;
    requires_confirmation: boolean;
    parse_source: "llm_validated";
    uncertainty_reason?: string | null;
  };
  explanation: string;
  source_type: "llm_rephrased";
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
  application_mode: "prep_edit_only" | "forecast_override_recompute";
  updated_line_ids: number[];
  audit_event_ids: number[];
  replenishment_plan_id: number | null;
  line_changes?: {
    line_id: number;
    outlet_name: string;
    sku_name: string;
    daypart: string;
    before_prep: number;
    after_prep: number;
  }[];
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
  source_type: "llm_rephrased";
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

interface BackendDailyPlan {
  forecast_run_id: string;
  model_run_id: number | null;
  model_version: string;
  engine_name: string;
  active_engine_name?: string;
  model_status: string;
  model_artifact_status?: string;
  model_artifact_available?: boolean;
  forecast_source_label?: string;
  validation_window: string;
  data_source?: "backend";
  metrics: BackendMetrics;
  summary?: DailyPlanSummary;
  top_actions?: DailyPlanTopAction[];
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
    estimated_mismatch_cost_delta_pct: metrics.estimated_mismatch_cost_delta_pct ?? null,
  };
}

function toBackendDailyPlan(payload: BackendDailyPlan): DailyPlanLatestResponse {
  const topActions = payload.top_actions ?? [];
  if (!payload.summary) {
    throw new Error("Backend daily plan summary is required.");
  }
  return {
    forecast_run_id: payload.forecast_run_id,
    model_run_id: payload.model_run_id ? String(payload.model_run_id) : "",
    model_version: payload.model_version,
    engine_name: payload.engine_name,
    active_engine_name: payload.active_engine_name ?? payload.engine_name,
    model_status: payload.model_status,
    model_artifact_status: payload.model_artifact_status ?? "unknown",
    model_artifact_available: payload.model_artifact_available ?? false,
    forecast_source_label: payload.forecast_source_label ?? `Generated by: ${payload.engine_name}`,
    validation_window: payload.validation_window,
    data_source: payload.data_source ?? "backend",
    metrics: normalizeMetrics(payload.metrics),
    summary: payload.summary,
    top_actions: topActions,
  };
}

export const planningApi = {
  latestPlan: async (date: string): Promise<DailyPlanLatestResponse> => {
    const payload = await apiFetch<BackendDailyPlan>(`${V1}/api/daily-plan/latest?date=${date}`);
    return toBackendDailyPlan(payload);
  },

  forecastReadiness: (date: string): Promise<ForecastReadiness> =>
    apiFetch<ForecastReadiness>(`${V1}/forecast-readiness?target_date=${date}`),

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

  explainRecommendation: (recommendationId: string, language: "en" | "ms" | "zh-CN" = "en"): Promise<ExplainRecommendationResponse> =>
    apiFetch(`${V1}/copilot/explain-recommendation`, {
      method: "POST",
      body: JSON.stringify({ recommendation_id: Number(recommendationId), language }),
    }),

  submitDecision: async (
    action: DailyPlanTopAction,
    payload: DecisionRequest
  ): Promise<DecisionResponse> => {
    if (!action.plan_id) {
      throw new Error("Backend prep plan ID is required before recording a decision.");
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
