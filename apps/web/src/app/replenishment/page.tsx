"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import Header from "@/components/Header";
import { api } from "@/lib/api";
import { cn, todayISO } from "@/lib/utils";
import type { DailyPlan, UrgencyLevel } from "@/types";

const URGENCY_STYLES: Record<UrgencyLevel, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

export default function ReplenishmentPage() {
  const [date, setDate] = useState(todayISO);
  const queryClient = useQueryClient();

  const dailyPlanQuery = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runReplenishment(date),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dailyPlan"] });
    },
  });

  const lines = useMemo(
    () => dailyPlanQuery.data?.replenishment_plan ?? [],
    [dailyPlanQuery.data?.replenishment_plan]
  );
  const urgencyCounts = useMemo(
    () =>
      lines.reduce(
        (counts, line) => {
          counts[line.urgency] = (counts[line.urgency] ?? 0) + 1;
          return counts;
        },
        {} as Partial<Record<UrgencyLevel, number>>
      ),
    [lines]
  );
  const totalReorderQty = useMemo(
    () => lines.reduce((sum, line) => sum + line.reorder_qty, 0),
    [lines]
  );

  return (
    <div className="min-h-screen">
      <Header title="Replenishment" date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="rounded-md bg-amber-500 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-60"
        >
          {runMutation.isPending ? "Running..." : "Run Replenishment"}
        </button>
      </Header>

      <main className="space-y-5 p-6">
        {dailyPlanQuery.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {dailyPlanQuery.error instanceof Error
              ? dailyPlanQuery.error.message
              : "Failed to load replenishment plan"}
          </div>
        )}

        {lines.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            {([
              { key: "critical" as UrgencyLevel, label: "Critical" },
              { key: "high" as UrgencyLevel, label: "High" },
              { key: "medium" as UrgencyLevel, label: "Medium" },
              { key: "low" as UrgencyLevel, label: "Low" },
            ] as const).map(({ key, label }) =>
              urgencyCounts[key] ? (
                <span
                  key={key}
                  className={cn(
                    "rounded-full px-3 py-0.5 text-xs font-semibold",
                    URGENCY_STYLES[key]
                  )}
                >
                  {urgencyCounts[key]} {label}
                </span>
              ) : null
            )}
            <span className="ml-1 text-sm text-neutral-500">
              <span className="font-semibold text-neutral-800">{totalReorderQty.toFixed(1)}</span>{" "}
              total reorder quantity
            </span>
          </div>
        )}

        <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <th className="px-4 py-3">Ingredient</th>
                <th className="px-4 py-3 text-right">Stock On Hand</th>
                <th className="px-4 py-3 text-right">Need Qty</th>
                <th className="px-4 py-3 text-right">Reorder Qty</th>
                <th className="px-4 py-3">Urgency</th>
                <th className="px-4 py-3">Driving SKUs</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {dailyPlanQuery.isLoading ? (
                Array.from({ length: 6 }).map((_, rowIndex) => (
                  <tr key={rowIndex}>
                    {Array.from({ length: 6 }).map((__, cellIndex) => (
                      <td key={cellIndex} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-neutral-100" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : lines.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-neutral-400">
                    No replenishment data.{" "}
                    <button
                      onClick={() => runMutation.mutate()}
                      className="font-medium text-amber-600 hover:text-amber-700"
                    >
                      Run Replenishment
                    </button>{" "}
                    to generate one.
                  </td>
                </tr>
              ) : (
                lines.map((line) => (
                  <tr
                    key={`${line.ingredient_id}-${line.ingredient_name}`}
                    className={cn(
                      "transition-colors hover:bg-neutral-50",
                      line.urgency === "critical" && "bg-red-50/30"
                    )}
                  >
                    <td className="px-4 py-3 font-medium text-neutral-800">{line.ingredient_name}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-neutral-500">
                      {line.stock_on_hand.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-neutral-700">
                      {line.need_qty.toFixed(1)}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-800">
                      {line.reorder_qty.toFixed(1)}
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
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {line.driving_skus.length > 0 ? line.driving_skus.join(", ") : "None"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
