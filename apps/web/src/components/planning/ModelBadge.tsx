import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  engineName: string;
  dataSource: "backend";
  modelStatus: string;
  validationWindow: string;
  wape: number;
  coverage: number;
  onOpenEvidence: () => void;
}

export default function ModelBadge({
  engineName,
  dataSource,
  modelStatus,
  validationWindow,
  wape,
  coverage,
  onOpenEvidence,
}: Props) {
  const { t } = useLanguage();
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-col">
        <span className="text-xs uppercase tracking-wide text-neutral-500">{t("planning.modelBadgeLabel", "Model badge")}</span>
        <span className="text-sm font-semibold text-neutral-900">{engineName}</span>
        <span className="text-xs text-neutral-500">{t("planning.offlineModel", "Offline model")}: {modelStatus}</span>
        <span className="text-xs text-neutral-500">{t("planning.validation", "Validation")}: {validationWindow}</span>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="success">{t("planning.source", "Source")}: {dataSource}</Badge>
        <Badge variant="info">{t("planning.wape", "WAPE")} {(wape * 100).toFixed(1)}%</Badge>
        <Badge variant="low">{t("planning.coverage", "Coverage")} {(coverage * 100).toFixed(0)}%</Badge>
      </div>
      <Button variant="outline" size="sm" onClick={onOpenEvidence}>
        {t("planning.viewEvidence", "View evidence")}
      </Button>
    </div>
  );
}
