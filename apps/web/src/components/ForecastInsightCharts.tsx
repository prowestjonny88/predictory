"use client";

import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart2, Maximize2, Minimize2 } from "lucide-react";

import type { DailyPlanForecastLine } from "@/types";

interface Props {
  forecasts?: DailyPlanForecastLine[];
  isLoading?: boolean;
}

const COLORS = [
  "#FCD34D", // amber-300
  "#F59E0B", // amber-400
  "#D97706", // amber-500
  "#B45309", // amber-700
  "#92400E", // amber-800
  "#60A5FA", // blue-400
  "#34D399", // emerald-400
  "#F87171", // red-400
  "#A78BFA", // violet-400
  "#FB923C", // orange-400
];

const DAYPART_COLORS = {
  morning: "#FCD34D",
  midday: "#F59E0B",
  evening: "#D97706",
};

// ── Chart 1: Filter by Outlet → bars per SKU ────────────────────────────────

function OutletChart({ forecasts }: { forecasts: DailyPlanForecastLine[] }) {
  const outlets = useMemo(() => {
    const seen = new Map<number, string>();
    for (const f of forecasts) {
      if (!seen.has(f.outlet_id)) {
        seen.set(f.outlet_id, f.outlet_name ?? `Outlet ${f.outlet_id}`);
      }
    }
    return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
  }, [forecasts]);

  const [selectedOutletId, setSelectedOutletId] = useState<number | "all">("all");
  const [expanded, setExpanded] = useState(false);

  const chartData = useMemo(() => {
    const filtered =
      selectedOutletId === "all"
        ? forecasts
        : forecasts.filter((f) => f.outlet_id === selectedOutletId);

    // Group by SKU, sum dayparts
    const bySku = new Map<string, { morning: number; midday: number; evening: number }>();
    for (const f of filtered) {
      const key = f.sku_name ?? `SKU ${f.sku_id}`;
      const existing = bySku.get(key) ?? { morning: 0, midday: 0, evening: 0 };
      existing.morning += f.morning;
      existing.midday += f.midday;
      existing.evening += f.evening;
      bySku.set(key, existing);
    }

    return Array.from(bySku.entries())
      .map(([name, vals]) => ({ name, ...vals, total: vals.morning + vals.midday + vals.evening }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 10);
  }, [forecasts, selectedOutletId]);

  return (
    <div
      className={`flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm transition-all duration-200 ${
        expanded ? "fixed inset-4 z-50 shadow-2xl" : "relative"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
        <BarChart2 className="h-4 w-4 text-amber-500" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-neutral-800">Forecast by Outlet</h3>
          <p className="text-xs text-neutral-400">Predicted demand per SKU, broken down by daypart</p>
        </div>
        {/* Outlet dropdown */}
        <select
          value={selectedOutletId}
          onChange={(e) =>
            setSelectedOutletId(e.target.value === "all" ? "all" : Number(e.target.value))
          }
          className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 focus:outline-none focus:ring-2 focus:ring-amber-400 transition-colors hover:border-amber-300"
        >
          <option value="all">All Outlets</option>
          {outlets.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
        {/* Expand toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition-colors"
          title={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      </div>

      {/* Chart */}
      <div className="flex-1 p-5">
        {chartData.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-sm text-neutral-400">
            No forecast data available
          </div>
        ) : (
          <div className={expanded ? "h-full" : "h-64"}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 30, right: 8, left: 0, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
                <XAxis
                  dataKey="name"
                  angle={-30}
                  textAnchor="end"
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  width={36}
                />
                <Tooltip
                  cursor={{ fill: "#F9FAFB" }}
                  contentStyle={{
                    borderRadius: "10px",
                    border: "1px solid #E5E7EB",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)",
                    fontSize: 12,
                    padding: "8px 12px",
                  }}
                  formatter={(value) => [`${value} units`]}
                />
                <Legend
                  verticalAlign="top"
                  align="right"
                  wrapperStyle={{ fontSize: 10, paddingBottom: 15 }}
                  iconType="circle"
                  iconSize={6}
                />
                <Bar dataKey="morning" name="Morning" stackId="a" fill={DAYPART_COLORS.morning} radius={[0, 0, 0, 0]} />
                <Bar dataKey="midday" name="Midday" stackId="a" fill={DAYPART_COLORS.midday} />
                <Bar dataKey="evening" name="Evening" stackId="a" fill={DAYPART_COLORS.evening} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Click-away overlay for expanded mode */}
      {expanded && (
        <div
          className="fixed inset-0 -z-10 bg-black/30 backdrop-blur-sm"
          onClick={() => setExpanded(false)}
        />
      )}
    </div>
  );
}

// ── Chart 2: Filter by SKU → bars per Outlet ────────────────────────────────

function ItemChart({ forecasts }: { forecasts: DailyPlanForecastLine[] }) {
  const skus = useMemo(() => {
    const seen = new Map<number, string>();
    for (const f of forecasts) {
      if (!seen.has(f.sku_id)) {
        seen.set(f.sku_id, f.sku_name ?? `SKU ${f.sku_id}`);
      }
    }
    return Array.from(seen.entries()).map(([id, name]) => ({ id, name }));
  }, [forecasts]);

  const [selectedSkuId, setSelectedSkuId] = useState<number | "all">("all");
  const [expanded, setExpanded] = useState(false);

  const outletNames = useMemo(() => {
    const names = new Set<string>();
    for (const f of forecasts) {
      names.add(f.outlet_name ?? `Outlet ${f.outlet_id}`);
    }
    return Array.from(names);
  }, [forecasts]);

  const chartData = useMemo(() => {
    const filtered =
      selectedSkuId === "all"
        ? forecasts
        : forecasts.filter((f) => f.sku_id === selectedSkuId);

    // Group by outlet
    const byOutlet = new Map<string, number>();
    for (const f of filtered) {
      const key = f.outlet_name ?? `Outlet ${f.outlet_id}`;
      byOutlet.set(key, (byOutlet.get(key) ?? 0) + f.total);
    }

    return Array.from(byOutlet.entries())
      .map(([name, total]) => ({ name, total: Math.round(total) }))
      .sort((a, b) => b.total - a.total);
  }, [forecasts, selectedSkuId]);

  return (
    <div
      className={`flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm transition-all duration-200 ${
        expanded ? "fixed inset-4 z-50 shadow-2xl" : "relative"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
        <BarChart2 className="h-4 w-4 text-blue-500" />
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-neutral-800">Forecast by Item</h3>
          <p className="text-xs text-neutral-400">Total predicted units per outlet for selected SKU</p>
        </div>
        {/* SKU dropdown */}
        <select
          value={selectedSkuId}
          onChange={(e) =>
            setSelectedSkuId(e.target.value === "all" ? "all" : Number(e.target.value))
          }
          className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 focus:outline-none focus:ring-2 focus:ring-amber-400 transition-colors hover:border-amber-300"
        >
          <option value="all">All Items</option>
          {skus.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {/* Expand toggle */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="rounded-md p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-600 transition-colors"
          title={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      </div>

      {/* Chart */}
      <div className="flex-1 p-5">
        {chartData.length === 0 ? (
          <div className="flex h-48 items-center justify-center text-sm text-neutral-400">
            No forecast data available
          </div>
        ) : (
          <div className={expanded ? "h-full" : "h-64"}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#F3F4F6" />
                <XAxis
                  dataKey="name"
                  angle={-30}
                  textAnchor="end"
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "#9CA3AF" }}
                  width={36}
                />
                <Tooltip
                  cursor={{ fill: "#F9FAFB" }}
                  contentStyle={{
                    borderRadius: "10px",
                    border: "1px solid #E5E7EB",
                    boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)",
                    fontSize: 12,
                    padding: "8px 12px",
                  }}
                  formatter={(value) => [`${value} units`, "Forecast"]}
                />
                <Bar dataKey="total" name="Total Units" radius={[4, 4, 0, 0]} maxBarSize={48}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Click-away overlay for expanded mode */}
      {expanded && (
        <div
          className="fixed inset-0 -z-10 bg-black/30 backdrop-blur-sm"
          onClick={() => setExpanded(false)}
        />
      )}
    </div>
  );
}

// ── Main export ──────────────────────────────────────────────────────────────

export default function ForecastInsightCharts({ forecasts, isLoading }: Props) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {[0, 1].map((i) => (
          <div key={i} className="h-80 animate-pulse rounded-xl border border-neutral-200 bg-neutral-100" />
        ))}
      </div>
    );
  }

  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-neutral-200 bg-white py-12 text-center">
        <BarChart2 className="h-8 w-8 text-neutral-200" />
        <p className="text-sm font-medium text-neutral-400">No forecast data for this date</p>
        <p className="text-xs text-neutral-400">Run a forecast to see the charts below</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <OutletChart forecasts={forecasts} />
      <ItemChart forecasts={forecasts} />
    </div>
  );
}
