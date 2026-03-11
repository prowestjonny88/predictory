"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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

      <main className="p-6">
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load prep plan"}
          </div>
        )}

        {plan && (
          <div className="mb-4 flex items-center gap-3">
            <span className="text-sm text-neutral-600">
              Plan status:
            </span>
            <span
              className={cn(
                "rounded-full px-3 py-0.5 text-xs font-semibold capitalize",
                plan.status === "approved"
                  ? "bg-green-100 text-green-700"
                  : "bg-yellow-100 text-yellow-700"
              )}
            >
              {plan.status}
            </span>
            {plan.approved_at && (
              <span className="text-xs text-neutral-400">
                Approved {new Date(plan.approved_at).toLocaleString()}
              </span>
            )}
          </div>
        )}

        <div className="bg-white rounded-xl border border-neutral-200 shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-neutral-50 border-b border-neutral-200 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Daypart</th>
                <th className="px-4 py-3 text-right">Forecast</th>
                <th className="px-4 py-3 text-right">Prep Qty</th>
                <th className="px-4 py-3 text-right">Override</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {isLoading
                ? Array.from({ length: 5 }).map((_, i) => (
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
                      No prep plan. Click "Generate Plan" to create one.
                    </td>
                  </tr>
                )
                : lines.map((line) => (
                  <tr key={line.id} className="hover:bg-neutral-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-neutral-800">
                      {line.sku_name ?? `SKU ${line.sku_id}`}
                    </td>
                    <td className="px-4 py-3 capitalize text-neutral-600">{line.daypart}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{line.forecast_qty}</td>
                    <td className="px-4 py-3 text-right tabular-nums font-semibold">{line.prep_qty}</td>
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
                      {plan && plan.status !== "approved" && edits[line.id] && (
                        <button
                          onClick={() => handleEdit(plan.id, line.id)}
                          disabled={editMutation.isPending}
                          className="text-xs text-amber-600 hover:text-amber-800 font-medium disabled:opacity-50"
                        >
                          Save
                        </button>
                      )}
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
