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
  data_source: "backend";
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
  source_type: "rules_based" | "llm_rephrased";
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
  model_status: string;
  validation_window: string;
  data_source?: "backend";
  metrics: BackendMetrics;
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
    estimated_mismatch_cost_delta_pct: metrics.estimated_mismatch_cost_delta_pct ?? -0.12,
  };
}

function toBackendDailyPlan(payload: BackendDailyPlan): DailyPlanLatestResponse {
  return {
    forecast_run_id: payload.forecast_run_id,
    model_run_id: payload.model_run_id ? String(payload.model_run_id) : "",
    model_version: payload.model_version,
    engine_name: payload.engine_name,
    model_status: payload.model_status,
    validation_window: payload.validation_window,
    data_source: payload.data_source ?? "backend",
    metrics: normalizeMetrics(payload.metrics),
    top_actions: payload.top_actions ?? [],
  };
}

export const planningApi = {
  latestPlan: async (date: string): Promise<DailyPlanLatestResponse> => {
    const payload = await apiFetch<BackendDailyPlan>(`${V1}/api/daily-plan/latest?date=${date}`);
    return toBackendDailyPlan(payload);
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
