import type {
  AgentAction,
  DailyActionsResponse,
  DailyPlan,
  DailyPlanAlert,
  DailyPlanForecastLine,
  ForecastLine,
  ForecastRun,
  Outlet,
  SKU,
} from "@/types";
import type { DailyPlanLatestResponse, DailyPlanTopAction } from "@/lib/api/planning";

type DemoSeverity = "critical" | "high" | "medium" | "low";

interface DemoForecastPayload {
  status: string;
  forecastDate: string;
  summary: {
    rows: number;
    p50_prep_total: number;
    p90_prep_total: number;
    recommended_prep_total: number;
    recommended_expected_cost_total: number;
    p50_expected_cost_total: number;
    cost_saving_vs_p50_total: number;
    cost_saving_vs_p90_total: number;
    recommended_expected_waste_units_total: number;
    recommended_expected_stockout_units_total: number;
  };
  forecastLines: DemoForecastLine[];
}

interface DemoDecisionContextPayload {
  forecastDate: string;
  pipelineSummary: {
    target: string;
    forecastModel: string;
    forecastModelVersion: string;
    forecastRows: number;
    optimizerRows: number;
    p10Total: number;
    p50Total: number;
    p90Total: number;
    recommendedPrepTotal: number;
    expectedCostTotal: number;
    savingVsP50Total: number;
    savingVsP90Total: number;
  };
  modelQuality: {
    validationWape: number;
    validationBias: number;
    wapeImprovementVsBaseline: number;
    bandCoverageP10P90: number;
  };
}

interface DemoForecastLine {
  forecastLineId: string;
  forecastDate: string;
  outlet: { id: string; name: string; type: string };
  sku: { id: string; name: string; category: string };
  daypart: "morning" | "midday" | "evening" | string;
  forecast: { p10: number; p50: number; p90: number; bandLevel: string };
  recommendation: {
    prepQty: number;
    decisionPosture: string;
    expectedCost: number;
    expectedWasteUnits: number;
    expectedStockoutUnits: number;
    savingVsP50Prep: number;
    savingVsP90Prep: number;
    explanation: string;
  };
  context: {
    reasonTags?: string[] | string;
  };
  model: {
    modelVersion: string;
    selectedModelName: string;
  };
}

interface DemoRecommendationPayload {
  status: string;
  forecastDate: string;
  cards: DemoRecommendationCard[];
}

interface DemoRecommendationCard {
  cardType: string;
  severity: DemoSeverity;
  title: string;
  subtitle: string;
  body: string;
  forecastLineId: string;
  metrics: {
    p10?: number;
    p50?: number;
    p90?: number;
    expectedCost?: number;
    expectedWasteUnits?: number;
    expectedStockoutUnits?: number;
    recommendedPrepQty?: number;
    p90PrepQty?: number;
    savingVsP90?: number;
  };
}

async function fetchDemoJson<T>(path: string): Promise<T> {
  const response = await fetch(`/demo-data/${path}`, { cache: "force-cache" });
  if (!response.ok) {
    throw new Error(`Demo data ${response.status}: ${path}`);
  }
  return response.json() as Promise<T>;
}

function numberId(value: string, values: string[]) {
  return values.indexOf(value) + 1;
}

function uniqueSorted<T>(items: T[], key: (item: T) => string) {
  return Array.from(new Map(items.map((item) => [key(item), item])).values()).sort((a, b) =>
    key(a).localeCompare(key(b))
  );
}

function reasonTags(line: DemoForecastLine) {
  const tags = line.context.reasonTags ?? [];
  return Array.isArray(tags) ? tags : tags.split(/\s+/).filter(Boolean);
}

async function loadForecastPayload() {
  return fetchDemoJson<DemoForecastPayload>("forecast_api_response.json");
}

async function loadRecommendationPayload() {
  return fetchDemoJson<DemoRecommendationPayload>("recommendation_cards.json");
}

async function loadDecisionContextPayload() {
  return fetchDemoJson<DemoDecisionContextPayload>("llm_decision_context.json");
}

export async function demoOutlets(): Promise<Outlet[]> {
  const payload = await loadForecastPayload();
  const outlets = uniqueSorted(payload.forecastLines, (line) => line.outlet.id);
  return outlets.map((line, index) => ({
    id: index + 1,
    code: line.outlet.id,
    name: line.outlet.name,
    city: "Kuala Lumpur",
    is_active: true,
  }));
}

export async function demoSkus(): Promise<SKU[]> {
  const payload = await loadForecastPayload();
  const skus = uniqueSorted(payload.forecastLines, (line) => line.sku.id);
  return skus.map((line, index) => ({
    id: index + 1,
    code: line.sku.id,
    sku_id: line.sku.id,
    name: line.sku.name,
    category: line.sku.category,
    price: 0,
    freshness_hours: 24,
    is_bestseller: false,
    safety_buffer_pct: 0.1,
    is_active: true,
  }));
}

export async function demoForecastRuns(outletId?: string): Promise<ForecastRun[]> {
  const payload = await loadForecastPayload();
  const outletCodes = uniqueSorted(payload.forecastLines, (line) => line.outlet.id).map((line) => line.outlet.id);
  const skuCodes = uniqueSorted(payload.forecastLines, (line) => line.sku.id).map((line) => line.sku.id);
  const filtered = payload.forecastLines.filter((line) => {
    if (!outletId) {
      return true;
    }
    return numberId(line.outlet.id, outletCodes) === Number(outletId);
  });
  const groups = new Map<string, ForecastLine>();

  for (const line of filtered) {
    const outlet_id = numberId(line.outlet.id, outletCodes);
    const sku_id = numberId(line.sku.id, skuCodes);
    const key = `${outlet_id}:${sku_id}`;
    const existing =
      groups.get(key) ??
      ({
        id: groups.size + 1,
        outlet_id,
        sku_id,
        morning: 0,
        midday: 0,
        evening: 0,
        total: 0,
        method: line.model.selectedModelName,
        confidence: 0.78,
        manual_adjustment_pct: null,
        rationale_json: { source: "demo-data", bands: {} },
        outlet_name: line.outlet.name,
        sku_name: line.sku.name,
      } satisfies ForecastLine);

    const p50 = line.forecast.p50;
    if (line.daypart === "morning" || line.daypart === "midday" || line.daypart === "evening") {
      existing[line.daypart] = p50;
    }
    existing.total = existing.morning + existing.midday + existing.evening;
    groups.set(key, existing);
  }

  return [
    {
      id: 1,
      forecast_date: payload.forecastDate,
      status: payload.status,
      lines: Array.from(groups.values()),
    },
  ];
}

export async function demoDailyPlan(): Promise<DailyPlan> {
  const payload = await loadForecastPayload();
  const cards = await loadRecommendationPayload();
  const context = await loadDecisionContextPayload();
  const outletCodes = uniqueSorted(payload.forecastLines, (line) => line.outlet.id).map((line) => line.outlet.id);
  const skuCodes = uniqueSorted(payload.forecastLines, (line) => line.sku.id).map((line) => line.sku.id);

  const forecasts: DailyPlanForecastLine[] = payload.forecastLines.map((line) => ({
    outlet_id: numberId(line.outlet.id, outletCodes),
    outlet_name: line.outlet.name,
    sku_id: numberId(line.sku.id, skuCodes),
    sku_name: line.sku.name,
    morning: line.daypart === "morning" ? line.forecast.p50 : 0,
    midday: line.daypart === "midday" ? line.forecast.p50 : 0,
    evening: line.daypart === "evening" ? line.forecast.p50 : 0,
    total: line.forecast.p50,
    reason_tags: reasonTags(line),
  }));

  const highWaste = [...payload.forecastLines]
    .sort((a, b) => b.recommendation.expectedWasteUnits - a.recommendation.expectedWasteUnits)
    .slice(0, 4);
  const highStockout = [...payload.forecastLines]
    .sort((a, b) => b.recommendation.expectedStockoutUnits - a.recommendation.expectedStockoutUnits)
    .slice(0, 4);
  const toAlert = (line: DemoForecastLine, type: "waste" | "stockout"): DailyPlanAlert => ({
    outlet_name: line.outlet.name,
    sku_name: line.sku.name,
    daypart: line.daypart,
    risk_level: line.recommendation.expectedCost > 50 ? "high" : "medium",
    reason:
      type === "waste"
        ? `${line.recommendation.expectedWasteUnits.toFixed(1)} expected waste units.`
        : `${line.recommendation.expectedStockoutUnits.toFixed(1)} expected stockout units.`,
  });

  return {
    date: payload.forecastDate,
    prep_plan_id: null,
    replenishment_plan_id: null,
    forecasts,
    prep_plan: [],
    replenishment_plan: [],
    waste_alerts: highWaste.map((line) => toAlert(line, "waste")),
    stockout_alerts: highStockout.map((line) => toAlert(line, "stockout")),
    summary: {
      total_predicted_sales: context.pipelineSummary.p50Total,
      waste_risk_score: Math.round(payload.summary.recommended_expected_waste_units_total / 5),
      stockout_risk_score: Math.round(payload.summary.recommended_expected_stockout_units_total / 4),
      top_actions: cards.cards.slice(0, 5).map((card) => card.title),
      at_risk_outlets: Array.from(new Set(highStockout.map((line) => line.outlet.name))),
    },
  };
}

export async function demoLatestPlan(): Promise<DailyPlanLatestResponse> {
  const forecastPayload = await loadForecastPayload();
  const recommendationPayload = await loadRecommendationPayload();
  const contextPayload = await loadDecisionContextPayload();
  const lineMap = new Map(forecastPayload.forecastLines.map((line) => [line.forecastLineId, line]));

  const top_actions: DailyPlanTopAction[] = recommendationPayload.cards.slice(0, 12).map((card) => {
    const line = lineMap.get(card.forecastLineId);
    const prep = line?.recommendation.prepQty ?? card.metrics.recommendedPrepQty ?? card.metrics.p50 ?? 0;
    return {
      id: card.forecastLineId,
      outlet_id: line?.outlet.id ?? "demo_outlet",
      outlet_name: line?.outlet.name ?? card.title,
      sku_id: line?.sku.id ?? "demo_sku",
      sku_name: line?.sku.name ?? card.title,
      sku_category: line?.sku.category ?? "Demo",
      daypart: line?.daypart ?? "morning",
      p10: line?.forecast.p10 ?? card.metrics.p10 ?? 0,
      p50: line?.forecast.p50 ?? card.metrics.p50 ?? 0,
      p90: line?.forecast.p90 ?? card.metrics.p90 ?? 0,
      opening_stock: 0,
      recommended_prep: prep,
      batch_size: 5,
      waste_cost: card.metrics.expectedWasteUnits ?? line?.recommendation.expectedWasteUnits ?? 0,
      stockout_cost: card.metrics.expectedStockoutUnits ?? line?.recommendation.expectedStockoutUnits ?? 0,
      financial_exposure: {
        stockout_exposure_rm: Math.round((card.metrics.expectedStockoutUnits ?? 0) * 12),
        waste_exposure_rm: Math.round((card.metrics.expectedWasteUnits ?? 0) * 8),
      },
      reason_summary: card.body,
      replenishment: [],
      status: "pending_approval",
    };
  });

  return {
    forecast_run_id: `demo_${forecastPayload.forecastDate}`,
    model_run_id: "lightgbm_p50_v1",
    model_version: "lightgbm_p50_v1",
    engine_name: "lightgbm_mlops_prototype",
    model_status: "demo_artifact",
    validation_window: "2022-09-01 to 2022-09-30",
    metrics: {
      wape: contextPayload.modelQuality.validationWape,
      bias: contextPayload.modelQuality.validationBias,
      p10_p90_coverage: contextPayload.modelQuality.bandCoverageP10P90,
      estimated_mismatch_cost_delta_pct:
        -contextPayload.pipelineSummary.savingVsP50Total /
        Math.max(forecastPayload.summary.p50_expected_cost_total ?? 1, 1),
    },
    top_actions,
  };
}

export async function demoDailyActions(date: string): Promise<DailyActionsResponse> {
  const recommendations = await loadRecommendationPayload();
  const actions: AgentAction[] = recommendations.cards.slice(0, 5).map((card) => ({
    action_type: "prep",
    action_text: `${card.title}: ${card.subtitle}`,
    urgency: card.severity === "high" ? "high" : "medium",
    estimated_impact: card.metrics.expectedCost
      ? `Expected cost RM ${card.metrics.expectedCost.toFixed(2)}`
      : card.subtitle,
    target: {
      outlet_id: null,
      outlet_name: null,
      sku_id: null,
      sku_name: null,
      ingredient_id: null,
      ingredient_name: null,
    },
    evidence: [card.body],
    source_type: "deterministic",
  }));
  return {
    date,
    brief: "Demo recommendations loaded from the Step 12 artifact bundle.",
    fallback_mode: true,
    top_actions: actions,
    prep_actions: actions,
    reorder_actions: [],
    risk_warnings: [],
    rebalance_suggestions: [],
  };
}
