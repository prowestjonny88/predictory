"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import type { ForecastRun } from "@/types";

const DAYPART_LABELS: Record<string, string> = {
  morning:   "Morning",
  afternoon: "Afternoon",
  evening:   "Evening",
};

export default function ForecastPage() {
  const [date, setDate] = useState(todayISO);
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<ForecastRun[]>({
    queryKey: ["forecasts", date],
    queryFn: () => api.getForecasts(date),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runForecast(date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forecasts", date] }),
  });

  const allLines = data?.flatMap((run) =>
    run.lines.map((line) => ({
      ...line,
      outlet_name: run.outlet_name,
      forecast_date: run.forecast_date,
    }))
  ) ?? [];

  return (
    <div className="min-h-screen">
      <Header title="Forecast" date={date}>
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
          {runMutation.isPending ? "Running…" : "Run Forecast"}
        </button>
      </Header>

      <main className="p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load forecasts"}
          </div>
        )}
        {runMutation.error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            Run failed:{" "}
            {runMutation.error instanceof Error
              ? runMutation.error.message
              : "unknown error"}
          </div>
        )}

        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Outlet</th>
                <th className="px-4 py-3">Daypart</th>
                <th className="px-4 py-3 text-right">Predicted</th>
                <th className="px-4 py-3 text-right">Adjusted</th>
                <th className="px-4 py-3 text-right">Δ %</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 6 }).map((__, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-neutral-100 animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : allLines.length === 0
                ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-10 text-center text-neutral-400">
                      No forecast data. Click "Run Forecast" to generate one.
                    </td>
                  </tr>
                )
                : allLines.map((line, i) => (
                  <tr key={i} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-800">
                      {line.sku_name ?? `SKU ${line.sku_id}`}
                    </td>
                    <td className="px-4 py-3 text-neutral-600">{line.outlet_name ?? "—"}</td>
                    <td className="px-4 py-3 text-neutral-600">
                      {DAYPART_LABELS[line.daypart] ?? line.daypart}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">{line.predicted_qty}</td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {line.adjusted_qty ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums">
                      {line.adjustment_pct != null
                        ? `${line.adjustment_pct > 0 ? "+" : ""}${line.adjustment_pct.toFixed(1)}%`
                        : "—"}
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
