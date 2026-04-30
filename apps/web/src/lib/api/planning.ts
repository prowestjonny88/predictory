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
  unit: string;
}

export interface DailyPlanTopAction {
  id: string;
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
  adjustment: {
    outlet_id: string;
    daypart: string;
    sku_category: string;
    adjustment_pct: number;
    reason: string;
  };
}

export interface ApplyAdjustmentResponse {
  forecast_run_id: string;
  status: string;
  message: string;
}

export interface DecisionRequest {
  operator_action: "approved" | "edited" | "rejected" | string;
  final_prep?: number;
  operator_reason?: string;
  role?: string;
}

export interface DecisionResponse {
  audit_event_id: string;
  status: string;
  final_prep: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

export const planningApi = {
  latestPlan: (date: string): Promise<DailyPlanLatestResponse> =>
    apiFetch(`${API_URL}/api/daily-plan/latest?date=${date}`),
  regeneratePlan: (payload: RegeneratePlanRequest): Promise<RegeneratePlanResponse> =>
    apiFetch(`${API_URL}/api/daily-plan/regenerate`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  parseManagerNote: (payload: ManagerNoteRequest): Promise<ManagerNoteResponse> =>
    apiFetch(`${API_URL}/api/gemini/parse-manager-note`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyManagerNote: (payload: ApplyAdjustmentRequest): Promise<ApplyAdjustmentResponse> =>
    apiFetch(`${API_URL}/api/daily-plan/apply-adjustment`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitDecision: (recommendationId: string, payload: DecisionRequest): Promise<DecisionResponse> =>
    apiFetch(`${API_URL}/api/daily-plan/recommendations/${recommendationId}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
