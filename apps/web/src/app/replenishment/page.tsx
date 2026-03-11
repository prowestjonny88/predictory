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

      <main className="p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load replenishment plan"}
          </div>
        )}

        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                <th className="px-4 py-3">Ingredient</th>
                <th className="px-4 py-3">Outlet</th>
                <th className="px-4 py-3 text-right">Current Stock</th>
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
                    <td colSpan={7} className="px-4 py-10 text-center text-neutral-400">
                      No replenishment data. Click "Run Replenishment" to generate one.
                    </td>
                  </tr>
                )
                : lines.map((line) => (
                  <tr key={line.id} className={cn("hover:bg-neutral-50 transition-colors", line.is_ordered && "opacity-60")}>
                    <td className="px-4 py-3 font-medium text-neutral-800">
                      {line.ingredient_name ?? `Ingredient ${line.ingredient_id}`}
                    </td>
                    <td className="px-4 py-3 text-neutral-600">
                      {line.outlet_name ?? `Outlet ${line.outlet_id}`}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {line.current_stock ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{line.required_qty}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">
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
                          "inline-block h-4 w-4 rounded-full border-2",
                          line.is_ordered
                            ? "bg-green-500 border-green-500"
                            : "bg-white border-neutral-300"
                        )}
                      />
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
