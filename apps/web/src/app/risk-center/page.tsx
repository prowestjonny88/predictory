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
  ShoppingCart,
  TrendingDown,
} from "lucide-react";

import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import { translateDaypart, translateRiskLevel } from "@/lib/i18n";
import { todayISO } from "@/lib/utils";
import type { StockoutAlert, WasteAlert } from "@/types";

const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

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

function WasteCard({ alert }: { alert: WasteAlert }) {
  const { language, t } = useLanguage();
  const wasteRatePct = alert.waste_rate * 100;

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
        <span className="w-12 text-right text-xs font-semibold tabular-nums text-neutral-600">
          {wasteRatePct.toFixed(1)}%
        </span>
      </div>
      <p className="text-xs italic leading-snug text-neutral-500">{alert.reason}</p>
      <p className="text-xs text-neutral-400">
        {t("common.daypart", "Daypart")}: {translateDaypart(language, alert.daypart)} |{" "}
        {t("risk.excessPrep", "Excess prep")}: {alert.excess_prep_units.toFixed(1)}
      </p>
      {alert.triggers.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {alert.triggers.map((trigger) => (
            <span
              key={`${alert.outlet_id}-${alert.sku_id}-${trigger}`}
              className="rounded border border-neutral-200 bg-neutral-100 px-1.5 py-0.5 text-xs text-neutral-500"
            >
              {trigger}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function StockoutCard({ alert }: { alert: StockoutAlert }) {
  const { language, t } = useLanguage();

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
      <p className="text-xs font-medium text-neutral-500">
        {t("risk.coverage", "Coverage")}:{" "}
        <span className="tabular-nums">{alert.coverage_pct.toFixed(0)}%</span>
      </p>
      <p className="text-xs italic leading-snug text-neutral-500">{alert.reason}</p>
      <p className="text-xs text-neutral-400">
        {t("common.daypart", "Daypart")}: {translateDaypart(language, alert.affected_daypart)} |{" "}
        {t("risk.shortage", "Shortage")}: {alert.shortage_qty.toFixed(1)}
      </p>
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
  const { language, t } = useLanguage();

  useEffect(() => {
    setMounted(true);
  }, []);

  const wasteQuery = useQuery<WasteAlert[]>({
    queryKey: ["wasteAlerts", date],
    queryFn: () => api.wasteAlerts(date),
  });

  const stockoutQuery = useQuery<StockoutAlert[]>({
    queryKey: ["stockoutAlerts", date],
    queryFn: () => api.stockoutAlerts(date),
  });

  const wasteAlerts = useMemo(() => wasteQuery.data ?? [], [wasteQuery.data]);
  const stockoutAlerts = useMemo(() => stockoutQuery.data ?? [], [stockoutQuery.data]);
  const loading = wasteQuery.isLoading || stockoutQuery.isLoading;

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
          text:
            language === "ms"
              ? `Kurangkan prep ${alert.sku_name} di ${alert.outlet_name} dengan segera`
              : language === "zh-CN"
                ? `立即减少 ${alert.outlet_name} 的 ${alert.sku_name} 备货`
                : `Reduce ${alert.sku_name} prep at ${alert.outlet_name} immediately`,
          priority: "urgent",
        });
      } else if (alert.risk_level === "high") {
        actions.push({
          id: `waste-high-${alert.outlet_id}-${alert.sku_id}`,
          text:
            language === "ms"
              ? `Semak ${alert.sku_name} di ${alert.outlet_name} - ${(alert.waste_rate * 100).toFixed(0)}% kadar pembaziran`
              : language === "zh-CN"
                ? `检查 ${alert.outlet_name} 的 ${alert.sku_name} - 浪费率 ${(alert.waste_rate * 100).toFixed(0)}%`
                : `Review ${alert.sku_name} at ${alert.outlet_name} - ${(alert.waste_rate * 100).toFixed(0)}% waste rate`,
          priority: "normal",
        });
      }
    }

    for (const alert of sortedStockout.slice(0, 4)) {
      if (alert.risk_level === "critical") {
        actions.push({
          id: `stockout-critical-${alert.outlet_id}-${alert.sku_id}`,
          text:
            language === "ms"
              ? `Tingkatkan alokasi ${alert.sku_name} di ${alert.outlet_name} untuk ${translateDaypart(language, alert.affected_daypart)}`
              : language === "zh-CN"
                ? `提高 ${alert.outlet_name} 在${translateDaypart(language, alert.affected_daypart)}的 ${alert.sku_name} 配置`
                : `Increase ${alert.sku_name} allocation at ${alert.outlet_name} for ${alert.affected_daypart}`,
          priority: "urgent",
        });
      } else if (alert.risk_level === "high") {
        actions.push({
          id: `stockout-high-${alert.outlet_id}-${alert.sku_id}`,
          text:
            language === "ms"
              ? `Pantau stok ${alert.sku_name} di ${alert.outlet_name} untuk ${translateDaypart(language, alert.affected_daypart)}`
              : language === "zh-CN"
                ? `监控 ${alert.outlet_name} 在${translateDaypart(language, alert.affected_daypart)}的 ${alert.sku_name} 库存`
                : `Monitor ${alert.sku_name} stock at ${alert.outlet_name} for ${alert.affected_daypart}`,
          priority: "normal",
        });
      }
    }

    return actions.slice(0, 6);
  }, [language, sortedStockout, sortedWaste]);

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

      <main className="space-y-6 p-6">
        {(wasteQuery.error || stockoutQuery.error) && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {wasteQuery.error instanceof Error
              ? wasteQuery.error.message
              : stockoutQuery.error instanceof Error
                ? stockoutQuery.error.message
                : t("risk.failed", "Failed to load risk alerts")}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
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
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Flame className="h-4 w-4 text-orange-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("risk.wasteHotspots", "Waste Hotspots")}
              </h2>
              {wasteCounts.total > 0 && (
                <span className="ml-auto text-xs text-neutral-400">
                  {wasteCounts.total}{" "}
                  {wasteCounts.total === 1 ? t("common.item", "item") : t("common.items", "items")}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {loading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-lg bg-neutral-100" />
                ))
              ) : sortedWaste.length === 0 ? (
                <p className="py-8 text-center text-sm text-neutral-400">
                  {t("risk.noWasteToday", "No waste alerts today.")}
                </p>
              ) : (
                sortedWaste.map((alert) => (
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
              {stockoutCounts.total > 0 && (
                <span className="ml-auto text-xs text-neutral-400">
                  {stockoutCounts.total}{" "}
                  {stockoutCounts.total === 1 ? t("common.item", "item") : t("common.items", "items")}
                </span>
              )}
            </div>
            <div className="space-y-3">
              {loading ? (
                Array.from({ length: 3 }).map((_, index) => (
                  <div key={index} className="h-24 animate-pulse rounded-lg bg-neutral-100" />
                ))
              ) : sortedStockout.length === 0 ? (
                <p className="py-8 text-center text-sm text-neutral-400">
                  {t("risk.noStockoutToday", "No stockout alerts today.")}
                </p>
              ) : (
                sortedStockout.map((alert) => (
                  <StockoutCard
                    key={`${alert.outlet_id}-${alert.sku_id}-${alert.affected_daypart}`}
                    alert={alert}
                  />
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
