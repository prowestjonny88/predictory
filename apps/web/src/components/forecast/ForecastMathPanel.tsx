import type { ForecastLine } from "@/types";
import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  line: (ForecastLine & { sku_name?: string; outlet_name?: string }) | null;
}

function formatPct(value?: number) {
  if (value == null) {
    return "-";
  }
  return `${value.toFixed(1)}%`;
}

function formatNumber(value?: number) {
  if (value == null || Number.isNaN(value)) {
    return "-";
  }
  return value.toFixed(1);
}

export default function ForecastMathPanel({ line }: Props) {
  const { t } = useLanguage();
  if (!line || !line.rationale_json) {
    return null;
  }

  const rationale = line.rationale_json as Record<string, any>;
  const weights = rationale.applied_component_weights ?? {};
  const ratios = rationale.historical_daypart_ratios ?? {};
  const holiday = rationale.holiday_signal;
  const weather = rationale.weather_signal;
  const overrides = rationale.manual_overrides ?? [];
  const stockout = rationale.stockout_censoring ?? {};

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-neutral-800">
            {t("forecast.mathDetails", "Forecast math details")}
          </h3>
          <p className="text-xs text-neutral-500">
            {line.sku_name ?? `SKU ${line.sku_id}`} · {line.outlet_name ?? `Outlet ${line.outlet_id}`}
          </p>
        </div>
        <span className="rounded-full bg-neutral-100 px-2 py-1 text-[11px] font-semibold text-neutral-600">
          {rationale.target_weekday ?? "-"}
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            {t("forecast.signalTotals", "Signal totals")}
          </p>
          <p className="mt-2 text-sm text-neutral-700">
            {t("forecast.weightedRecent", "Weighted recent")}:{" "}
            {formatNumber(rationale.weighted_recent_total)} (w {formatPct(weights.weighted_recent_total * 100)})
          </p>
          <p className="text-sm text-neutral-700">
            {t("forecast.weekdayPattern", "Weekday pattern")}:{" "}
            {formatNumber(rationale.weekday_pattern_total)} (w {formatPct(weights.weekday_pattern_total * 100)})
          </p>
          <p className="text-sm text-neutral-700">
            {t("forecast.avg14d", "14d average")}:{" "}
            {formatNumber(rationale.moving_avg_14d_total)} (w {formatPct(weights.moving_avg_14d_total * 100)})
          </p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            {t("forecast.adjustments", "Adjustments")}
          </p>
          <p className="mt-2 text-sm text-neutral-700">{t("forecast.baselineTotal", "Baseline total")}: {formatNumber(rationale.baseline_total)}</p>
          <p className="text-sm text-neutral-700">{t("forecast.contextAdjustment", "Context adjustment")}: {formatPct(rationale.context_adjustment_pct)}</p>
          <p className="text-sm text-neutral-700">{t("forecast.finalTotal", "Final total")}: {formatNumber(rationale.final_total_before_daypart_split)}</p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            {t("forecast.daypartSplit", "Daypart split")}
          </p>
          <p className="mt-2 text-sm text-neutral-700">{t("common.daypart.morning", "Morning")} ratio: {formatNumber(ratios.morning * 100)}%</p>
          <p className="text-sm text-neutral-700">{t("common.daypart.midday", "Midday")} ratio: {formatNumber(ratios.midday * 100)}%</p>
          <p className="text-sm text-neutral-700">{t("common.daypart.evening", "Evening")} ratio: {formatNumber(ratios.evening * 100)}%</p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            {t("forecast.drivers", "Drivers")}
          </p>
          <p className="mt-2 text-sm text-neutral-700">
            {t("forecast.holiday", "Holiday")}:{" "}
            {holiday?.label ?? t("common.none", "None")} ({formatPct(holiday?.adjustment_pct)})
          </p>
          <p className="text-sm text-neutral-700">
            {t("forecast.weather", "Weather")}:{" "}
            {weather?.label ?? t("forecast.unavailable", "Unavailable")} ({formatPct(weather?.adjustment_pct)})
          </p>
          <p className="text-sm text-neutral-700">{t("forecast.manualOverrides", "Manual overrides")}: {overrides.length}</p>
          <p className="text-sm text-neutral-700">{t("forecast.stockoutRecovery", "Stockout recovery")}: {stockout.adjusted_history_days ?? 0} {t("forecast.days", "day(s)")}</p>
        </div>
      </div>

      {rationale.reason_tags?.length ? (
        <div className="mt-4 rounded-lg border border-neutral-100 bg-white p-3 text-xs text-neutral-600">
          {t("forecast.reasonTags", "Reason tags")}: {rationale.reason_tags.join(" · ")}
        </div>
      ) : null}
    </section>
  );
}
