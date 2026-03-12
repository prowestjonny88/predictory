"use client";

import { Fragment, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Factory, HelpCircle, X } from "lucide-react";

import Header from "@/components/Header";
import { api } from "@/lib/api";
import { cn, todayISO } from "@/lib/utils";
import type { DailyPlan, Outlet, SKU } from "@/types";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-neutral-100 text-neutral-600",
  accepted: "bg-green-100 text-green-700",
  edited: "bg-blue-100 text-blue-700",
};

export default function PrepPlanPage() {
  const [date, setDate] = useState(todayISO);
  const [edits, setEdits] = useState<Record<number, string>>({});
  const [expandedLines, setExpandedLines] = useState(new Set<number>());
  const [explanations, setExplanations] = useState<
    Record<number, { text: string; loading: boolean; error: boolean }>
  >({});
  const queryClient = useQueryClient();

  const dailyPlanQuery = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const outletsQuery = useQuery<Outlet[]>({
    queryKey: ["outlets"],
    queryFn: api.outlets,
    staleTime: Infinity,
  });

  const skusQuery = useQuery<SKU[]>({
    queryKey: ["skus"],
    queryFn: api.skus,
    staleTime: Infinity,
  });

  const prepPlanId = dailyPlanQuery.data?.prep_plan_id ?? null;
  const prepPlanDetailQuery = useQuery({
    queryKey: ["prepPlanDetail", prepPlanId],
    queryFn: () => api.getPrepPlan(prepPlanId as number),
    enabled: prepPlanId != null,
  });

  const runMutation = useMutation({
    mutationFn: () => api.runPrepPlan(date),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dailyPlan"] });
      await queryClient.invalidateQueries({ queryKey: ["prepPlanDetail"] });
    },
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
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dailyPlan"] });
      await queryClient.invalidateQueries({ queryKey: ["prepPlanDetail"] });
    },
  });

  const approveMutation = useMutation({
    mutationFn: (planId: number) => api.approvePrepPlan(planId, "manager"),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["dailyPlan"] });
      await queryClient.invalidateQueries({ queryKey: ["prepPlanDetail"] });
    },
  });

  const outlets = useMemo(() => outletsQuery.data ?? [], [outletsQuery.data]);
  const skus = useMemo(() => skusQuery.data ?? [], [skusQuery.data]);
  const outletMap = useMemo(
    () => new Map(outlets.map((outlet) => [outlet.id, outlet.name])),
    [outlets]
  );
  const skuMap = useMemo(() => new Map(skus.map((sku) => [sku.id, sku.name])), [skus]);
  const forecastMap = useMemo(
    () =>
      new Map(
        (dailyPlanQuery.data?.forecasts ?? []).map((line) => [`${line.outlet_id}:${line.sku_id}`, line])
      ),
    [dailyPlanQuery.data?.forecasts]
  );
  const lines = useMemo(() => dailyPlanQuery.data?.prep_plan ?? [], [dailyPlanQuery.data?.prep_plan]);

  const totalPrepUnits = useMemo(
    () => lines.reduce((sum, line) => sum + (line.edited_units ?? line.recommended_units), 0),
    [lines]
  );
  const editedCount = useMemo(
    () => lines.filter((line) => line.status === "edited").length,
    [lines]
  );

  const kitchenAllocation = useMemo(() => {
    const bySkuId = new Map<
      number,
      { sku_name: string; morning: number; midday: number; evening: number }
    >();

    for (const line of lines) {
      const entry = bySkuId.get(line.sku_id) ?? {
        sku_name:
          forecastMap.get(`${line.outlet_id}:${line.sku_id}`)?.sku_name ??
          skuMap.get(line.sku_id) ??
          `SKU ${line.sku_id}`,
        morning: 0,
        midday: 0,
        evening: 0,
      };
      const qty = line.edited_units ?? line.recommended_units;
      if (line.daypart === "morning") {
        entry.morning += qty;
      } else if (line.daypart === "midday") {
        entry.midday += qty;
      } else if (line.daypart === "evening") {
        entry.evening += qty;
      }
      bySkuId.set(line.sku_id, entry);
    }

    return Array.from(bySkuId.values())
      .map((value) => ({
        ...value,
        total: value.morning + value.midday + value.evening,
      }))
      .sort((left, right) => right.total - left.total);
  }, [forecastMap, lines, skuMap]);

  async function togglePrepWhy(outletId: number, skuId: number, lineId: number) {
    const next = new Set(expandedLines);
    if (next.has(lineId)) {
      next.delete(lineId);
      setExpandedLines(next);
      return;
    }

    next.add(lineId);
    setExpandedLines(next);
    if (explanations[lineId]) {
      return;
    }

    setExplanations((current) => ({
      ...current,
      [lineId]: { text: "", loading: true, error: false },
    }));

    try {
      const response = await api.explainPlan({
        context_type: "prep",
        outlet_id: outletId,
        sku_id: skuId,
        plan_date: date,
      });
      setExplanations((current) => ({
        ...current,
        [lineId]: { text: response.explanation, loading: false, error: false },
      }));
    } catch (_error) {
      setExplanations((current) => ({
        ...current,
        [lineId]: { text: "", loading: false, error: true },
      }));
    }
  }

  function handleEdit(lineId: number) {
    if (prepPlanId == null) {
      return;
    }

    const raw = edits[lineId];
    const units = parseInt(raw ?? "", 10);
    if (!Number.isNaN(units) && units >= 0) {
      editMutation.mutate(
        { planId: prepPlanId, lineId, units },
        {
          onSuccess: () => {
            setEdits((current) => ({ ...current, [lineId]: "" }));
          },
        }
      );
    }
  }

  function forecastQtyForLine(outletId: number, skuId: number, daypart: string): number {
    const forecastLine = forecastMap.get(`${outletId}:${skuId}`);
    if (!forecastLine) {
      return 0;
    }
    if (daypart === "morning") {
      return forecastLine.morning;
    }
    if (daypart === "midday") {
      return forecastLine.midday;
    }
    if (daypart === "evening") {
      return forecastLine.evening;
    }
    return 0;
  }

  const prepStatus = prepPlanDetailQuery.data?.status ?? "draft";

  return (
    <div className="min-h-screen">
      <Header title="Prep Plan" date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="rounded-md bg-neutral-100 px-4 py-1.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-200 disabled:opacity-60"
        >
          {runMutation.isPending ? "Running..." : "Generate Plan"}
        </button>
        {prepPlanId != null && prepStatus !== "approved" && (
          <button
            onClick={() => approveMutation.mutate(prepPlanId)}
            disabled={approveMutation.isPending}
            className="rounded-md bg-green-600 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-green-700 disabled:opacity-60"
          >
            {approveMutation.isPending ? "Approving..." : "Approve All"}
          </button>
        )}
      </Header>

      <main className="space-y-5 p-6">
        {(dailyPlanQuery.error || prepPlanDetailQuery.error) && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {dailyPlanQuery.error instanceof Error
              ? dailyPlanQuery.error.message
              : prepPlanDetailQuery.error instanceof Error
                ? prepPlanDetailQuery.error.message
                : "Failed to load prep plan"}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-4">
          {prepPlanId != null && (
            <span
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold capitalize",
                prepStatus === "approved"
                  ? "bg-green-100 text-green-700 ring-1 ring-green-200"
                  : "bg-yellow-100 text-yellow-700 ring-1 ring-yellow-200"
              )}
            >
              {prepStatus === "approved" ? "Approved" : "Draft"}
            </span>
          )}
          {prepPlanDetailQuery.data?.approved_by && (
            <span className="text-xs text-neutral-400">
              Approved by {prepPlanDetailQuery.data.approved_by}
            </span>
          )}
          {lines.length > 0 && (
            <>
              <span className="text-sm text-neutral-500">
                <span className="font-semibold text-neutral-800">{totalPrepUnits}</span> total prep
                units
              </span>
              <span className="text-sm text-neutral-500">
                <span className="font-semibold text-neutral-800">{lines.length}</span> SKU/daypart
                lines
              </span>
              {editedCount > 0 && (
                <span className="text-sm font-medium text-blue-600">
                  {editedCount} override{editedCount !== 1 && "s"} applied
                </span>
              )}
            </>
          )}
        </div>

        {kitchenAllocation.length > 0 && (
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Factory className="h-4 w-4 text-neutral-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Central Kitchen Summary
              </h2>
            </div>
            <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                    <th className="px-4 py-2.5">SKU</th>
                    <th className="px-4 py-2.5 text-right">Morning</th>
                    <th className="px-4 py-2.5 text-right">Midday</th>
                    <th className="px-4 py-2.5 text-right">Evening</th>
                    <th className="px-4 py-2.5 text-right text-neutral-700">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {kitchenAllocation.map((row) => (
                    <tr key={row.sku_name} className="hover:bg-neutral-50">
                      <td className="px-4 py-2 font-medium text-neutral-800">{row.sku_name}</td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">
                        {row.morning || "-"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">
                        {row.midday || "-"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums text-neutral-500">
                        {row.evening || "-"}
                      </td>
                      <td className="px-4 py-2 text-right tabular-nums font-bold text-neutral-800">
                        {row.total}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <th className="px-4 py-3">SKU</th>
                <th className="px-4 py-3">Outlet</th>
                <th className="px-4 py-3">Daypart</th>
                <th className="px-4 py-3 text-right">Forecast</th>
                <th className="px-4 py-3 text-right">Recommended</th>
                <th className="px-4 py-3 text-right">Override</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 w-12" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {dailyPlanQuery.isLoading ? (
                Array.from({ length: 6 }).map((_, rowIndex) => (
                  <tr key={rowIndex}>
                    {Array.from({ length: 8 }).map((__, cellIndex) => (
                      <td key={cellIndex} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-neutral-100" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : lines.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-neutral-400">
                    No prep plan yet. Click{" "}
                    <button
                      onClick={() => runMutation.mutate()}
                      className="font-medium text-amber-600 hover:text-amber-700"
                    >
                      Generate Plan
                    </button>{" "}
                    to create one.
                  </td>
                </tr>
              ) : (
                lines.map((line) => {
                  const forecastLine = forecastMap.get(`${line.outlet_id}:${line.sku_id}`);
                  const skuName = forecastLine?.sku_name ?? skuMap.get(line.sku_id) ?? `SKU ${line.sku_id}`;
                  const outletName =
                    forecastLine?.outlet_name ?? outletMap.get(line.outlet_id) ?? `Outlet ${line.outlet_id}`;
                  const forecastQty = forecastQtyForLine(line.outlet_id, line.sku_id, line.daypart);

                  return (
                    <Fragment key={line.id}>
                      <tr
                        className={cn(
                          "transition-colors hover:bg-neutral-50",
                          line.status === "edited" && "bg-blue-50/30"
                        )}
                      >
                        <td className="px-4 py-3 font-medium text-neutral-800">{skuName}</td>
                        <td className="px-4 py-3 text-xs text-neutral-500">{outletName}</td>
                        <td className="px-4 py-3 capitalize text-neutral-600">{line.daypart}</td>
                        <td className="px-4 py-3 text-right tabular-nums text-neutral-500">
                          {forecastQty.toFixed(1)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-800">
                          {line.recommended_units}
                        </td>
                        <td className="px-4 py-3">
                          <input
                            type="number"
                            min={0}
                            placeholder={String(line.edited_units ?? line.recommended_units)}
                            value={edits[line.id] ?? ""}
                            onChange={(event) =>
                              setEdits((current) => ({ ...current, [line.id]: event.target.value }))
                            }
                            disabled={prepStatus === "approved"}
                            className="w-20 rounded border border-neutral-300 px-2 py-1 text-right text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-amber-400 disabled:opacity-40"
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
                            {prepPlanId != null && prepStatus !== "approved" && edits[line.id] && (
                              <button
                                onClick={() => handleEdit(line.id)}
                                disabled={editMutation.isPending}
                                className="text-xs font-medium text-amber-600 hover:text-amber-800 disabled:opacity-50"
                              >
                                Save
                              </button>
                            )}
                            <button
                              onClick={() => togglePrepWhy(line.outlet_id, line.sku_id, line.id)}
                              className={`inline-flex items-center gap-1 text-xs font-medium ${
                                expandedLines.has(line.id)
                                  ? "text-amber-700"
                                  : "text-neutral-400 hover:text-amber-600"
                              }`}
                              title="AI rationale"
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
                          <td colSpan={8} className="border-t border-amber-100 bg-amber-50 px-6 py-3">
                            {explanations[line.id]?.loading ? (
                              <div className="flex items-center gap-2 text-sm text-neutral-500">
                                <div className="h-3 w-3 animate-pulse rounded-full bg-amber-300" />
                                Generating rationale...
                              </div>
                            ) : explanations[line.id]?.error ? (
                              <p className="text-xs italic text-neutral-400">Rationale unavailable.</p>
                            ) : explanations[line.id]?.text ? (
                              <p className="text-sm leading-relaxed text-neutral-700">
                                {explanations[line.id]?.text}
                              </p>
                            ) : null}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );
}
