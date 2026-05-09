"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { useCurrency } from "@/components/CurrencyProvider";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { planningApi, type ExplainRecommendationResponse } from "@/lib/api/planning";
import type { ExplainContextType } from "@/types";

interface ExplainButtonProps {
  label?: string;
  title?: string;
  contextType: ExplainContextType;
  evidence: Record<string, unknown>;
  recommendationId?: string | number;
  disabled?: boolean;
  variant?: "outline" | "secondary" | "ghost";
  size?: "sm" | "default";
}

export default function ExplainButton({
  label,
  title,
  contextType,
  evidence,
  recommendationId,
  disabled,
  variant = "outline",
  size = "sm",
}: ExplainButtonProps) {
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ExplainRecommendationResponse | null>(null);

  const loadingMessages = [
    t("explain.loadingEvidence", "Reading backend evidence..."),
    t("explain.loadingTradeoff", "Checking prep and risk tradeoff..."),
    t("explain.loadingWriting", "Writing plain-language explanation..."),
  ];

  async function loadExplanation() {
    if (response || loading) return;
    setLoading(true);
    setLoadingStep(0);
    setError(null);
    const timers = [
      window.setTimeout(() => setLoadingStep(1), 900),
      window.setTimeout(() => setLoadingStep(2), 2200),
    ];
    try {
      const payload = recommendationId
        ? await planningApi.explainRecommendation(String(recommendationId), language)
        : await api.explainEvidence({ context_type: contextType, evidence, language });
      setResponse(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("explain.unavailable", "Gemini explanation unavailable."));
    } finally {
      timers.forEach((timer) => window.clearTimeout(timer));
      setLoading(false);
    }
  }

  const visibleEvidence = response?.evidence ?? evidence;

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) void loadExplanation();
      }}
    >
      <SheetTrigger asChild>
        <Button variant={variant} size={size} disabled={disabled}>
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          {label ?? t("explain.button", "Explain")}
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{title ?? t("explain.title", "Gemini explanation")}</SheetTitle>
          <SheetDescription>
            {t(
              "explain.description",
              "Gemini explains the backend evidence shown here. It does not calculate or change these numbers."
            )}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          <div className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700">
            {response?.source_type === "llm_rephrased"
              ? t("explain.sourceGemini", "Source: Gemini explanation")
              : response?.source_type
                ? t("explain.sourceTyped", "Source: {{source}}", {
                    source: formatEvidenceValue(
                      "source",
                      response.source_type,
                      (amount, options) => formatCurrency(amount, language, options),
                      t
                    ),
                  })
                : t("explain.sourcePending", "Source: backend evidence")}
          </div>

          {loading && (
            <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">
              {loadingMessages[loadingStep] ?? loadingMessages[0]}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {response?.explanation && (
            <div className="whitespace-pre-wrap rounded-lg border border-sky-100 bg-sky-50/50 p-4 text-sm leading-relaxed text-neutral-800">
              {response.explanation}
            </div>
          )}

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {t("explain.evidence", "Evidence used")}
            </p>
            <div className="space-y-2">
              {Object.entries(visibleEvidence).map(([key, value]) => (
                <div
                  key={key}
                  className="grid grid-cols-[140px_1fr] gap-3 rounded-md border border-neutral-100 bg-white px-3 py-2 text-xs"
                >
                  <span className="font-medium text-neutral-500">{formatEvidenceKey(key, t)}</span>
                  <span className="break-words text-neutral-800">
                    {formatEvidenceValue(
                      key,
                      value,
                      (amount, options) => formatCurrency(amount, language, options),
                      t
                    )}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function formatEvidenceKey(key: string, t: (key: string, fallback: string) => string): string {
  const labels: Record<string, [string, string]> = {
    metric: ["explain.key.metric", "Metric"],
    value_rm: ["explain.key.amount", "Amount"],
    scope: ["explain.key.scope", "Scope"],
    source: ["explain.key.source", "Source"],
    pending_action_count: ["explain.key.pendingActions", "Actions awaiting review"],
    ingredient_shortage_count: ["explain.key.ingredientShortages", "Ingredient shortages"],
    forecast_run_id: ["explain.key.forecastRun", "Forecast run"],
    outlet_id: ["explain.key.outletId", "Outlet ID"],
    outlet_name: ["explain.key.outlet", "Outlet"],
    sku_id: ["explain.key.skuId", "SKU ID"],
    sku_name: ["explain.key.sku", "SKU"],
    sku_category: ["explain.key.skuCategory", "SKU category"],
    daypart: ["explain.key.daypart", "Daypart"],
    p10: ["explain.key.lowDemand", "Low-demand scenario"],
    p50: ["explain.key.expectedDemand", "Expected-demand scenario"],
    p90: ["explain.key.highDemand", "High-demand scenario"],
    recommended_prep: ["explain.key.recommendedPrep", "Recommended prep"],
    final_prep: ["explain.key.finalPrep", "Final prep"],
    current_stock: ["explain.key.currentStock", "Current stock"],
    opening_stock: ["explain.key.openingStock", "Opening stock"],
    batch_size: ["explain.key.batchSize", "Batch size"],
    waste_cost: ["explain.key.wasteCost", "Waste cost"],
    stockout_cost: ["explain.key.stockoutCost", "Stockout cost"],
    stockout_exposure_rm: ["explain.key.stockoutExposure", "Stockout exposure"],
    waste_exposure_rm: ["explain.key.wasteExposure", "Waste exposure"],
    priority_score: ["explain.key.priorityScore", "Priority score"],
    priority_reason: ["explain.key.priorityReason", "Priority reason"],
    need_qty: ["explain.key.needQuantity", "Need quantity"],
    reorder_qty: ["explain.key.reorderQuantity", "Reorder quantity"],
    urgency: ["explain.key.urgency", "Urgency"],
    driving_skus: ["explain.key.drivingSkus", "Driving SKUs"],
  };
  const label = labels[key];
  return label ? t(label[0], label[1]) : key.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function formatEvidenceValue(
  key: string,
  value: unknown,
  formatMoney: (amount: number, options?: Intl.NumberFormatOptions) => string,
  t: (key: string, fallback: string) => string
): string {
  if (value === null || value === undefined || value === "") return t("common.unavailable", "Unavailable");
  if (value === "full_plan") return t("common.fullPlan", "Full plan");
  if (value === "backend_daily_plan_summary") return t("explain.value.backendDailyPlanSummary", "Backend daily-plan summary");
  if (value === "backend_replenishment_plan") return t("explain.value.backendReplenishmentPlan", "Backend replenishment plan");
  if (value === "backend_replenishment_breakdown") return t("explain.value.backendReplenishmentBreakdown", "Backend replenishment breakdown");
  if (value === "backend_waste_alert") return t("explain.value.backendWasteAlert", "Backend waste alert");
  if (value === "backend_stockout_alert") return t("explain.value.backendStockoutAlert", "Backend stockout alert");
  if (value === "llm_rephrased") return t("common.source.ai", "AI phrased");
  if (value === "rules_based") return t("common.source.rulesBased", "Rules-based");
  if (value === "full_plan_stockout_exposure_rm") return t("explain.value.fullPlanStockoutExposure", "Stockout exposure across the full plan");
  if (value === "full_plan_waste_exposure_rm") return t("explain.value.fullPlanWasteExposure", "Waste exposure across the full plan");
  if (typeof value === "number") {
    if (isMoneyEvidenceKey(key)) {
      return formatMoney(value, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    return Number.isInteger(value) ? String(value) : value.toFixed(2);
  }
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? t("common.yes", "Yes") : t("common.no", "No");
  return JSON.stringify(value);
}

function isMoneyEvidenceKey(key: string): boolean {
  return key === "value_rm" || key.endsWith("_cost") || key.endsWith("_exposure_rm");
}
