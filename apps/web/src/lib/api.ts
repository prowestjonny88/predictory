import type {
  DailyActionsRequest,
  DailyActionsResponse,
  DailyBriefRequest,
  DailyBriefResponse,
  DailyPlan,
  ExplainPlanRequest,
  ExplainPlanResponse,
  ForecastContext,
  ForecastOverride,
  ForecastOverridePayload,
  ForecastRun,
  HealthResponse,
  ImportResult,
  Ingredient,
  LanguageCode,
  Outlet,
  PlanRunResult,
  PrepPlanDetail,
  ScenarioRequest,
  ScenarioResult,
  SKU,
  StockoutAlert,
  WasteAlert,
} from "@/types";

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

export const api = {
  outlets: (): Promise<Outlet[]> => apiFetch<Outlet[]>(`${V1}/outlets`),
  skus: (): Promise<SKU[]> => apiFetch<SKU[]>(`${V1}/skus`),
  ingredients: (): Promise<Ingredient[]> => apiFetch<Ingredient[]>(`${V1}/ingredients`),
  health: (): Promise<HealthResponse> => apiFetch<HealthResponse>(`${API_URL}/health`),

  dailyPlan: (date: string): Promise<DailyPlan> =>
    apiFetch<DailyPlan>(`${V1}/api/daily-plan/${date}`),

  runForecast: (date: string): Promise<ForecastRun> =>
    apiFetch<ForecastRun>(`${V1}/forecasts/run?target_date=${date}`, { method: "POST" }),
  getForecasts: (date: string, outletId?: string): Promise<ForecastRun[]> =>
    apiFetch<ForecastRun[]>(
      `${V1}/forecasts?forecast_date=${date}${outletId ? `&outlet_id=${outletId}` : ""}`
    ),
  adjustForecastLine: (runId: number, lineId: number, pct: number): Promise<unknown> =>
    apiFetch(`${V1}/forecasts/${runId}/lines/${lineId}`, {
      method: "PATCH",
      body: JSON.stringify({ manual_adjustment_pct: pct }),
    }),
  getForecastContext: (
    targetDate: string,
    outletId: number,
    skuId?: number | null
  ): Promise<ForecastContext> =>
    apiFetch<ForecastContext>(
      `${V1}/forecast-context?target_date=${targetDate}&outlet_id=${outletId}${
        skuId ? `&sku_id=${skuId}` : ""
      }`
    ),
  getForecastOverrides: (
    targetDate: string,
    outletId: number,
    skuId?: number | null
  ): Promise<ForecastOverride[]> =>
    apiFetch<ForecastOverride[]>(
      `${V1}/forecast-overrides?target_date=${targetDate}&outlet_id=${outletId}${
        skuId ? `&sku_id=${skuId}` : ""
      }`
    ),
  createForecastOverride: (payload: ForecastOverridePayload): Promise<ForecastOverride> =>
    apiFetch<ForecastOverride>(`${V1}/forecast-overrides`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateForecastOverride: (
    overrideId: number,
    payload: Partial<Pick<ForecastOverridePayload, "title" | "notes" | "adjustment_pct" | "enabled">>
  ): Promise<ForecastOverride> =>
    apiFetch<ForecastOverride>(`${V1}/forecast-overrides/${overrideId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deleteForecastOverride: (overrideId: number): Promise<void> =>
    apiFetch<void>(`${V1}/forecast-overrides/${overrideId}`, { method: "DELETE" }),

  runPrepPlan: (date: string): Promise<PlanRunResult> =>
    apiFetch<PlanRunResult>(`${V1}/plans/prep/run?target_date=${date}`, { method: "POST" }),
  getPrepPlan: (planId: number): Promise<PrepPlanDetail> =>
    apiFetch<PrepPlanDetail>(`${V1}/plans/prep/${planId}`),
  editPrepLine: (planId: number, lineId: number, editedUnits: number): Promise<unknown> =>
    apiFetch(`${V1}/plans/prep/${planId}/lines/${lineId}`, {
      method: "PATCH",
      body: JSON.stringify({ edited_units: editedUnits }),
    }),
  approvePrepPlan: (planId: number, approvedBy: string): Promise<PrepPlanDetail> =>
    apiFetch<PrepPlanDetail>(`${V1}/plans/prep/${planId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  runReplenishment: (date: string): Promise<PlanRunResult> =>
    apiFetch<PlanRunResult>(`${V1}/plans/replenishment/run?target_date=${date}`, {
      method: "POST",
    }),

  wasteAlerts: (date: string): Promise<WasteAlert[]> =>
    apiFetch<WasteAlert[]>(`${V1}/alerts/waste?target_date=${date}`),
  stockoutAlerts: (date: string): Promise<StockoutAlert[]> =>
    apiFetch<StockoutAlert[]>(`${V1}/alerts/stockout?target_date=${date}`),

  explainPlan: (body: ExplainPlanRequest): Promise<ExplainPlanResponse> =>
    apiFetch<ExplainPlanResponse>(`${V1}/copilot/explain-plan`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dailyBrief: (date: string, language: LanguageCode = "en"): Promise<DailyBriefResponse> =>
    apiFetch<DailyBriefResponse>(`${V1}/copilot/daily-brief`, {
      method: "POST",
      body: JSON.stringify({ brief_date: date, language } satisfies DailyBriefRequest),
    }),
  dailyActions: (
    date: string,
    topN = 5,
    language: LanguageCode = "en"
  ): Promise<DailyActionsResponse> =>
    apiFetch<DailyActionsResponse>(`${V1}/copilot/daily-actions`, {
      method: "POST",
      body: JSON.stringify({
        target_date: date,
        top_n: topN,
        language,
      } satisfies DailyActionsRequest),
    }),
  runScenario: (
    text: string,
    date: string,
    language: LanguageCode = "en"
  ): Promise<ScenarioResult> =>
    apiFetch<ScenarioResult>(`${V1}/copilot/run-scenario`, {
      method: "POST",
      body: JSON.stringify({
        scenario_text: text,
        target_date: date,
        language,
      } satisfies ScenarioRequest),
    }),

  uploadCSV: (file: File, dataType = "auto"): Promise<ImportResult> => {
    const formData = new FormData();
    formData.append("file", file);
    return apiFetch<ImportResult>(`${V1}/imports/upload?data_type=${dataType}`, {
      method: "POST",
      headers: {},
      body: formData,
    });
  },
};
