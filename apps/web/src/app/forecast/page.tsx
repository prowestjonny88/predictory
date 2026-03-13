"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HelpCircle, X } from "lucide-react";

import DemandDriversPanel from "@/components/forecast/DemandDriversPanel";
import ForecastChart from "@/components/ForecastChart";
import OverrideEditor from "@/components/forecast/OverrideEditor";
import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import { translateDaypart } from "@/lib/i18n";
import { todayISO } from "@/lib/utils";
import type {
  ForecastLine,
  ForecastOverride,
  ForecastOverridePayload,
  ForecastRun,
  Outlet,
  SKU,
} from "@/types";

type ForecastDisplayLine = ForecastLine & { run_id: number };

export default function ForecastPage() {
  const [date, setDate] = useState(todayISO);
  const [outletId, setOutletId] = useState<string>("all");
  const [contextSkuId, setContextSkuId] = useState<string>("");
  const [editingOverride, setEditingOverride] = useState<ForecastOverride | null>(null);
  const [expandedLines, setExpandedLines] = useState(new Set<number>());
  const [adjustmentInputs, setAdjustmentInputs] = useState<Record<number, string>>({});
  const [explanations, setExplanations] = useState<
    Record<number, { text: string; loading: boolean; error: boolean }>
  >({});
  const { language, t } = useLanguage();
  const queryClient = useQueryClient();

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

  const forecastsQuery = useQuery<ForecastRun[]>({
    queryKey: ["forecasts", date, outletId],
    queryFn: () => api.getForecasts(date, outletId === "all" ? undefined : outletId),
    staleTime: 30_000,
  });

  const contextQuery = useQuery({
    queryKey: ["forecastContext", date, outletId, contextSkuId],
    queryFn: () =>
      api.getForecastContext(
        date,
        Number(outletId),
        contextSkuId ? Number(contextSkuId) : undefined
      ),
    enabled: outletId !== "all",
  });

  useEffect(() => {
    setContextSkuId("");
    setEditingOverride(null);
    setExpandedLines(new Set());
    setAdjustmentInputs({});
    setExplanations({});
  }, [date, outletId]);

  const outlets = useMemo(() => outletsQuery.data ?? [], [outletsQuery.data]);
  const skus = useMemo(() => skusQuery.data ?? [], [skusQuery.data]);
  const skuMap = useMemo(() => new Map(skus.map((sku) => [sku.id, sku])), [skus]);
  const outletMap = useMemo(
    () => new Map(outlets.map((outlet) => [outlet.id, outlet])),
    [outlets]
  );
  const currentRun = forecastsQuery.data?.[0] ?? null;

  const lines: ForecastDisplayLine[] = useMemo(() => {
    if (!currentRun) {
      return [];
    }

    return currentRun.lines
      .map((line) => {
        const sku = skuMap.get(line.sku_id);
        const outlet = outletMap.get(line.outlet_id);
        return {
          ...line,
          run_id: currentRun.id,
          sku_name: sku?.name ?? line.sku_name,
          outlet_name: outlet?.name ?? line.outlet_name,
        };
      })
      .sort((left, right) => right.total - left.total);
  }, [currentRun, outletMap, skuMap]);

  const selectableSkus = Array.from(
    new Map(
      lines.map((line) => [
        line.sku_id,
        {
          id: line.sku_id,
          code: skuMap.get(line.sku_id)?.code ?? "",
          name: skuMap.get(line.sku_id)?.name ?? line.sku_name ?? `SKU ${line.sku_id}`,
          category: skuMap.get(line.sku_id)?.category ?? "",
          price: skuMap.get(line.sku_id)?.price ?? 0,
          freshness_hours: skuMap.get(line.sku_id)?.freshness_hours ?? 0,
          is_bestseller: skuMap.get(line.sku_id)?.is_bestseller ?? false,
          safety_buffer_pct: skuMap.get(line.sku_id)?.safety_buffer_pct ?? 0,
          is_active: skuMap.get(line.sku_id)?.is_active ?? true,
        },
      ])
    ).values()
  );

  const daypartTotals = useMemo(() => {
    const totals = { morning: 0, midday: 0, evening: 0 };
    for (const line of lines) {
      totals.morning += line.morning;
      totals.midday += line.midday;
      totals.evening += line.evening;
    }
    return totals;
  }, [lines]);

  const selectedOutlet =
    outletId === "all" ? null : outlets.find((outlet) => String(outlet.id) === outletId) ?? null;

  async function invalidateForecastViews() {
    await queryClient.invalidateQueries({ queryKey: ["forecasts"] });
    await queryClient.invalidateQueries({ queryKey: ["forecastContext"] });
    await queryClient.invalidateQueries({ queryKey: ["dailyPlan"] });
  }

  async function refreshForecastViews() {
    await api.runForecast(date);
    await invalidateForecastViews();
  }

  const runMutation = useMutation({
    mutationFn: () => api.runForecast(date),
    onSuccess: invalidateForecastViews,
  });

  const adjustMutation = useMutation({
    mutationFn: ({
      runId,
      lineId,
      pct,
    }: {
      runId: number;
      lineId: number;
      pct: number;
    }) => api.adjustForecastLine(runId, lineId, pct),
    onSuccess: invalidateForecastViews,
  });

  const createOverrideMutation = useMutation({
    mutationFn: api.createForecastOverride,
    onSuccess: async () => {
      setEditingOverride(null);
      await refreshForecastViews();
    },
  });

  const updateOverrideMutation = useMutation({
    mutationFn: ({
      overrideId,
      payload,
    }: {
      overrideId: number;
      payload: Parameters<typeof api.updateForecastOverride>[1];
    }) => api.updateForecastOverride(overrideId, payload),
    onSuccess: async () => {
      setEditingOverride(null);
      await refreshForecastViews();
    },
  });

  const deleteOverrideMutation = useMutation({
    mutationFn: (overrideId: number) => api.deleteForecastOverride(overrideId),
    onSuccess: async () => {
      if (editingOverride) {
        setEditingOverride(null);
      }
      await refreshForecastViews();
    },
  });

  async function toggleWhy(line: ForecastDisplayLine) {
    const next = new Set(expandedLines);
    if (next.has(line.id)) {
      next.delete(line.id);
      setExpandedLines(next);
      return;
    }

    next.add(line.id);
    setExpandedLines(next);
    if (explanations[line.id]) {
      return;
    }

    setExplanations((current) => ({
      ...current,
      [line.id]: { text: "", loading: true, error: false },
    }));

    try {
      const response = await api.explainPlan({
        context_type: "forecast",
        outlet_id: line.outlet_id,
        sku_id: line.sku_id,
        plan_date: date,
        language,
      });
      setExplanations((current) => ({
        ...current,
        [line.id]: { text: response.explanation, loading: false, error: false },
      }));
    } catch (_error) {
      setExplanations((current) => ({
        ...current,
        [line.id]: { text: "", loading: false, error: true },
      }));
    }
  }

  function handleOverrideSubmit(
    payload:
      | ForecastOverridePayload
      | Partial<Pick<ForecastOverridePayload, "title" | "notes" | "adjustment_pct" | "enabled">>,
    overrideId?: number
  ) {
    if (overrideId) {
      updateOverrideMutation.mutate({
        overrideId,
        payload: payload as Parameters<typeof api.updateForecastOverride>[1],
      });
      return;
    }
    createOverrideMutation.mutate(payload as ForecastOverridePayload);
  }

  function saveManualAdjustment(line: ForecastDisplayLine) {
    const raw = adjustmentInputs[line.id];
    const parsed = Number(raw);
    if (!Number.isFinite(parsed)) {
      return;
    }

    adjustMutation.mutate(
      {
        runId: line.run_id,
        lineId: line.id,
        pct: parsed,
      },
      {
        onSuccess: async () => {
          setAdjustmentInputs((current) => ({ ...current, [line.id]: "" }));
          await invalidateForecastViews();
        },
      }
    );
  }

  return (
    <div className="min-h-screen">
      <Header title={t("forecast.title", "Demand Forecast")} date={date}>
        <select
          value={outletId}
          onChange={(event) => setOutletId(event.target.value)}
          className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          <option value="all">{t("forecast.allOutlets", "All Outlets")}</option>
          {outlets.map((outlet) => (
            <option key={outlet.id} value={String(outlet.id)}>
              {outlet.name}
            </option>
          ))}
        </select>
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
          {runMutation.isPending
            ? t("common.running", "Running...")
            : t("forecast.runForecast", "Run Forecast")}
        </button>
      </Header>

      <main className="max-w-7xl space-y-6 p-6 page-enter">
        {(forecastsQuery.error ||
          runMutation.error ||
          adjustMutation.error ||
          createOverrideMutation.error ||
          updateOverrideMutation.error ||
          deleteOverrideMutation.error) && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {forecastsQuery.error instanceof Error
              ? forecastsQuery.error.message
              : runMutation.error instanceof Error
                ? runMutation.error.message
                : adjustMutation.error instanceof Error
                  ? adjustMutation.error.message
                  : createOverrideMutation.error instanceof Error
                    ? createOverrideMutation.error.message
                    : updateOverrideMutation.error instanceof Error
                      ? updateOverrideMutation.error.message
                      : deleteOverrideMutation.error instanceof Error
                        ? deleteOverrideMutation.error.message
                        : t("dashboard.failedDailyPlan", "Failed to load daily plan")}
          </div>
        )}

        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {t("forecast.predictedByDaypart", "Predicted Demand by Daypart")}
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                key: "morning",
                label: t("common.daypart.morning", "Morning"),
                value: daypartTotals.morning,
                tone: "border-amber-200 bg-amber-50 text-amber-700",
              },
              {
                key: "midday",
                label: t("common.daypart.midday", "Midday"),
                value: daypartTotals.midday,
                tone: "border-sky-200 bg-sky-50 text-sky-700",
              },
              {
                key: "evening",
                label: t("common.daypart.evening", "Evening"),
                value: daypartTotals.evening,
                tone: "border-violet-200 bg-violet-50 text-violet-700",
              },
            ].map((card) => (
              <div key={card.key} className={`rounded-xl border p-5 ${card.tone}`}>
                <p className="text-xs font-semibold uppercase tracking-wide">{card.label}</p>
                {forecastsQuery.isLoading ? (
                  <div className="mt-3 h-8 w-24 animate-pulse rounded bg-neutral-200/70" />
                ) : (
                  <p className="mt-3 text-3xl font-bold">
                    {card.value.toFixed(1)}
                    <span className="ml-1 text-sm font-normal opacity-60">
                      {t("common.units", "units")}
                    </span>
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>

        {lines.length > 0 && (
          <section>
            <ForecastChart lines={lines} />
          </section>
        )}

        {selectedOutlet ? (
          <div className="space-y-4">
            <DemandDriversPanel
              outletName={selectedOutlet.name}
              context={contextQuery.data}
              isLoading={contextQuery.isLoading}
              errorMessage={contextQuery.error instanceof Error ? contextQuery.error.message : null}
              skus={selectableSkus}
              selectedSkuId={contextSkuId}
              onSelectedSkuIdChange={setContextSkuId}
              onEditOverride={setEditingOverride}
              onDeleteOverride={(overrideId) => deleteOverrideMutation.mutate(overrideId)}
              deletePending={deleteOverrideMutation.isPending}
            />
            <OverrideEditor
              targetDate={date}
              outletId={selectedOutlet.id}
              skus={selectableSkus}
              editingOverride={editingOverride}
              onCancelEdit={() => setEditingOverride(null)}
              onSubmit={handleOverrideSubmit}
              isBusy={createOverrideMutation.isPending || updateOverrideMutation.isPending}
            />
          </div>
        ) : (
          <div className="rounded-xl border border-neutral-200 bg-neutral-50 px-5 py-4 text-sm text-neutral-600">
            {t(
              "forecast.demandDriversPrompt",
              "Choose one outlet to inspect demand drivers and manage event or promo overrides."
            )}
          </div>
        )}

        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {t("forecast.lines", "Forecast Lines")}
          </h2>
          <div className="overflow-x-auto overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  <th className="px-4 py-3">{t("forecast.sku", "SKU")}</th>
                  <th className="px-4 py-3">{t("forecast.outlet", "Outlet")}</th>
                  <th className="px-4 py-3 text-right">{t("common.daypart.morning", "Morning")}</th>
                  <th className="px-4 py-3 text-right">{t("common.daypart.midday", "Midday")}</th>
                  <th className="px-4 py-3 text-right">{t("common.daypart.evening", "Evening")}</th>
                  <th className="px-4 py-3 text-right">{t("forecast.total", "Total")}</th>
                  <th className="px-4 py-3 text-right">{t("forecast.manualAdj", "Manual Adj.")}</th>
                  <th className="px-4 py-3 w-16" />
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {forecastsQuery.isLoading
                  ? Array.from({ length: 8 }).map((_, rowIndex) => (
                      <tr key={rowIndex}>
                        {Array.from({ length: 8 }).map((__, cellIndex) => (
                          <td key={cellIndex} className="px-4 py-3">
                            <div className="h-4 animate-pulse rounded bg-neutral-100" />
                          </td>
                        ))}
                      </tr>
                    ))
                  : lines.length === 0
                    ? (
                      <tr>
                        <td colSpan={8} className="px-4 py-12 text-center text-sm text-neutral-400">
                          {t(
                            "forecast.noData",
                            "No forecast data available. Run a forecast to generate line items for this date."
                          )}
                        </td>
                      </tr>
                    )
                    : lines.map((line) => (
                        <Fragment key={line.id}>
                          <tr className="transition-colors hover:bg-neutral-50">
                            <td className="px-4 py-3 font-medium text-neutral-800">
                              {line.sku_name ?? `SKU ${line.sku_id}`}
                            </td>
                            <td className="px-4 py-3 text-xs text-neutral-500">
                              {line.outlet_name ?? `Outlet ${line.outlet_id}`}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums text-neutral-700">
                              {line.morning.toFixed(1)}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums text-neutral-700">
                              {line.midday.toFixed(1)}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums text-neutral-700">
                              {line.evening.toFixed(1)}
                            </td>
                            <td className="px-4 py-3 text-right tabular-nums font-semibold text-neutral-900">
                              {line.total.toFixed(1)}
                            </td>
                            <td className="px-4 py-3 text-right">
                              <div className="space-y-2">
                                <div className="text-xs text-neutral-500">
                                  {t("forecast.current", "Current")}:{" "}
                                  {line.manual_adjustment_pct != null
                                    ? `${line.manual_adjustment_pct.toFixed(1)}%`
                                    : t("forecast.noCurrentAdjustment", "none")}
                                </div>
                                <div className="flex justify-end gap-2">
                                  <input
                                    type="number"
                                    min={-100}
                                    step={1}
                                    value={adjustmentInputs[line.id] ?? ""}
                                    onChange={(event) =>
                                      setAdjustmentInputs((current) => ({
                                        ...current,
                                        [line.id]: event.target.value,
                                      }))
                                    }
                                    placeholder="0"
                                    className="w-20 rounded border border-neutral-300 px-2 py-1 text-right text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-amber-400"
                                  />
                                  <button
                                    onClick={() => saveManualAdjustment(line)}
                                    disabled={
                                      adjustMutation.isPending ||
                                      (adjustmentInputs[line.id] ?? "").trim().length === 0
                                    }
                                    className="rounded-md border border-neutral-200 px-2 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                                  >
                                    {t("common.save", "Save")}
                                  </button>
                                </div>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => toggleWhy(line)}
                                className={`inline-flex items-center gap-1 text-xs font-medium ${
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
                                {expandedLines.has(line.id)
                                  ? t("forecast.closeWhy", "Close")
                                  : t("forecast.why", "Why?")}
                              </button>
                            </td>
                          </tr>
                          {expandedLines.has(line.id) && (
                            <tr>
                              <td colSpan={8} className="border-t border-amber-100 bg-amber-50 px-6 py-3">
                                {explanations[line.id]?.loading ? (
                                  <div className="flex items-center gap-2 text-sm text-neutral-500">
                                    <div className="h-3 w-3 animate-pulse rounded-full bg-amber-300" />
                                    {t("forecast.generatingExplanation", "Generating explanation...")}
                                  </div>
                                ) : explanations[line.id]?.error ? (
                                  <p className="text-xs italic text-neutral-400">
                                    {t(
                                      "forecast.explanationUnavailable",
                                      "Explanation unavailable. Try again later."
                                    )}
                                  </p>
                                ) : explanations[line.id]?.text ? (
                                  <p className="text-sm leading-relaxed text-neutral-700">
                                    {explanations[line.id]?.text}
                                  </p>
                                ) : null}
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}
