"use client";

import { useState, useMemo, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HelpCircle, X } from "lucide-react";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import type { ForecastRun, Outlet } from "@/types";

const DAYPARTS = ["morning", "afternoon", "evening"] as const;
type Daypart = typeof DAYPARTS[number];

const DAYPART_LABELS: Record<Daypart, string> = {
  morning:   "Morning",
  afternoon: "Afternoon",
  evening:   "Evening",
};

const DAYPART_TIMES: Record<Daypart, string> = {
  morning:   "7 am – 11 am",
  afternoon: "11 am – 3 pm",
  evening:   "3 pm – 8 pm",
};

const DAYPART_CARD: Record<Daypart, string> = {
  morning:   "bg-amber-50 border-amber-200",
  afternoon: "bg-sky-50 border-sky-200",
  evening:   "bg-violet-50 border-violet-200",
};

const DAYPART_TEXT: Record<Daypart, string> = {
  morning:   "text-amber-700",
  afternoon: "text-sky-700",
  evening:   "text-violet-700",
};

const DAYPART_BADGE: Record<Daypart, string> = {
  morning:   "bg-amber-100 text-amber-700 border-amber-200",
  afternoon: "bg-sky-100 text-sky-700 border-sky-200",
  evening:   "bg-violet-100 text-violet-700 border-violet-200",
};

export default function ForecastPage() {
  const [date, setDate] = useState(todayISO);
  const [outletId, setOutletId] = useState<string>("all");
  const qc = useQueryClient();

  const { data: outlets } = useQuery<Outlet[]>({
    queryKey: ["outlets"],
    queryFn: api.outlets,
    staleTime: Infinity,
  });

  const { data, isLoading, error } = useQuery<ForecastRun[]>({
    queryKey: ["forecasts", date, outletId],
    queryFn: () =>
      api.getForecasts(date, outletId === "all" ? undefined : outletId),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runForecast(date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["forecasts"] }),
  });

  const allLines = useMemo(
    () =>
      data?.flatMap((run) =>
        run.lines.map((line) => ({ ...line, outlet_name: run.outlet_name }))
      ) ?? [],
    [data]
  );

  const daypartTotals = useMemo(() => {
    const t: Partial<Record<Daypart, number>> = {};
    for (const line of allLines) {
      const dp = line.daypart as Daypart;
      t[dp] = (t[dp] ?? 0) + line.predicted_qty;
    }
    return t;
  }, [allLines]);

  const [expandedLines, setExpandedLines] = useState(new Set<number>());
  const [explanations, setExplanations] = useState<
    Record<number, { text: string; loading: boolean; error: boolean }>
  >({});

  async function toggleWhy(lineId: number) {
    const newSet = new Set(expandedLines);
    if (newSet.has(lineId)) {
      newSet.delete(lineId);
      setExpandedLines(newSet);
      return;
    }
    newSet.add(lineId);
    setExpandedLines(newSet);
    if (explanations[lineId]) return;
    setExplanations((prev) => ({ ...prev, [lineId]: { text: "", loading: true, error: false } }));
    try {
      const r = await api.explainPlan({ context_type: "forecast_line", line_id: lineId });
      setExplanations((prev) => ({ ...prev, [lineId]: { text: r.explanation, loading: false, error: false } }));
    } catch (_err) {
      setExplanations((prev) => ({ ...prev, [lineId]: { text: "", loading: false, error: true } }));
    }
  }

  return (
    <div className="min-h-screen">
      <Header title="Demand Forecast" date={date}>
        <select
          value={outletId}
          onChange={(e) => setOutletId(e.target.value)}
          className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          <option value="all">All Outlets</option>
          {outlets?.map((o) => (
            <option key={o.id} value={String(o.id)}>
              {o.name}
            </option>
          ))}
        </select>
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

      <main className="p-6 space-y-6">
        {/* Errors */}
        {(error || runMutation.error) && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error
              ? error.message
              : runMutation.error instanceof Error
              ? `Run failed: ${runMutation.error.message}`
              : "Failed to load forecast"}
          </div>
        )}

        {/* Daypart summary cards */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Predicted Demand by Daypart
          </h2>
          <div className="grid grid-cols-3 gap-4">
            {DAYPARTS.map((dp) => (
              <div
                key={dp}
                className={`rounded-xl border p-5 ${DAYPART_CARD[dp]}`}
              >
                <p className={`text-xs font-semibold uppercase tracking-wide mb-1 ${DAYPART_TEXT[dp]}`}>
                  {DAYPART_LABELS[dp]}
                </p>
                <p className="text-xs text-neutral-400 mb-3">{DAYPART_TIMES[dp]}</p>
                {isLoading ? (
                  <div className="h-8 w-20 bg-neutral-200/50 animate-pulse rounded" />
                ) : (
                  <p className={`text-3xl font-bold ${DAYPART_TEXT[dp]}`}>
                    {daypartTotals[dp] ?? 0}
                    <span className="text-sm font-normal opacity-60 ml-1">units</span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Detail table */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Line Detail
          </h2>
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
                  <th className="px-4 py-3 w-16" />
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {isLoading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i}>
                        {Array.from({ length: 7 }).map((__, j) => (
                          <td key={j} className="px-4 py-3">
                            <div className="h-4 bg-neutral-100 animate-pulse rounded" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : allLines.length === 0
                  ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-sm text-neutral-400">
                        No forecast data —{" "}
                        <button
                          onClick={() => runMutation.mutate()}
                          className="text-amber-600 hover:text-amber-700 font-medium"
                        >
                          Run Forecast
                        </button>{" "}
                        to generate one.
                      </td>
                    </tr>
                  )
                  : allLines.map((line, i) => {
                      const dp = line.daypart as Daypart;
                      const delta = line.adjustment_pct;
                      const expl = explanations[line.id];
                      const isExpanded = expandedLines.has(line.id);
                      return (
                        <Fragment key={i}>
                          <tr className="hover:bg-neutral-50 transition-colors">
                            <td className="px-4 py-3 font-medium text-neutral-800">
                              {line.sku_name ?? `SKU ${line.sku_id}`}
                            </td>
                            <td className="px-4 py-3 text-neutral-500 text-xs">
                              {line.outlet_name ?? "—"}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${
                                  DAYPART_BADGE[dp] ?? "bg-neutral-100 border-neutral-200 text-neutral-600"
                                }`}
                              >
                                {DAYPART_LABELS[dp] ?? line.daypart}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-800">
                              {line.predicted_qty}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums text-neutral-500">
                              {line.adjusted_qty ?? "—"}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums text-sm">
                              {delta != null ? (
                                <span
                                  className={
                                    delta > 0
                                      ? "text-green-600"
                                      : delta < 0
                                      ? "text-red-500"
                                      : "text-neutral-400"
                                  }
                                >
                                  {delta > 0 ? "+" : ""}
                                  {delta.toFixed(1)}%
                                </span>
                              ) : (
                                <span className="text-neutral-300">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => toggleWhy(line.id)}
                                className={`inline-flex items-center gap-1 text-xs font-medium transition-colors ${
                                  isExpanded
                                    ? "text-amber-700"
                                    : "text-neutral-400 hover:text-amber-600"
                                }`}
                              >
                                {isExpanded ? (
                                  <X className="h-3 w-3" />
                                ) : (
                                  <HelpCircle className="h-3 w-3" />
                                )}
                                {isExpanded ? "Close" : "Why?"}
                              </button>
                            </td>
                          </tr>
                          {isExpanded && (
                            <tr>
                              <td
                                colSpan={7}
                                className="bg-amber-50 px-6 py-3 border-t border-amber-100"
                              >
                                {expl?.loading ? (
                                  <div className="flex items-center gap-2 text-sm text-neutral-500">
                                    <div className="h-3 w-3 rounded-full bg-amber-300 animate-pulse" />
                                    Generating explanation…
                                  </div>
                                ) : expl?.error ? (
                                  <p className="text-xs text-neutral-400 italic">
                                    Explanation unavailable. Try again later.
                                  </p>
                                ) : expl?.text ? (
                                  <p className="text-sm text-neutral-700 leading-relaxed">
                                    {expl.text}
                                  </p>
                                ) : null}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      );
                    })}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
