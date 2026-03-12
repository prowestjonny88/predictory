"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";

import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateRiskLevel } from "@/lib/i18n";
import { api } from "@/lib/api";
import { cn, todayISO } from "@/lib/utils";
import type { DailyPlan, DailyPlanReplenishmentLine, UrgencyLevel } from "@/types";

const URGENCY_STYLES: Record<UrgencyLevel, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-green-100 text-green-700",
};

export default function ReplenishmentPage() {
  const [date, setDate] = useState(todayISO);
  const [orderedIds, setOrderedIds] = useState(new Set<number>());
  const queryClient = useQueryClient();
  const { language, t } = useLanguage();

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
  const totalReorderQty = useMemo(() => lines.reduce((sum, line) => sum + line.reorder_qty, 0), [lines]);
  const orderedCount = orderedIds.size;

  function toggleOrdered(ingredientId: number) {
    setOrderedIds((prev) => {
      const next = new Set(prev);
      if (next.has(ingredientId)) {
        next.delete(ingredientId);
      } else {
        next.add(ingredientId);
      }
      return next;
    });
  }

  function derivedReason(line: DailyPlanReplenishmentLine): string {
    if (line.need_qty <= 0) return t("replenishment.stockSufficient", "Stock sufficient");
    const pct = Math.round((line.stock_on_hand / line.need_qty) * 100);
    const skuList = line.driving_skus.slice(0, 2).join(", ");
    const tail = line.driving_skus.length > 2 ? ` +${line.driving_skus.length - 2}` : "";
    if (language === "ms") {
      return `Stok meliputi ${pct}% keperluan pengeluaran${skuList ? ` untuk ${skuList}${tail}` : ""}`;
    }
    if (language === "zh-CN") {
      return `库存覆盖生产需求的 ${pct}%${skuList ? `，用于 ${skuList}${tail}` : ""}`;
    }
    return `Stock covers ${pct}% of production need${skuList ? ` for ${skuList}${tail}` : ""}`;
  }

  return (
    <div className="min-h-screen">
      <Header title={t("replenishment.title", "Replenishment")} date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => {
            setDate(event.target.value);
            setOrderedIds(new Set());
          }}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
        <button
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
          className="rounded-md bg-amber-500 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-60"
        >
          {runMutation.isPending
            ? t("common.running", "Running...")
            : t("replenishment.run", "Run Replenishment")}
        </button>
      </Header>

      <main className="max-w-7xl space-y-5 p-6">
        {dailyPlanQuery.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {dailyPlanQuery.error instanceof Error
              ? dailyPlanQuery.error.message
              : t("replenishment.failed", "Failed to load replenishment plan")}
          </div>
        )}

        {lines.length > 0 && (
          <div className="flex flex-wrap items-center gap-3">
            {(["critical", "high", "medium", "low"] as UrgencyLevel[]).map((key) =>
              urgencyCounts[key] ? (
                <span
                  key={key}
                  className={cn("rounded-full px-3 py-0.5 text-xs font-semibold", URGENCY_STYLES[key])}
                >
                  {urgencyCounts[key]} {translateRiskLevel(language, key)}
                </span>
              ) : null
            )}
            {orderedCount > 0 && (
              <span className="rounded-full bg-green-100 px-3 py-0.5 text-xs font-semibold text-green-700">
                {orderedCount} {t("replenishment.ordered", "ordered")}
              </span>
            )}
            <span className="ml-1 text-sm text-neutral-500">
              {t("replenishment.totalQty", "{{count}} total reorder quantity", {
                count: totalReorderQty.toFixed(1),
              })}
            </span>
          </div>
        )}

        <div className="overflow-x-auto overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <th className="px-4 py-3">{t("replenishment.ingredient", "Ingredient")}</th>
                <th className="px-4 py-3 text-right">{t("replenishment.stockOnHand", "Stock On Hand")}</th>
                <th className="px-4 py-3 text-right">{t("replenishment.needQty", "Need Qty")}</th>
                <th className="px-4 py-3 text-right">{t("replenishment.reorderQty", "Reorder Qty")}</th>
                <th className="px-4 py-3">{t("replenishment.urgency", "Urgency")}</th>
                <th className="px-4 py-3">{t("replenishment.drivingSkus", "Driving SKUs")}</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {dailyPlanQuery.isLoading ? (
                Array.from({ length: 6 }).map((_, rowIndex) => (
                  <tr key={rowIndex}>
                    {Array.from({ length: 7 }).map((__, cellIndex) => (
                      <td key={cellIndex} className="px-4 py-3">
                        <div className="h-4 animate-pulse rounded bg-neutral-100" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : lines.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-sm text-neutral-400">
                    {t("replenishment.noData", "No replenishment data.")}{" "}
                    <button
                      onClick={() => runMutation.mutate()}
                      className="font-medium text-amber-600 hover:text-amber-700"
                    >
                      {t("replenishment.run", "Run Replenishment")}
                    </button>{" "}
                    {t("replenishment.toGenerate", "to generate one.")}
                  </td>
                </tr>
              ) : (
                lines.map((line) => {
                    const isOrdered = orderedIds.has(line.ingredient_id);
                    return (
                      <tr
                        key={`${line.ingredient_id}-${line.ingredient_name}`}
                        className={cn(
                          "transition-colors hover:bg-neutral-50",
                          line.urgency === "critical" && !isOrdered && "bg-red-50/30",
                          isOrdered && "opacity-60"
                        )}
                      >
                        <td className="px-4 py-3">
                          <p className={cn("font-medium text-neutral-800", isOrdered && "line-through text-neutral-400")}>
                            {line.ingredient_name}
                          </p>
                          <p className="mt-0.5 text-xs italic text-neutral-400">
                            {derivedReason(line)}
                          </p>
                        </td>
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
                            {translateRiskLevel(language, line.urgency)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-neutral-500">
                          {line.driving_skus.length > 0 ? line.driving_skus.join(", ") : t("common.none", "None")}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={() => toggleOrdered(line.ingredient_id)}
                            className={cn(
                              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                              isOrdered
                                ? "border border-green-200 bg-green-50 text-green-700 hover:bg-green-100"
                                : "border border-neutral-200 bg-white text-neutral-600 hover:bg-neutral-50"
                            )}
                          >
                            <CheckCircle2 className={cn("h-3.5 w-3.5", isOrdered ? "text-green-600" : "text-neutral-400")} />
                            {isOrdered
                              ? t("replenishment.ordered", "Ordered")
                              : t("replenishment.markOrdered", "Mark as Ordered")}
                          </button>
                        </td>
                      </tr>
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
