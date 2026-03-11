"use client";

import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Flame, ShoppingCart, AlertTriangle, Lightbulb, TrendingDown } from "lucide-react";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import type { WasteAlert, StockoutAlert } from "@/types";

const RISK_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

function riskBadgeClass(r: string): string {
  switch (r) {
    case "critical": return "bg-red-100 text-red-700 border border-red-200";
    case "high":     return "bg-orange-100 text-orange-700 border border-orange-200";
    case "medium":   return "bg-yellow-100 text-yellow-700 border border-yellow-200";
    case "low":      return "bg-green-100 text-green-700 border border-green-200";
    default:         return "bg-neutral-100 text-neutral-600";
  }
}

function barFill(rate: number): string {
  if (rate >= 25) return "#ef4444";
  if (rate >= 15) return "#f97316";
  if (rate >= 8)  return "#eab308";
  return "#22c55e";
}

function RiskBadge({ risk }: { risk: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${riskBadgeClass(risk)}`}>
      {risk}
    </span>
  );
}

function WasteCard({ alert }: { alert: WasteAlert }) {
  return (
    <div className={`rounded-lg border p-4 space-y-2 ${
      alert.risk_level === "critical" ? "border-red-200 bg-red-50/40" :
      alert.risk_level === "high"     ? "border-orange-200 bg-orange-50/30" :
      "border-neutral-200 bg-white"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-neutral-800 text-sm">{alert.sku_name ?? `SKU ${alert.sku_id}`}</p>
          <p className="text-xs text-neutral-500 mt-0.5">{alert.outlet_name ?? `Outlet ${alert.outlet_id}`}</p>
        </div>
        <RiskBadge risk={alert.risk_level} />
      </div>
      {alert.waste_rate_pct != null && (
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-neutral-200 rounded-full h-1.5">
            <div
              className={`h-1.5 rounded-full ${
                alert.risk_level === "critical" ? "bg-red-500" :
                alert.risk_level === "high"     ? "bg-orange-500" : "bg-yellow-500"
              }`}
              style={{ width: `${Math.min(alert.waste_rate_pct, 100)}%` }}
            />
          </div>
          <span className="text-xs font-semibold tabular-nums text-neutral-600 w-10 text-right">
            {alert.waste_rate_pct.toFixed(1)}%
          </span>
        </div>
      )}
      {alert.reason && <p className="text-xs text-neutral-500 italic leading-snug">{alert.reason}</p>}
      {alert.triggers && alert.triggers.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {alert.triggers.map((t, i) => (
            <span key={i} className="text-xs bg-neutral-100 text-neutral-500 px-1.5 py-0.5 rounded border border-neutral-200">{t}</span>
          ))}
        </div>
      )}
    </div>
  );
}

function StockoutCard({ alert }: { alert: StockoutAlert }) {
  return (
    <div className={`rounded-lg border p-4 space-y-2 ${
      alert.risk_level === "critical" ? "border-red-200 bg-red-50/40" :
      alert.risk_level === "high"     ? "border-orange-200 bg-orange-50/30" :
      "border-neutral-200 bg-white"
    }`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-neutral-800 text-sm">{alert.sku_name ?? `SKU ${alert.sku_id}`}</p>
          <p className="text-xs text-neutral-500 mt-0.5">{alert.outlet_name ?? `Outlet ${alert.outlet_id}`}</p>
        </div>
        <RiskBadge risk={alert.risk_level} />
      </div>
      {alert.coverage_pct != null && (
        <p className="text-xs text-neutral-500 font-medium">
          Coverage: <span className="tabular-nums">{alert.coverage_pct.toFixed(0)}%</span>
        </p>
      )}
      {alert.reason && <p className="text-xs text-neutral-500 italic leading-snug">{alert.reason}</p>}
      {alert.message && alert.message !== alert.reason && (
        <p className="text-xs text-neutral-400 leading-snug">{alert.message}</p>
      )}
    </div>
  );
}

type SummaryColor = "red" | "orange";

function SummaryPill({
  icon, label, value, color, loading,
}: {
  icon: React.ReactNode; label: string; value: number; color: SummaryColor; loading: boolean;
}) {
  const styles: Record<SummaryColor, { bg: string; text: string }> = {
    red:    { bg: "bg-red-50 border-red-200",       text: "text-red-800" },
    orange: { bg: "bg-orange-50 border-orange-200", text: "text-orange-800" },
  };
  const s = styles[color];
  return (
    <div className={`rounded-xl border p-4 flex items-center gap-3 ${s.bg}`}>
      {icon}
      <div>
        {loading ? (
          <div className="h-7 w-8 bg-neutral-200/70 animate-pulse rounded mb-0.5" />
        ) : (
          <p className={`text-2xl font-bold leading-none ${s.text}`}>{value}</p>
        )}
        <p className="text-xs text-neutral-500 mt-1">{label}</p>
      </div>
    </div>
  );
}

export default function RiskCenterPage() {
  const [date, setDate] = useState(todayISO);
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  const { data: wasteAlerts, isLoading: loadingWaste } = useQuery<WasteAlert[]>({
    queryKey: ["wasteAlerts", date],
    queryFn: () => api.wasteAlerts(date),
  });

  const { data: stockoutAlerts, isLoading: loadingStockout } = useQuery<StockoutAlert[]>({
    queryKey: ["stockoutAlerts", date],
    queryFn: () => api.stockoutAlerts(date),
  });

  const sortedWaste = useMemo(
    () => [...(wasteAlerts ?? [])].sort(
      (a, b) => (RISK_ORDER[a.risk_level] ?? 9) - (RISK_ORDER[b.risk_level] ?? 9)
    ),
    [wasteAlerts]
  );

  const sortedStockout = useMemo(
    () => [...(stockoutAlerts ?? [])].sort(
      (a, b) => (RISK_ORDER[a.risk_level] ?? 9) - (RISK_ORDER[b.risk_level] ?? 9)
    ),
    [stockoutAlerts]
  );

  const wasteCounts = useMemo(() => ({
    critical: wasteAlerts?.filter((a) => a.risk_level === "critical").length ?? 0,
    high:     wasteAlerts?.filter((a) => a.risk_level === "high").length ?? 0,
    total:    wasteAlerts?.length ?? 0,
  }), [wasteAlerts]);

  const stockoutCounts = useMemo(() => ({
    critical: stockoutAlerts?.filter((a) => a.risk_level === "critical").length ?? 0,
    high:     stockoutAlerts?.filter((a) => a.risk_level === "high").length ?? 0,
    total:    stockoutAlerts?.length ?? 0,
  }), [stockoutAlerts]);

  const outletImbalanceData = useMemo(() => {
    const byOutlet = new Map<string, { sum: number; count: number }>();
    for (const a of wasteAlerts ?? []) {
      const name = a.outlet_name ?? `Outlet ${a.outlet_id}`;
      const existing = byOutlet.get(name) ?? { sum: 0, count: 0 };
      byOutlet.set(name, {
        sum: existing.sum + (a.waste_rate_pct ?? 0),
        count: existing.count + 1,
      });
    }
    return Array.from(byOutlet.entries())
      .map(([outlet, v]) => ({
        outlet,
        wasteRate: Math.round(v.count > 0 ? v.sum / v.count : 0),
      }))
      .sort((a, b) => b.wasteRate - a.wasteRate);
  }, [wasteAlerts]);

  const suggestedActions = useMemo(() => {
    const actions: { id: string; text: string; priority: "urgent" | "normal" }[] = [];
    for (const a of sortedWaste.slice(0, 4)) {
      const outlet = a.outlet_name ?? `Outlet ${a.outlet_id}`;
      const sku = a.sku_name ?? `SKU ${a.sku_id}`;
      if (a.risk_level === "critical") {
        actions.push({ id: `wc-${a.sku_id}-${a.outlet_id}`, text: `Reduce ${sku} prep at ${outlet} immediately`, priority: "urgent" });
      } else if (a.risk_level === "high") {
        actions.push({ id: `wh-${a.sku_id}-${a.outlet_id}`, text: `Review ${sku} forecast at ${outlet} — ${a.waste_rate_pct?.toFixed(0) ?? "?"}% waste rate`, priority: "normal" });
      }
    }
    for (const a of sortedStockout.slice(0, 4)) {
      const outlet = a.outlet_name ?? `Outlet ${a.outlet_id}`;
      const sku = a.sku_name ?? `SKU ${a.sku_id}`;
      if (a.risk_level === "critical") {
        actions.push({ id: `sc-${a.sku_id}-${a.outlet_id}`, text: `Increase ${sku} morning allocation at ${outlet}`, priority: "urgent" });
      } else if (a.risk_level === "high") {
        actions.push({ id: `sh-${a.sku_id}-${a.outlet_id}`, text: `Monitor ${sku} stock levels at ${outlet}`, priority: "normal" });
      }
    }
    return actions.slice(0, 6);
  }, [sortedWaste, sortedStockout]);

  const loading = loadingWaste || loadingStockout;
  const chartHeight = Math.max(outletImbalanceData.length * 44, 100);

  return (
    <div className="min-h-screen">
      <Header title="Risk & Waste Centre" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="p-6 space-y-6">
        {/* Summary pills */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <SummaryPill icon={<Flame className="h-4 w-4 text-red-500" />}       label="Critical Waste"    value={wasteCounts.critical}    color="red"    loading={loading} />
          <SummaryPill icon={<Flame className="h-4 w-4 text-orange-400" />}    label="High Waste"        value={wasteCounts.high}        color="orange" loading={loading} />
          <SummaryPill icon={<ShoppingCart className="h-4 w-4 text-red-500" />}    label="Critical Stockout" value={stockoutCounts.critical} color="red"    loading={loading} />
          <SummaryPill icon={<ShoppingCart className="h-4 w-4 text-orange-400" />} label="High Stockout"     value={stockoutCounts.high}    color="orange" loading={loading} />
        </div>

        {/* Waste + Stockout side by side */}
        <div className="grid grid-cols-2 gap-6">
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Flame className="h-4 w-4 text-orange-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Waste Hotspots</h2>
              {wasteCounts.total > 0 && (
                <span className="ml-auto text-xs text-neutral-400">{wasteCounts.total} alert{wasteCounts.total !== 1 && "s"}</span>
              )}
            </div>
            <div className="space-y-3">
              {loading
                ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 rounded-lg bg-neutral-100 animate-pulse" />)
                : sortedWaste.length === 0
                ? <p className="text-sm text-neutral-400 py-8 text-center">No waste alerts today 🎉</p>
                : sortedWaste.map((a, i) => <WasteCard key={`${a.sku_id}-${a.outlet_id}-${i}`} alert={a} />)}
            </div>
          </section>

          <section>
            <div className="flex items-center gap-2 mb-3">
              <ShoppingCart className="h-4 w-4 text-sky-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Stockout Alerts</h2>
              {stockoutCounts.total > 0 && (
                <span className="ml-auto text-xs text-neutral-400">{stockoutCounts.total} alert{stockoutCounts.total !== 1 && "s"}</span>
              )}
            </div>
            <div className="space-y-3">
              {loading
                ? Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-24 rounded-lg bg-neutral-100 animate-pulse" />)
                : sortedStockout.length === 0
                ? <p className="text-sm text-neutral-400 py-8 text-center">No stockout alerts today 🎉</p>
                : sortedStockout.map((a, i) => <StockoutCard key={`${a.sku_id}-${a.outlet_id}-${i}`} alert={a} />)}
            </div>
          </section>
        </div>

        {/* Outlet Imbalance Chart + Suggested Actions */}
        <div className="grid grid-cols-5 gap-6">
          <section className="col-span-3 bg-white rounded-xl border border-neutral-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingDown className="h-4 w-4 text-neutral-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Outlet Waste Imbalance</h2>
              <span className="ml-auto text-xs text-neutral-400">Avg waste rate %</span>
            </div>
            {loading ? (
              <div className="h-40 bg-neutral-100 animate-pulse rounded" />
            ) : outletImbalanceData.length === 0 ? (
              <p className="text-sm text-neutral-400 text-center py-10">No outlet data available</p>
            ) : mounted ? (
              <ResponsiveContainer width="100%" height={chartHeight}>
                <BarChart data={outletImbalanceData} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f3f4f6" />
                  <XAxis type="number" tick={{ fontSize: 10, fill: "#9ca3af" }} tickFormatter={(v) => `${v}%`} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="outlet" tick={{ fontSize: 11, fill: "#4b5563" }} width={100} axisLine={false} tickLine={false} />
                  <RechartsTooltip
                    formatter={(v) => [v != null ? `${v}%` : "N/A", "Avg Waste Rate"]}
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb", boxShadow: "0 1px 4px rgba(0,0,0,0.08)" }}
                  />
                  <Bar dataKey="wasteRate" radius={[0, 4, 4, 0]} barSize={22}>
                    {outletImbalanceData.map((entry, i) => (
                      <Cell key={i} fill={barFill(entry.wasteRate)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : null}
          </section>

          <section className="col-span-2 bg-white rounded-xl border border-neutral-200 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-4">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">Suggested Actions</h2>
            </div>
            {suggestedActions.length === 0 ? (
              <p className="text-sm text-neutral-400 text-center py-8">All clear — no actions needed!</p>
            ) : (
              <ul className="space-y-3">
                {suggestedActions.map((action) => (
                  <li key={action.id} className="flex gap-3 items-start">
                    <span className={`mt-0.5 flex-none h-5 w-5 rounded-full flex items-center justify-center ${
                      action.priority === "urgent" ? "bg-red-100" : "bg-amber-100"
                    }`}>
                      <AlertTriangle className={`h-3 w-3 ${action.priority === "urgent" ? "text-red-600" : "text-amber-600"}`} />
                    </span>
                    <p className="text-sm text-neutral-700 leading-snug">{action.text}</p>
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
