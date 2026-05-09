"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  AlertTriangle,
  Flame,
  Lightbulb,
  PackageX,
  ShoppingCart,
  TrendingDown,
} from "lucide-react";

import Header from "@/components/Header";
import ExplainButton from "@/components/copilot/ExplainButton";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import { translateDaypart, translateRiskLevel } from "@/lib/i18n";
import { todayISO } from "@/lib/utils";
import type { ProductionConstraintAlert, StockoutAlert, WasteAlert } from "@/types";

const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
type RiskFilter = "priority" | "all" | "waste" | "stockout" | "production";
const PRIORITY_RISK_LEVELS = new Set(["critical", "high"]);

function riskBadgeClass(risk: string): string {
  switch (risk) {
    case "critical":
      return "border border-red-200 bg-red-100 text-red-700";
    case "high":
      return "border border-orange-200 bg-orange-100 text-orange-700";
    case "medium":
      return "border border-yellow-200 bg-yellow-100 text-yellow-700";
    case "low":
      return "border border-green-200 bg-green-100 text-green-700";
    default:
      return "bg-neutral-100 text-neutral-600";
  }
}

function barFill(rate: number): string {
  if (rate >= 25) {
    return "#ef4444";
  }
  if (rate >= 15) {
    return "#f97316";
  }
  if (rate >= 8) {
    return "#eab308";
  }
  return "#22c55e";
}

function parseNumberFromReason(reason: string, pattern: RegExp): number | null {
  const match = reason.match(pattern);
  if (!match?.[1]) {
    return null;
  }
  const value = Number(match[1]);
  return Number.isFinite(value) ? value : null;
}

function humanizeWasteTrigger(
  trigger: string,
  t: (key: string, fallback: string, values?: Record<string, string | number>) => string
): string {
  const planned = parseNumberFromReason(trigger, /Prep \(([\d.]+)\)/);
  const ceiling = parseNumberFromReason(trigger, /batch ceiling \(([\d.]+)\)/);
  if (planned != null && ceiling != null) {
    return t("risk.triggerTooMuchPrep", "Over safe prep limit", {
      planned,
      ceiling,
    });
  }
  const wasteRate = parseNumberFromReason(trigger, /waste rate ([\d.]+)%/i);
  if (wasteRate != null) {
    return t("risk.triggerRecentWaste", "Recent waste above limit", { rate: wasteRate });
  }
  return trigger;
}

function RiskBadge({ risk }: { risk: string }) {
  const { language } = useLanguage();

  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${riskBadgeClass(risk)}`}
    >
      {translateRiskLevel(language, risk)}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-neutral-100 bg-white/70 px-2 py-1">
      <p className="text-[11px] font-medium text-neutral-400">{label}</p>
      <p className="mt-0.5 font-semibold tabular-nums text-neutral-800">{value}</p>
    </div>
  );
}

function WasteCard({ alert }: { alert: WasteAlert }) {
  const { language, t } = useLanguage();
  const wasteRatePct = alert.waste_rate * 100;
  const nextStep = t("risk.nextStepWaste", "Cut back this prep batch before approval, then watch sell-through during service.");
  const plannedPrep = parseNumberFromReason(alert.reason, /Prep \(([\d.]+)\)/);
  const safeCeiling = parseNumberFromReason(alert.reason, /batch ceiling \(([\d.]+)\)/);

  return (
    <div
      className={`space-y-2 rounded-lg border p-4 ${
        alert.risk_level === "critical"
          ? "border-red-200 bg-red-50/40"
          : alert.risk_level === "high"
            ? "border-orange-200 bg-orange-50/30"
            : "border-neutral-200 bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-800">{alert.sku_name}</p>
          <p className="mt-0.5 text-xs text-neutral-500">{alert.outlet_name}</p>
        </div>
        <RiskBadge risk={alert.risk_level} />
      </div>
      <div className="flex items-center justify-between text-xs font-medium text-neutral-500">
        <span>{t("risk.wasteLevel", "Waste level")}</span>
        <span className="tabular-nums">{wasteRatePct.toFixed(1)}%</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-neutral-200">
          <div
            className={`h-1.5 rounded-full ${
              alert.risk_level === "critical"
                ? "bg-red-500"
                : alert.risk_level === "high"
                  ? "bg-orange-500"
                  : "bg-yellow-500"
            }`}
            style={{ width: `${Math.min(wasteRatePct, 100)}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-neutral-600">
        <Metric label={t("risk.plannedPrep", "Planned prep")} value={plannedPrep ?? "-"} />
        <Metric label={t("risk.safePrepLimit", "Safe prep limit")} value={safeCeiling ?? "-"} />
        <Metric
          label={t("risk.reduceBy", "Reduce by")}
          value={alert.excess_prep_units > 0 ? alert.excess_prep_units.toFixed(0) : "-"}
        />
      </div>
      <p className="text-xs text-neutral-400">
        {t("common.daypart", "Daypart")}: {translateDaypart(language, alert.daypart)}
      </p>
      <div className="rounded-md border border-neutral-100 bg-white/70 p-2 text-xs text-neutral-600">
        <span className="font-semibold">{t("risk.nextStep", "Next step")}: </span>
        {nextStep}
      </div>
      {alert.triggers.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {alert.triggers.map((trigger) => (
            <span
              key={`${alert.outlet_id}-${alert.sku_id}-${trigger}`}
              className="rounded border border-neutral-200 bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-500"
            >
              {humanizeWasteTrigger(trigger, t)}
            </span>
          ))}
        </div>
      )}
      <ExplainButton
        label={t("risk.explainAlert", "Explain alert")}
        title={t("risk.explainWasteTitle", "Waste risk explanation")}
        contextType="waste"
        evidence={{
          outlet_id: alert.outlet_id,
          outlet_name: alert.outlet_name,
          sku_id: alert.sku_id,
          sku_name: alert.sku_name,
          daypart: alert.daypart,
          risk_level: alert.risk_level,
          waste_rate_pct: wasteRatePct,
          excess_prep_units: alert.excess_prep_units,
          triggers: alert.triggers,
          reason: alert.reason,
          suggested_action: nextStep,
          source: "backend_waste_alert",
        }}
      />
    </div>
  );
}

function StockoutCard({ alert }: { alert: StockoutAlert }) {
  const { language, t } = useLanguage();
  const nextStep = t("risk.nextStepStockout", "Add stock or move units to this outlet before morning service.");
  const available = parseNumberFromReason(alert.reason, /stock \(([\d.]+)\)/i);
  const forecast = parseNumberFromReason(alert.reason, /forecast \(([\d.]+)\)/i);

  return (
    <div
      className={`space-y-2 rounded-lg border p-4 ${
        alert.risk_level === "critical"
          ? "border-red-200 bg-red-50/40"
          : alert.risk_level === "high"
            ? "border-orange-200 bg-orange-50/30"
            : "border-neutral-200 bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-800">{alert.sku_name}</p>
          <p className="mt-0.5 text-xs text-neutral-500">{alert.outlet_name}</p>
        </div>
        <RiskBadge risk={alert.risk_level} />
      </div>
      <div className="flex items-center justify-between text-xs font-medium text-neutral-500">
        <span>{t("risk.enoughFor", "Enough for")}</span>
        <span className="tabular-nums">{alert.coverage_pct.toFixed(0)}%</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-neutral-200">
          <div
            className={`h-1.5 rounded-full ${
              alert.risk_level === "critical"
                ? "bg-red-500"
                : alert.risk_level === "high"
                  ? "bg-orange-500"
                  : "bg-yellow-500"
            }`}
            style={{ width: `${Math.min(alert.coverage_pct, 100)}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-neutral-600">
        <Metric label={t("risk.readyStock", "Ready stock")} value={available ?? "-"} />
        <Metric label={t("risk.expectedSales", "Expected sales")} value={forecast ?? "-"} />
        <Metric label={t("risk.shortBy", "Short by")} value={alert.shortage_qty.toFixed(1)} />
      </div>
      <p className="text-xs text-neutral-400">
        {t("common.daypart", "Daypart")}: {translateDaypart(language, alert.affected_daypart)} |{" "}
        {t("risk.needMoreStock", "Needs more stock before service")}
      </p>
      <div className="rounded-md border border-neutral-100 bg-white/70 p-2 text-xs text-neutral-600">
        <span className="font-semibold">{t("risk.nextStep", "Next step")}: </span>
        {nextStep}
      </div>
      <ExplainButton
        label={t("risk.explainAlert", "Explain alert")}
        title={t("risk.explainStockoutTitle", "Stockout risk explanation")}
        contextType="stockout"
        evidence={{
          outlet_id: alert.outlet_id,
          outlet_name: alert.outlet_name,
          sku_id: alert.sku_id,
          sku_name: alert.sku_name,
          daypart: alert.affected_daypart,
          risk_level: alert.risk_level,
          shortage_qty: alert.shortage_qty,
          coverage_pct: alert.coverage_pct,
          reason: alert.reason,
          suggested_action: nextStep,
          source: "backend_stockout_alert",
        }}
      />
    </div>
  );
}

function ProductionConstraintCard({ alert }: { alert: ProductionConstraintAlert }) {
  const { t } = useLanguage();
  const nextStep = t(
    "risk.nextStepProduction",
    "Reorder this ingredient or reduce the affected prep plan before approval."
  );

  return (
    <div
      className={`space-y-2 rounded-lg border p-4 ${
        alert.urgency === "critical"
          ? "border-red-200 bg-red-50/40"
          : alert.urgency === "high"
            ? "border-orange-200 bg-orange-50/30"
            : "border-neutral-200 bg-white"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-neutral-800">{alert.ingredient_name}</p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {t("risk.productionConstraint", "Production constraint")}
          </p>
        </div>
        <RiskBadge risk={alert.urgency} />
      </div>
      <div className="flex items-center justify-between text-xs font-medium text-neutral-500">
        <span>{t("risk.enoughFor", "Enough for")}</span>
        <span className="tabular-nums">{alert.coverage_pct.toFixed(0)}%</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="h-1.5 flex-1 rounded-full bg-neutral-200">
          <div
            className={`h-1.5 rounded-full ${
              alert.urgency === "critical"
                ? "bg-red-500"
                : alert.urgency === "high"
                  ? "bg-orange-500"
                  : "bg-yellow-500"
            }`}
            style={{ width: `${Math.min(alert.coverage_pct, 100)}%` }}
          />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-neutral-600">
        <Metric label={t("risk.need", "Need")} value={`${alert.required_qty.toFixed(1)} ${alert.unit}`} />
        <Metric label={t("risk.have", "Have")} value={`${alert.stock_on_hand.toFixed(1)} ${alert.unit}`} />
        <Metric label={t("risk.shortBy", "Short by")} value={`${alert.shortage_qty.toFixed(1)} ${alert.unit}`} />
      </div>
      {alert.driving_skus.length > 0 && (
        <p className="text-xs text-neutral-500">
          <span className="font-semibold">{t("risk.affectedSkus", "Affected SKUs")}: </span>
          {alert.driving_skus.slice(0, 4).join(", ")}
          {alert.driving_skus.length > 4 ? "..." : ""}
        </p>
      )}
      <div className="rounded-md border border-neutral-100 bg-white/70 p-2 text-xs text-neutral-600">
        <span className="font-semibold">{t("risk.nextStep", "Next step")}: </span>
        {nextStep}
      </div>
      <ExplainButton
        label={t("risk.explainAlert", "Explain alert")}
        title={t("risk.explainProductionTitle", "Production constraint explanation")}
        contextType="replenishment"
        evidence={{
          ingredient_id: alert.ingredient_id,
          ingredient_name: alert.ingredient_name,
          required_qty: alert.required_qty,
          stock_on_hand: alert.stock_on_hand,
          shortage_qty: alert.shortage_qty,
          reorder_qty: alert.reorder_qty,
          unit: alert.unit,
          urgency: alert.urgency,
          coverage_pct: alert.coverage_pct,
          driving_skus: alert.driving_skus,
          reason: alert.reason,
          suggested_action: nextStep,
          source: "backend_production_constraint",
        }}
      />
    </div>
  );
}

function SummaryPill({
  icon,
  label,
  value,
  color,
  loading,
}: {
  icon: ReactNode;
  label: string;
  value: number;
  color: "red" | "orange";
  loading: boolean;
}) {
  const styles = {
    red: { bg: "bg-red-50 border-red-200", text: "text-red-800" },
    orange: { bg: "bg-orange-50 border-orange-200", text: "text-orange-800" },
  } as const;
  const selected = styles[color];

  return (
    <div className={`flex items-center gap-3 rounded-xl border p-4 ${selected.bg}`}>
      {icon}
      <div>
        {loading ? (
          <div className="mb-0.5 h-7 w-8 animate-pulse rounded bg-neutral-200/70" />
        ) : (
          <p className={`text-2xl font-bold leading-none ${selected.text}`}>{value}</p>
        )}
        <p className="mt-1 text-xs text-neutral-500">{label}</p>
      </div>
    </div>
  );
}

export default function RiskCenterPage() {
  const [date, setDate] = useState(todayISO);
  const [mounted, setMounted] = useState(false);
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("priority");
  const { language, t } = useLanguage();

  useEffect(() => {
    setMounted(true);
  }, []);

  const wasteQuery = useQuery<WasteAlert[]>({
    queryKey: ["wasteAlerts", date],
    queryFn: () => api.wasteAlerts(date),
    staleTime: 120_000,
    placeholderData: (previous) => previous,
  });

  const stockoutQuery = useQuery<StockoutAlert[]>({
    queryKey: ["stockoutAlerts", date],
    queryFn: () => api.stockoutAlerts(date),
    staleTime: 120_000,
    placeholderData: (previous) => previous,
  });
  const productionQuery = useQuery<ProductionConstraintAlert[]>({
    queryKey: ["productionConstraints", date],
    queryFn: () => api.productionConstraints(date),
    staleTime: 120_000,
    placeholderData: (previous) => previous,
  });

  const wasteAlerts = useMemo(() => wasteQuery.data ?? [], [wasteQuery.data]);
  const stockoutAlerts = useMemo(() => stockoutQuery.data ?? [], [stockoutQuery.data]);
  const productionAlerts = useMemo(() => productionQuery.data ?? [], [productionQuery.data]);
  const loading = wasteQuery.isLoading || stockoutQuery.isLoading || productionQuery.isLoading;

  const sortedWaste = useMemo(
    () =>
      [...wasteAlerts].sort(
        (left, right) => (RISK_ORDER[left.risk_level] ?? 9) - (RISK_ORDER[right.risk_level] ?? 9)
      ),
    [wasteAlerts]
  );

  const sortedStockout = useMemo(
    () =>
      [...stockoutAlerts].sort(
        (left, right) => (RISK_ORDER[left.risk_level] ?? 9) - (RISK_ORDER[right.risk_level] ?? 9)
      ),
    [stockoutAlerts]
  );
  const sortedProduction = useMemo(
    () =>
      [...productionAlerts].sort(
        (left, right) => (RISK_ORDER[left.urgency] ?? 9) - (RISK_ORDER[right.urgency] ?? 9)
      ),
    [productionAlerts]
  );

  const filteredWaste = useMemo(() => {
    if (riskFilter === "stockout" || riskFilter === "production") {
      return [];
    }
    if (riskFilter === "priority") {
      return sortedWaste.filter((alert) => PRIORITY_RISK_LEVELS.has(alert.risk_level));
    }
    return sortedWaste;
  }, [riskFilter, sortedWaste]);

  const filteredStockout = useMemo(() => {
    if (riskFilter === "waste" || riskFilter === "production") {
      return [];
    }
    if (riskFilter === "priority") {
      return sortedStockout.filter((alert) => PRIORITY_RISK_LEVELS.has(alert.risk_level));
    }
    return sortedStockout;
  }, [riskFilter, sortedStockout]);

  const filteredProduction = useMemo(() => {
    if (riskFilter === "waste" || riskFilter === "stockout") {
      return [];
    }
    if (riskFilter === "priority") {
      return sortedProduction.filter((alert) => PRIORITY_RISK_LEVELS.has(alert.urgency));
    }
    return sortedProduction;
  }, [riskFilter, sortedProduction]);

  const wasteCounts = useMemo(
    () => ({
      critical: wasteAlerts.filter((alert) => alert.risk_level === "critical").length,
      high: wasteAlerts.filter((alert) => alert.risk_level === "high").length,
      total: wasteAlerts.length,
    }),
    [wasteAlerts]
  );

  const stockoutCounts = useMemo(
    () => ({
      critical: stockoutAlerts.filter((alert) => alert.risk_level === "critical").length,
      high: stockoutAlerts.filter((alert) => alert.risk_level === "high").length,
      total: stockoutAlerts.length,
    }),
    [stockoutAlerts]
  );
  const productionCounts = useMemo(
    () => ({
      critical: productionAlerts.filter((alert) => alert.urgency === "critical").length,
      high: productionAlerts.filter((alert) => alert.urgency === "high").length,
      total: productionAlerts.length,
    }),
    [productionAlerts]
  );

  const outletImbalanceData = useMemo(() => {
    const byOutlet = new Map<string, { sum: number; count: number }>();

    for (const alert of wasteAlerts) {
      const outletName = alert.outlet_name;
      const existing = byOutlet.get(outletName) ?? { sum: 0, count: 0 };
      byOutlet.set(outletName, {
        sum: existing.sum + alert.waste_rate * 100,
        count: existing.count + 1,
      });
    }

    return Array.from(byOutlet.entries())
      .map(([outlet, value]) => ({
        outlet,
        wasteRate: Math.round(value.count > 0 ? value.sum / value.count : 0),
      }))
      .sort((left, right) => right.wasteRate - left.wasteRate);
  }, [wasteAlerts]);

  const suggestedActions = useMemo(() => {
    const actions: { id: string; text: string; priority: "urgent" | "normal" }[] = [];

    for (const alert of sortedWaste.slice(0, 4)) {
      if (alert.risk_level === "critical") {
        actions.push({
          id: `waste-critical-${alert.outlet_id}-${alert.sku_id}`,
          text: t("risk.action.reduceCriticalWaste", "Reduce {{sku}} prep at {{outlet}} immediately", {
            sku: alert.sku_name,
            outlet: alert.outlet_name,
          }),
          priority: "urgent",
        });
      } else if (alert.risk_level === "high") {
        actions.push({
          id: `waste-high-${alert.outlet_id}-${alert.sku_id}`,
          text: t("risk.action.reviewHighWaste", "Review {{sku}} at {{outlet}} - {{rate}}% waste rate", {
            sku: alert.sku_name,
            outlet: alert.outlet_name,
            rate: (alert.waste_rate * 100).toFixed(0),
          }),
          priority: "normal",
        });
      }
    }

    for (const alert of sortedStockout.slice(0, 4)) {
      if (alert.risk_level === "critical") {
        actions.push({
          id: `stockout-critical-${alert.outlet_id}-${alert.sku_id}`,
          text: t(
            "risk.action.increaseCriticalStockout",
            "Increase {{sku}} allocation at {{outlet}} for {{daypart}}",
            {
              sku: alert.sku_name,
              outlet: alert.outlet_name,
              daypart: translateDaypart(language, alert.affected_daypart),
            }
          ),
          priority: "urgent",
        });
      } else if (alert.risk_level === "high") {
        actions.push({
          id: `stockout-high-${alert.outlet_id}-${alert.sku_id}`,
          text: t(
            "risk.action.monitorHighStockout",
            "Monitor {{sku}} stock at {{outlet}} for {{daypart}}",
            {
              sku: alert.sku_name,
              outlet: alert.outlet_name,
              daypart: translateDaypart(language, alert.affected_daypart),
            }
          ),
          priority: "normal",
        });
      }
    }
    for (const alert of sortedProduction.slice(0, 4)) {
      if (alert.urgency === "critical" || alert.urgency === "high") {
        actions.push({
          id: `production-${alert.urgency}-${alert.ingredient_id}`,
          text: t("risk.action.reorderIngredient", "Reorder {{ingredient}} - {{shortage}} {{unit}} shortage", {
            ingredient: alert.ingredient_name,
            shortage: alert.shortage_qty.toFixed(1),
            unit: alert.unit,
          }),
          priority: alert.urgency === "critical" ? "urgent" : "normal",
        });
      }
    }

    return actions.slice(0, 6);
  }, [language, sortedProduction, sortedStockout, sortedWaste, t]);

  const chartHeight = Math.max(outletImbalanceData.length * 44, 100);

  return (
    <div className="min-h-screen">
      <Header title={t("risk.title", "Risk & Waste Centre")} date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="max-w-7xl space-y-6 p-6">
        {(wasteQuery.error || stockoutQuery.error || productionQuery.error) && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {wasteQuery.error instanceof Error
              ? wasteQuery.error.message
              : stockoutQuery.error instanceof Error
                ? stockoutQuery.error.message
                : productionQuery.error instanceof Error
                  ? productionQuery.error.message
                : t("risk.failed", "Failed to load risk alerts")}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
          <SummaryPill
            icon={<Flame className="h-4 w-4 text-red-500" />}
            label={t("risk.criticalWaste", "Critical Waste")}
            value={wasteCounts.critical}
            color="red"
            loading={loading}
          />
          <SummaryPill
            icon={<Flame className="h-4 w-4 text-orange-400" />}
            label={t("risk.highWaste", "High Waste")}
            value={wasteCounts.high}
            color="orange"
            loading={loading}
          />
          <SummaryPill
            icon={<ShoppingCart className="h-4 w-4 text-red-500" />}
            label={t("risk.criticalStockout", "Critical Stockout")}
            value={stockoutCounts.critical}
            color="red"
            loading={loading}
          />
          <SummaryPill
            icon={<ShoppingCart className="h-4 w-4 text-orange-400" />}
            label={t("risk.highStockout", "High Stockout")}
            value={stockoutCounts.high}
            color="orange"
            loading={loading}
          />
          <SummaryPill
            icon={<PackageX className="h-4 w-4 text-orange-400" />}
            label={t("risk.productionConstraints", "Production Constraints")}
            value={productionCounts.critical + productionCounts.high}
            color="orange"
            loading={loading}
          />
        </div>

        <div className="flex flex-wrap gap-2 rounded-xl border border-neutral-200 bg-white p-2">
          {([
            ["priority", t("risk.filterPriority", "High/Critical")],
            ["all", t("risk.filterAll", "All")],
            ["waste", t("risk.filterWaste", "Waste")],
            ["stockout", t("risk.filterStockout", "Stockout")],
            ["production", t("risk.filterProduction", "Production")],
          ] as [RiskFilter, string][]).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setRiskFilter(key)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                riskFilter === key
                  ? "bg-amber-100 text-amber-800"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Flame className="h-4 w-4 text-orange-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.wasteHotspots", "Waste Hotspots")}
              </h2>
              {filteredWaste.length > 0 && (
                <span className="ml-auto text-xs text-neutral-400">
                  {filteredWaste.length}{" "}
                  {filteredWaste.length === 1 ? t("common.item", "item") : t("common.items", "items")}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {loading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-lg bg-neutral-100" />
                ))
              ) : filteredWaste.length === 0 ? (
                <p className="py-8 text-center text-sm text-neutral-400">
                  {t("risk.noWasteToday", "No waste alerts today.")}
                </p>
              ) : (
                filteredWaste.map((alert) => (
                  <WasteCard key={`${alert.outlet_id}-${alert.sku_id}-${alert.daypart}`} alert={alert} />
                ))
              )}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-sky-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.stockoutAlerts", "Stockout Alerts")}
              </h2>
              {filteredStockout.length > 0 && (
                <span className="ml-auto text-xs text-neutral-400">
                  {filteredStockout.length}{" "}
                  {filteredStockout.length === 1 ? t("common.item", "item") : t("common.items", "items")}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {loading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-lg bg-neutral-100" />
                ))
              ) : filteredStockout.length === 0 ? (
                <p className="py-8 text-center text-sm text-neutral-400">
                  {t("risk.noStockoutToday", "No stockout alerts today.")}
                </p>
              ) : (
                filteredStockout.map((alert) => (
                  <StockoutCard
                    key={`${alert.outlet_id}-${alert.sku_id}-${alert.affected_daypart}`}
                    alert={alert}
                  />
                ))
              )}
            </div>
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <PackageX className="h-4 w-4 text-amber-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.productionConstraints", "Production Constraints")}
              </h2>
              {filteredProduction.length > 0 && (
                <span className="ml-auto text-xs text-neutral-400">
                  {filteredProduction.length}{" "}
                  {filteredProduction.length === 1 ? t("common.item", "item") : t("common.items", "items")}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {loading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-lg bg-neutral-100" />
                ))
              ) : filteredProduction.length === 0 ? (
                <p className="py-8 text-center text-sm text-neutral-400">
                  {t("risk.noProductionConstraints", "No production constraints today.")}
                </p>
              ) : (
                filteredProduction.map((alert) => (
                  <ProductionConstraintCard key={alert.ingredient_id} alert={alert} />
                ))
              )}
            </div>
          </section>
        </div>

        <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
          <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm xl:col-span-3">
            <div className="mb-4 flex items-center gap-2">
              <TrendingDown className="h-4 w-4 text-neutral-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.outletImbalance", "Outlet Waste Imbalance")}
              </h2>
              <span className="ml-auto text-xs text-neutral-400">
                {t("risk.avgWasteRate", "Avg waste rate %")}
              </span>
            </div>
            {loading ? (
              <div className="h-40 animate-pulse rounded bg-neutral-100" />
            ) : outletImbalanceData.length === 0 ? (
              <p className="py-10 text-center text-sm text-neutral-400">
                {t("risk.noOutletData", "No outlet data available.")}
              </p>
            ) : mounted ? (
              <ResponsiveContainer width="100%" height={chartHeight}>
                <BarChart
                  data={outletImbalanceData}
                  layout="vertical"
                  margin={{ left: 8, right: 40, top: 4, bottom: 4 }}
                >
                  <CartesianGrid stroke="#f3f4f6" strokeDasharray="3 3" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 10, fill: "#9ca3af" }}
                    tickFormatter={(value) => `${value}%`}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="outlet"
                    tick={{ fontSize: 11, fill: "#4b5563" }}
                    width={110}
                    axisLine={false}
                    tickLine={false}
                  />
                  <RechartsTooltip
                    formatter={(value) => [`${value}%`, t("risk.avgWasteRateTooltip", "Avg Waste Rate")]}
                    contentStyle={{
                      fontSize: 12,
                      borderRadius: 8,
                      border: "1px solid #e5e7eb",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                    }}
                  />
                  <Bar dataKey="wasteRate" radius={[0, 4, 4, 0]} barSize={22}>
                    {outletImbalanceData.map((entry) => (
                      <Cell key={entry.outlet} fill={barFill(entry.wasteRate)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : null}
          </section>

          <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm xl:col-span-2">
            <div className="mb-4 flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.suggestedActions", "Suggested Actions")}
              </h2>
            </div>
            {suggestedActions.length === 0 ? (
              <p className="py-8 text-center text-sm text-neutral-400">
                {t("risk.allClear", "All clear. No actions needed.")}
              </p>
            ) : (
              <ul className="space-y-3">
                {suggestedActions.map((action) => (
                  <li key={action.id} className="flex items-start gap-3">
                    <span
                      className={`mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full ${
                        action.priority === "urgent" ? "bg-red-100" : "bg-amber-100"
                      }`}
                    >
                      <AlertTriangle
                        className={`h-3 w-3 ${
                          action.priority === "urgent" ? "text-red-600" : "text-amber-600"
                        }`}
                      />
                    </span>
                    <p className="text-sm leading-snug text-neutral-700">{action.text}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
