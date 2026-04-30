import type { ForecastLine } from "@/types";

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
          <h3 className="text-sm font-semibold text-neutral-800">Forecast math details</h3>
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
          <p className="text-xs uppercase tracking-wide text-neutral-500">Signal totals</p>
          <p className="mt-2 text-sm text-neutral-700">
            Weighted recent: {formatNumber(rationale.weighted_recent_total)} (w {formatPct(weights.weighted_recent_total * 100)})
          </p>
          <p className="text-sm text-neutral-700">
            Weekday pattern: {formatNumber(rationale.weekday_pattern_total)} (w {formatPct(weights.weekday_pattern_total * 100)})
          </p>
          <p className="text-sm text-neutral-700">
            14d average: {formatNumber(rationale.moving_avg_14d_total)} (w {formatPct(weights.moving_avg_14d_total * 100)})
          </p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">Adjustments</p>
          <p className="mt-2 text-sm text-neutral-700">Baseline total: {formatNumber(rationale.baseline_total)}</p>
          <p className="text-sm text-neutral-700">Context adjustment: {formatPct(rationale.context_adjustment_pct)}</p>
          <p className="text-sm text-neutral-700">Final total: {formatNumber(rationale.final_total_before_daypart_split)}</p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">Daypart split</p>
          <p className="mt-2 text-sm text-neutral-700">Morning ratio: {formatNumber(ratios.morning * 100)}%</p>
          <p className="text-sm text-neutral-700">Midday ratio: {formatNumber(ratios.midday * 100)}%</p>
          <p className="text-sm text-neutral-700">Evening ratio: {formatNumber(ratios.evening * 100)}%</p>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">Drivers</p>
          <p className="mt-2 text-sm text-neutral-700">
            Holiday: {holiday?.label ?? "None"} ({formatPct(holiday?.adjustment_pct)})
          </p>
          <p className="text-sm text-neutral-700">
            Weather: {weather?.label ?? "Unavailable"} ({formatPct(weather?.adjustment_pct)})
          </p>
          <p className="text-sm text-neutral-700">Manual overrides: {overrides.length}</p>
          <p className="text-sm text-neutral-700">Stockout recovery: {stockout.adjusted_history_days ?? 0} day(s)</p>
        </div>
      </div>

      {rationale.reason_tags?.length ? (
        <div className="mt-4 rounded-lg border border-neutral-100 bg-white p-3 text-xs text-neutral-600">
          Reason tags: {rationale.reason_tags.join(" · ")}
        </div>
      ) : null}
    </section>
  );
}
