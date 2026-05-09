import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  engineName: string;
  activeEngineName: string;
  dataSource: "backend";
  modelStatus: string;
  modelArtifactStatus: string;
  modelArtifactAvailable: boolean;
  forecastSourceLabel: string;
  validationWindow: string;
  wape: number;
  coverage: number;
  onOpenEvidence: () => void;
}

export default function ModelBadge({
  dataSource,
  modelArtifactAvailable,
  onOpenEvidence,
}: Props) {
  const { t } = useLanguage();
  const dataSourceLabel = dataSource === "backend" ? t("planning.source.backend", "Backend") : dataSource;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-col">
        <span className="text-xs uppercase tracking-wide text-neutral-500">
          {t("planning.forecastEvidence", "Forecast evidence")}
        </span>
        <span className="text-sm font-semibold text-neutral-900">
          {t("planning.forecastBackedPlan", "Forecast-backed plan")}
        </span>
        <span className="text-xs text-neutral-500">
          {t(
            "planning.forecastBackedPlanCopy",
            "Validated on recent sales with uncertainty range included."
          )}
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="success">{t("planning.source", "Source")}: {dataSourceLabel}</Badge>
        <Badge variant={modelArtifactAvailable ? "success" : "high"}>
          {t("planning.evidence", "Evidence")}:{" "}
          {modelArtifactAvailable
            ? t("planning.available", "available")
            : t("planning.missing", "missing")}
        </Badge>
      </div>
      <Button variant="outline" size="sm" onClick={onOpenEvidence}>
        {t("planning.viewEvidence", "View evidence")}
      </Button>
    </div>
  );
}
