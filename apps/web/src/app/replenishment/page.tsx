"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO, cn } from "@/lib/utils";
import Header from "@/components/Header";
import type { DailyPlan, UrgencyLevel } from "@/types";

const URGENCY_STYLES: Record<UrgencyLevel, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  medium:   "bg-yellow-100 text-yellow-700",
  low:      "bg-green-100 text-green-700",
};

export default function ReplenishmentPage() {
  const [date, setDate] = useState(todayISO);
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runReplenishment(date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dailyPlan", date] }),
  });

  const plan = data?.replenishment_plan;
  const lines = plan?.lines ?? [];

  const urgencyCounts = lines.reduce(
    (acc, l) => {
      acc[l.urgency] = (acc[l.urgency] ?? 0) + 1;
      return acc;
    },
    {} as Partial<Record<UrgencyLevel, number>>
  );
  const pendingCount = lines.filter((l) => !l.is_ordered).length;

  return (
    <div className="min-h-screen">
      <Header title="Replenishment" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="rounded-md bg-amber-500 hover:bg-amber-600 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
        >
          {runMutation.isPending ? "Running…" : "Run Replenishment"}
        </button>
      </Header>

      <main className="p-6 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load replenishment plan"}
          </div>
        )}

        {/* Urgency summary strip */}
        {lines.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            {([
              { key: "critical" as UrgencyLevel, label: "Critical", cls: URGENCY_STYLES.critical },
              { key: "high"     as UrgencyLevel, label: "High",     cls: URGENCY_STYLES.high },
              { key: "medium"   as UrgencyLevel, label: "Medium",   cls: URGENCY_STYLES.medium },
              { key: "low"      as UrgencyLevel, label: "Low",       cls: URGENCY_STYLES.low },
            ] as const).map(({ key, label, cls }) =>
              urgencyCounts[key] ? (
                <span
                  key={key}
                  className={cn(
                    "rounded-full px-3 py-0.5 text-xs font-semibold",
                    cls
                  )}
                >
                  {urgencyCounts[key]} {label}
                </span>
              ) : null
            )}
            <span className="text-sm text-neutral-500 ml-1">
              <span className="font-semibold text-neutral-800">{pendingCount}</span> items pending order
            </span>
          </div>
        )}

        {/* Table */}
        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                <th className="px-4 py-3">Ingredient</th>
                <th className="px-4 py-3">Outlet</th>
                <th className="px-4 py-3 text-right">On Hand</th>
                <th className="px-4 py-3 text-right">Required</th>
                <th className="px-4 py-3 text-right">Order Qty</th>
                <th className="px-4 py-3">Urgency</th>
                <th className="px-4 py-3 text-center">Ordered</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 7 }).map((__, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-neutral-100 animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : lines.length === 0
                ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-sm text-neutral-400">
                      No replenishment data —{" "}
                      <button
                        onClick={() => runMutation.mutate()}
                        className="text-amber-600 hover:text-amber-700 font-medium"
                      >
                        Run Replenishment
                      </button>{" "}
                      to generate one.
                    </td>
                  </tr>
                )
                : lines.map((line) => (
                  <tr
                    key={line.id}
                    className={cn(
                      "hover:bg-neutral-50 transition-colors",
                      line.is_ordered && "opacity-50",
                      line.urgency === "critical" && !line.is_ordered && "bg-red-50/30"
                    )}
                  >
                    <td className="px-4 py-3 font-medium text-neutral-800">
                      {line.ingredient_name ?? `Ingredient ${line.ingredient_id}`}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {line.outlet_name ?? `Outlet ${line.outlet_id}`}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-neutral-500">
                      {line.current_stock ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{line.required_qty}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-800">
                      {line.order_qty}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
                          URGENCY_STYLES[line.urgency]
                        )}
                      >
                        {line.urgency}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={cn(
                          "inline-flex items-center justify-center h-5 w-5 rounded-full border-2 text-xs",
                          line.is_ordered
                            ? "bg-green-500 border-green-500 text-white"
                            : "bg-white border-neutral-300"
                        )}
                      >
                        {line.is_ordered && "✓"}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
