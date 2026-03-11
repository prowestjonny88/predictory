"use client";

import { useState, useMemo, Fragment } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HelpCircle, X, Factory } from "lucide-react";
import { api } from "@/lib/api";
import { todayISO, cn } from "@/lib/utils";
import Header from "@/components/Header";
import type { DailyPlan, PrepPlanLine } from "@/types";

const STATUS_STYLES: Record<string, string> = {
  pending:  "bg-neutral-100 text-neutral-600",
  accepted: "bg-green-100 text-green-700",
  edited:   "bg-blue-100 text-blue-700",
};

export default function PrepPlanPage() {
  const [date, setDate] = useState(todayISO);
  const [edits, setEdits] = useState<Record<number, string>>({});
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const runMutation = useMutation({
    mutationFn: () => api.runPrepPlan(date),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dailyPlan", date] }),
  });

  const editMutation = useMutation({
    mutationFn: ({
      planId,
      lineId,
      units,
    }: {
      planId: number;
      lineId: number;
      units: number;
    }) => api.editPrepLine(planId, lineId, units),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dailyPlan", date] }),
  });

  const approveMutation = useMutation({
    mutationFn: (planId: number) => api.approvePrepPlan(planId, "manager"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["dailyPlan", date] }),
  });

  const plan = data?.prep_plan;
  const lines: PrepPlanLine[] = plan?.lines ?? [];

  const totalPrepUnits = useMemo(
    () => lines.reduce((s, l) => s + (l.edited_units ?? l.prep_qty), 0),
    [lines]
  );
  const editedCount = useMemo(
    () => lines.filter((l) => l.status === "edited").length,
    [lines]
  );

  const kitchenAllocation = useMemo(() => {
    const bySkuId = new Map<
      number,
      { sku_name: string; morning: number; afternoon: number; evening: number }
    >();
    for (const line of lines) {
      const existing = bySkuId.get(line.sku_id) ?? {
        sku_name: line.sku_name ?? `SKU ${line.sku_id}`,
        morning: 0,
        afternoon: 0,
        evening: 0,
      };
      const qty = line.edited_units ?? line.prep_qty;
      if (line.daypart === "morning") existing.morning += qty;
      else if (line.daypart === "afternoon") existing.afternoon += qty;
      else if (line.daypart === "evening") existing.evening += qty;
      bySkuId.set(line.sku_id, existing);
    }
    return Array.from(bySkuId.values())
      .map((v) => ({ ...v, total: v.morning + v.afternoon + v.evening }))
      .sort((a, b) => b.total - a.total);
  }, [lines]);

  const [expandedLines, setExpandedLines] = useState(new Set<number>());
  const [explanations, setExplanations] = useState<Record<number, { text: string; loading: boolean; error: boolean }>>({});

  function togglePrepWhy(lineId: number) {
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
    api
      .explainPlan({ context_type: "prep_line", line_id: lineId })
      .then((r) => {
        setExplanations((prev) => ({ ...prev, [lineId]: { text: r.explanation, loading: false, error: false } }));
      })
      .catch(() => {
        setExplanations((prev) => ({ ...prev, [lineId]: { text: "", loading: false, error: true } }));
      });
  }

  function handleEdit(planId: number, lineId: number) {
    const raw = edits[lineId];
    const units = parseInt(raw ?? "", 10);
    if (!isNaN(units) && units >= 0) {
      editMutation.mutate({ planId, lineId, units });
    }
  }

  return (
    <div className="min-h-screen">
      <Header title="Prep Plan" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="rounded-md bg-neutral-100 hover:bg-neutral-200 text-neutral-700 px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
        >
          {runMutation.isPending ? "Running…" : "Generate Plan"}
        </button>
        {plan && plan.status === "draft" && (
          <button
            onClick={() => approveMutation.mutate(plan.id)}
            disabled={approveMutation.isPending}
            className="rounded-md bg-green-600 hover:bg-green-700 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
          >
            {approveMutation.isPending ? "Approving…" : "Approve All"}
          </button>
        )}
      </Header>

      <main className="p-6 space-y-5">
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load prep plan"}
          </div>
        )}

        {/* Summary strip */}
        <div className="flex flex-wrap items-center gap-4">
          {plan && (
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold capitalize",
                plan.status === "approved"
                  ? "bg-green-100 text-green-700 ring-1 ring-green-200"
                  : "bg-yellow-100 text-yellow-700 ring-1 ring-yellow-200"
              )}
            >
              {plan.status === "approved" ? "✓ Approved" : "Draft"}
            </span>
          )}
          {plan && plan.approved_at && (
            <span className="text-xs text-neutral-400">
              Approved {new Date(plan.approved_at).toLocaleString()}
            </span>
          )}
          {lines.length > 0 && (
            <>
              <span className="text-sm text-neutral-500">
                <span className="font-semibold text-neutral-800">{totalPrepUnits}</span> total prep units
              </span>
              <span className="text-sm text-neutral-500">
                <span className="font-semibold text-neutral-800">{lines.length}</span> SKU/daypart lines
              </span>
              {editedCount > 0 && (
                <span className="text-sm text-blue-600 font-medium">
                  {editedCount} override{editedCount !== 1 && "s"} applied
                </span>
              )}
            </>
          )}
        </div>

        {/* Central Kitchen Allocation */}
        {kitchenAllocation.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Factory className="h-4 w-4 text-neutral-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                Central Kitchen Summary
              </h2>
            </div>
            <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                    <th className="px-4 py-2.5">SKU</th>
                    <th className="px-4 py-2.5 text-right">Morning</th>
                    <th className="px-4 py-2.5 text-right">Afternoon</th>
                    <th className="px-4 py-2.5 text-right">Evening</th>
                    <th className="px-4 py-2.5 text-right font-bold text-neutral-700">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {kitchenAllocation.map((row) => (
                    <tr key={row.sku_name} className="hover:bg-neutral-50">
                      <td className="px-4 py-2 font-medium text-neutral-800">{row.sku_name}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">{row.morning || "—"}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">{row.afternoon || "—"}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">{row.evening || "—"}</td>
                      <td className="px-4 py-2 text-right tabular-nums font-bold text-neutral-800">{row.total}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Table */}
        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Outlet</th>
                <th className="px-4 py-3">Daypart</th>
                <th className="px-4 py-3 text-right">Forecast</th>
                <th className="px-4 py-3 text-right">Prep Qty</th>
                <th className="px-4 py-3 text-right">Override</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 w-12" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 8 }).map((__, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-neutral-100 animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                : lines.length === 0
                ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-sm text-neutral-400">
                      No prep plan yet — click{" "}
                      <button
                        onClick={() => runMutation.mutate()}
                        className="text-amber-600 hover:text-amber-700 font-medium"
                      >
                        Generate Plan
                      </button>{" "}
                      to create one.
                    </td>
                  </tr>
                )
                : lines.map((line) => (
                  <Fragment key={line.id}>
                    <tr
                      className={cn(
                        "hover:bg-neutral-50 transition-colors",
                        line.status === "edited" && "bg-blue-50/30"
                      )}
                    >
                    <td className="px-4 py-3 font-medium text-neutral-800">
                      {line.sku_name ?? `SKU ${line.sku_id}`}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {plan?.outlet_name ?? `Outlet ${plan?.outlet_id ?? "—"}`}
                    </td>
                    <td className="px-4 py-3 capitalize text-neutral-600">{line.daypart}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-neutral-500">{line.forecast_qty}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-800">{line.prep_qty}</td>
                    <td className="px-4 py-3">
                      <input
                        type="number"
                        min={0}
                        placeholder={String(line.edited_units ?? line.prep_qty)}
                        value={edits[line.id] ?? ""}
                        onChange={(e) =>
                          setEdits((prev) => ({ ...prev, [line.id]: e.target.value }))
                        }
                        disabled={plan?.status === "approved"}
                        className="w-20 rounded border border-neutral-300 px-2 py-1 text-sm text-right tabular-nums focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-40"
                      />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
                          STATUS_STYLES[line.status] ?? "bg-neutral-100 text-neutral-600"
                        )}
                      >
                        {line.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {plan && plan.status !== "approved" && edits[line.id] && (
                          <button
                            onClick={() => handleEdit(plan.id, line.id)}
                            disabled={editMutation.isPending}
                            className="text-xs text-amber-600 hover:text-amber-800 font-medium disabled:opacity-50"
                          >
                            Save
                          </button>
                        )}
                        <button
                          onClick={() => togglePrepWhy(line.id)}
                          title="AI Rationale"
                          className={`inline-flex items-center gap-1 text-xs font-medium transition-colors ${
                            expandedLines.has(line.id)
                              ? "text-amber-700"
                              : "text-neutral-400 hover:text-amber-600"
                          }`}
                        >
                          {expandedLines.has(line.id) ? (
                            <X className="h-3 w-3" />
                          ) : (
                            <HelpCircle className="h-3 w-3" />
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedLines.has(line.id) && (
                    <tr>
                      <td colSpan={8} className="bg-amber-50 px-6 py-3 border-t border-amber-100">
                        {explanations[line.id]?.loading ? (
                          <div className="flex items-center gap-2 text-sm text-neutral-500">
                            <div className="h-3 w-3 rounded-full bg-amber-300 animate-pulse" />
                            Generating rationale…
                          </div>
                        ) : explanations[line.id]?.error ? (
                          <p className="text-xs text-neutral-400 italic">Rationale unavailable.</p>
                        ) : explanations[line.id]?.text ? (
                          <p className="text-sm text-neutral-700 leading-relaxed">
                            {explanations[line.id]?.text}
                          </p>
                        ) : null}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
