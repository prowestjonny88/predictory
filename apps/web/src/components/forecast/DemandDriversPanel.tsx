"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import type { ForecastContext, ForecastOverride, SKU } from "@/types";

interface Props {
  outletName: string;
  context: ForecastContext | undefined;
  isLoading: boolean;
  errorMessage?: string | null;
  skus: SKU[];
  selectedSkuId: string;
  onSelectedSkuIdChange: (value: string) => void;
  onEditOverride: (override: ForecastOverride) => void;
  onDeleteOverride: (overrideId: number) => void;
  deletePending: boolean;
}

function SignalCard({
  title,
  value,
  subtitle,
  badge,
}: {
  title: string;
  value: string;
  subtitle: string;
  badge?: string;
}) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400">{title}</p>
          <p className="mt-2 text-lg font-semibold text-neutral-900">{value}</p>
          <p className="mt-1 text-xs leading-relaxed text-neutral-500">{subtitle}</p>
        </div>
        {badge && (
          <span className="rounded-full bg-amber-100 px-2 py-1 text-[11px] font-semibold text-amber-700">
            {badge}
          </span>
        )}
      </div>
    </div>
  );
}

export default function DemandDriversPanel({
  outletName,
  context,
  isLoading,
  errorMessage,
  skus,
  selectedSkuId,
  onSelectedSkuIdChange,
  onEditOverride,
  onDeleteOverride,
  deletePending,
}: Props) {
  const { t } = useLanguage();

  if (isLoading) {
    return (
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {t("drivers.title", "Demand Drivers")}
            </h2>
            <p className="mt-1 text-sm text-neutral-500">
              {t("drivers.loading", "Loading demand context for this outlet...")}
            </p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-32 animate-pulse rounded-xl border border-neutral-200 bg-neutral-100"
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 rounded-xl border border-neutral-200 bg-neutral-50 p-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {t("drivers.title", "Demand Drivers")}
          </h2>
          <p className="mt-1 text-sm text-neutral-600">
            {t(
              "drivers.inspect",
              "Inspect the signals influencing tomorrow's forecast for {{outletName}}.",
              { outletName }
            )}
          </p>
        </div>
        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-500">
          {t("drivers.skuContext", "SKU context")}
          <select
            value={selectedSkuId}
            onChange={(event) => onSelectedSkuIdChange(event.target.value)}
            className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            <option value="">{t("drivers.allSelectedOutlet", "All selected outlet")}</option>
            {skus.map((sku) => (
              <option key={sku.id} value={String(sku.id)}>
                {sku.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {errorMessage && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {errorMessage}
        </div>
      )}

      {context && (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <SignalCard
              title={t("drivers.holiday", "Holiday")}
              value={context.holiday?.label ?? t("drivers.noHolidayFlag", "No holiday flag")}
              subtitle={
                context.holiday?.details.join(" • ") ??
                t("drivers.noHolidayImpact", "No configured holiday impact for this date.")
              }
              badge={context.holiday ? `${context.holiday.adjustment_pct.toFixed(1)}%` : undefined}
            />
            <SignalCard
              title={t("drivers.weather", "Weather")}
              value={context.weather.label}
              subtitle={context.weather.details.join(" • ")}
              badge={`${context.weather.adjustment_pct.toFixed(1)}%`}
            />
            <SignalCard
              title={t("drivers.stockoutRecovery", "Stockout Recovery")}
              value={
                context.stockout_censoring.adjusted_history_days > 0
                  ? t("drivers.daysAdjusted", "{{count}} day(s) adjusted", {
                      count: context.stockout_censoring.adjusted_history_days,
                    })
                  : t("drivers.noAdjustments", "No adjustments")
              }
              subtitle={context.stockout_censoring.note}
              badge={
                context.stockout_censoring.enabled
                  ? t("drivers.heuristic", "Heuristic")
                  : undefined
              }
            />
            <SignalCard
              title={t("drivers.activeOverrides", "Active Overrides")}
              value={`${context.active_overrides.length}`}
              subtitle={t(
                "drivers.netAdjustment",
                "Net adjustment {{value}}% for the current context.",
                { value: context.combined_adjustment_pct.toFixed(1) }
              )}
              badge={context.active_overrides.length ? t("drivers.manual", "Manual") : undefined}
            />
          </div>

          <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-neutral-800">
                  {t("drivers.savedOverrides", "Saved Overrides")}
                </h3>
                <p className="mt-1 text-xs text-neutral-500">
                  {t(
                    "drivers.savedOverridesHelp",
                    "Outlet-wide overrides affect all SKUs. SKU-specific overrides only affect the selected SKU."
                  )}
                </p>
              </div>
            </div>

            {context.active_overrides.length === 0 ? (
              <p className="mt-4 text-sm text-neutral-500">
                {t("drivers.noOverrides", "No active overrides for this outlet and date.")}
              </p>
            ) : (
              <div className="mt-4 space-y-3">
                {context.active_overrides.map((override) => (
                  <div
                    key={override.id}
                    className="flex flex-col gap-3 rounded-lg border border-neutral-200 px-4 py-3 md:flex-row md:items-center md:justify-between"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-neutral-800">{override.title}</p>
                        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold uppercase text-neutral-600">
                          {t(`common.override.${override.override_type}`, override.override_type)}
                        </span>
                        {override.sku_name && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                            {override.sku_name}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs text-neutral-500">
                        {(override.notes || t("common.noNotes", "No notes"))} •{" "}
                        {override.adjustment_pct.toFixed(1)}% •{" "}
                        {override.enabled
                          ? t("common.enabled", "Enabled")
                          : t("common.disabled", "Disabled")}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => onEditOverride(override)}
                        className="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
                      >
                        {t("common.edit", "Edit")}
                      </button>
                      <button
                        onClick={() => onDeleteOverride(override.id)}
                        disabled={deletePending}
                        className="rounded-md border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
                      >
                        {t("common.delete", "Delete")}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
