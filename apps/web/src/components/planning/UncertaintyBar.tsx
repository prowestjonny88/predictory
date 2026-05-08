import { useLanguage } from "@/components/i18n/LanguageProvider";
import { cn } from "@/lib/utils";

interface Props {
  p10: number;
  p50: number;
  p90: number;
  recommended: number;
  className?: string;
}

export default function UncertaintyBar({ p10, p50, p90, recommended, className }: Props) {
  const { t } = useLanguage();
  const min = Math.min(p10, p50, p90, recommended);
  const max = Math.max(p10, p50, p90, recommended);
  const span = Math.max(max - min, 1);

  const p10Pos = ((p10 - min) / span) * 100;
  const p50Pos = ((p50 - min) / span) * 100;
  const p90Pos = ((p90 - min) / span) * 100;
  const recPos = ((recommended - min) / span) * 100;
  const ariaLabel = `${t("planning.uncertainty.range", "Demand range")}: ${t(
    "planning.uncertainty.lowDemand",
    "Low demand / Quiet day"
  )} ${p10}, ${t("planning.uncertainty.expectedDemand", "Expected demand")} ${p50}, ${t(
    "planning.uncertainty.highDemand",
    "High demand / Busy day"
  )} ${p90}, ${t("planning.uncertainty.recommendedPrep", "Recommended prep")} ${recommended}`;

  return (
    <div className={cn("flex flex-col gap-3 rounded-lg border border-neutral-100 bg-white p-3", className)}>
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-600">
          {t("planning.uncertainty.range", "Demand range")}
        </p>
        <p className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-semibold text-amber-800">
          {t("planning.uncertainty.recommendedPrep", "Recommended prep")}: {recommended}
        </p>
      </div>
      <div className="relative h-4 rounded-full bg-neutral-200" role="img" aria-label={ariaLabel}>
        <div
          className="absolute top-0 h-4 rounded-full bg-emerald-200"
          style={{ left: `${p10Pos}%`, right: `${100 - p90Pos}%` }}
        />
        <div
          className="absolute top-1/2 h-5 w-1.5 -translate-y-1/2 rounded-full bg-neutral-900"
          style={{ left: `calc(${p50Pos}% - 3px)` }}
          aria-hidden="true"
        />
        <div
          className="absolute top-1/2 h-6 w-6 -translate-y-1/2 rounded-full border-4 border-amber-500 bg-white shadow-sm"
          style={{ left: `calc(${recPos}% - 12px)` }}
          aria-hidden="true"
        />
      </div>
      <div className="grid grid-cols-3 gap-2 text-[11px] text-neutral-500">
        <span>
          <span className="block font-semibold text-neutral-700">{t("planning.uncertainty.lowDemand", "Low demand / Quiet day")}</span>
          {p10}
        </span>
        <span className="text-center">
          <span className="block font-semibold text-neutral-700">{t("planning.uncertainty.expectedDemand", "Expected demand")}</span>
          {p50}
        </span>
        <span className="text-right">
          <span className="block font-semibold text-neutral-700">{t("planning.uncertainty.highDemand", "High demand / Busy day")}</span>
          {p90}
        </span>
      </div>
    </div>
  );
}
