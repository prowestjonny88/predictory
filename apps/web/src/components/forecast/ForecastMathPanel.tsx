import type { ForecastLine } from "@/types";
import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  line: (ForecastLine & { sku_name?: string; outlet_name?: string }) | null;
}

const DAYPARTS = ["morning", "midday", "evening"] as const;

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
  const uncertainty = rationale.uncertainty ?? {};
  const featureRows = rationale.feature_rows ?? {};

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-neutral-800">
            {t("forecast.mathDetails", "Forecast evidence")}
          </h3>
          <p className="text-xs text-neutral-500">
            {line.sku_name ?? `SKU ${line.sku_id}`} {" - "} {line.outlet_name ?? `Outlet ${line.outlet_id}`}
          </p>
        </div>
        <span className="rounded-full bg-neutral-100 px-2 py-1 text-[11px] font-semibold text-neutral-600">
          {rationale.model_version ?? line.method}
        </span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-3">
        <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
          <p className="text-xs uppercase tracking-wide text-neutral-500">
            {t("forecast.model", "Model")}
          </p>
          <p className="mt-2 text-sm text-neutral-700">
            {t("forecast.engine", "Engine")}: {rationale.engine_name ?? "-"}
          </p>
          <p className="text-sm text-neutral-700">
            {t("forecast.method", "Method")}: {rationale.method ?? line.method}
          </p>
          <p className="text-sm text-neutral-700">
            {t("forecast.total", "Total")}: {formatNumber(line.total)}
          </p>
        </div>

        {DAYPARTS.map((daypart) => {
          const band = uncertainty[daypart] ?? {};
          const row = featureRows[daypart] ?? {};
          return (
            <div key={daypart} className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
              <p className="text-xs uppercase tracking-wide text-neutral-500">
                {t(`common.daypart.${daypart}`, daypart)}
              </p>
              <p className="mt-2 text-sm text-neutral-700">p10: {formatNumber(band.p10)}</p>
              <p className="text-sm text-neutral-700">p50: {formatNumber(band.p50)}</p>
              <p className="text-sm text-neutral-700">p90: {formatNumber(band.p90)}</p>
              <p className="text-xs text-neutral-500">
                {t("forecast.featureCount", "Encoded features")}: {row.encoded_feature_count ?? "-"}
              </p>
            </div>
          );
        })}
      </div>

      {rationale.reason_tags?.length ? (
        <div className="mt-4 rounded-lg border border-neutral-100 bg-white p-3 text-xs text-neutral-600">
          {t("forecast.reasonTags", "Reason tags")}: {rationale.reason_tags.join(" / ")}
        </div>
      ) : null}
    </section>
  );
}
