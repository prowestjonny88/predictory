import type {
  DailyPlan,
  ForecastRun,
  PrepPlan,
  ReplenishmentPlan,
  WasteAlert,
  StockoutAlert,
  Outlet,
  SKU,
  ScenarioResult,
  ImportResult,
  HealthResponse,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// All routers are mounted at /api/v1 ; planning router has /api/daily-plan
// as its own path prefix resulting in /api/v1/api/daily-plan/{date}.
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
  return res.json() as Promise<T>;
}

export const api = {
  // ── Master data ───────────────────────────────────────────────────────────
  outlets:     (): Promise<Outlet[]> => apiFetch<Outlet[]>(`${V1}/outlets`),
  skus:        (): Promise<SKU[]>    => apiFetch<SKU[]>(`${V1}/skus`),
  ingredients: (): Promise<unknown[]> => apiFetch<unknown[]>(`${V1}/ingredients`),
  health:      (): Promise<HealthResponse> =>
    apiFetch<HealthResponse>(`${API_URL}/health`),

  // ── Daily plan (main orchestration endpoint) ──────────────────────────────
  // Planning router path is /api/daily-plan/{date} mounted at /api/v1 prefix.
  dailyPlan: (date: string): Promise<DailyPlan> =>
    apiFetch<DailyPlan>(`${V1}/api/daily-plan/${date}`),

  // ── Forecasting ────────────────────────────────────────────────────────────
  runForecast: (date: string): Promise<ForecastRun> =>
    apiFetch<ForecastRun>(`${V1}/forecasts/run?target_date=${date}`, { method: "POST" }),
  getForecasts: (date: string, outletId?: string): Promise<ForecastRun[]> =>
    apiFetch<ForecastRun[]>(
      `${V1}/forecasts?forecast_date=${date}${outletId ? `&outlet_id=${outletId}` : ""}`
    ),
  adjustForecastLine: (runId: number, lineId: number, pct: number): Promise<unknown> =>
    apiFetch(`${V1}/forecasts/${runId}/lines/${lineId}`, {
      method: "PATCH",
      body: JSON.stringify({ adjustment_pct: pct }),
    }),

  // ── Prep plan ──────────────────────────────────────────────────────────────
  runPrepPlan: (date: string): Promise<PrepPlan> =>
    apiFetch<PrepPlan>(`${V1}/plans/prep/run?target_date=${date}`, { method: "POST" }),
  editPrepLine: (planId: number, lineId: number, editedUnits: number): Promise<unknown> =>
    apiFetch(`${V1}/plans/prep/${planId}/lines/${lineId}`, {
      method: "PATCH",
      body: JSON.stringify({ edited_units: editedUnits }),
    }),
  approvePrepPlan: (planId: number, approvedBy: string): Promise<PrepPlan> =>
    apiFetch<PrepPlan>(`${V1}/plans/prep/${planId}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  // ── Replenishment ──────────────────────────────────────────────────────────
  runReplenishment: (date: string): Promise<ReplenishmentPlan> =>
    apiFetch<ReplenishmentPlan>(`${V1}/plans/replenishment/run?target_date=${date}`, {
      method: "POST",
    }),

  // ── Alerts ─────────────────────────────────────────────────────────────────
  wasteAlerts:    (date: string): Promise<WasteAlert[]>    =>
    apiFetch<WasteAlert[]>(`${V1}/alerts/waste?target_date=${date}`),
  stockoutAlerts: (date: string): Promise<StockoutAlert[]> =>
    apiFetch<StockoutAlert[]>(`${V1}/alerts/stockout?target_date=${date}`),

  // ── Copilot ────────────────────────────────────────────────────────────────
  explainPlan: (body: { context_type: string; line_id?: number }): Promise<{ explanation: string }> =>
    apiFetch<{ explanation: string }>(`${V1}/copilot/explain-plan`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dailyBrief: (date: string): Promise<{ brief: string }> =>
    apiFetch<{ brief: string }>(`${V1}/copilot/daily-brief`, {
      method: "POST",
      body: JSON.stringify({ brief_date: date }),
    }),
  runScenario: (text: string, date: string): Promise<ScenarioResult> =>
    apiFetch<ScenarioResult>(`${V1}/copilot/run-scenario`, {
      method: "POST",
      body: JSON.stringify({ scenario_text: text, target_date: date }),
    }),

  // ── Imports ────────────────────────────────────────────────────────────────
  uploadCSV: (file: File, dataType = "auto"): Promise<ImportResult> => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<ImportResult>(`${V1}/imports/upload?data_type=${dataType}`, {
      method: "POST",
      headers: {},
      body: fd,
    });
  },
};
