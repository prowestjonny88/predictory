import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card";
import { useCurrency } from "@/components/CurrencyProvider";
import ExplainButton from "@/components/copilot/ExplainButton";
import UncertaintyBar from "@/components/planning/UncertaintyBar";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateDaypart, translateStatus } from "@/lib/i18n";
import { Info } from "lucide-react";
import type { DailyPlanTopAction } from "@/lib/api/planning";

interface Props {
  item: DailyPlanTopAction;
  onOpen: (item: DailyPlanTopAction) => void;
  onCouncilReview?: (item: DailyPlanTopAction) => void;
}

export default function RecommendationCard({ item, onOpen, onCouncilReview }: Props) {
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();

  const totalExposure = item.financial_exposure.stockout_exposure_rm + item.financial_exposure.waste_exposure_rm;
  const isCritical = totalExposure >= 500;
  const evidence = {
    outlet_name: item.outlet_name,
    sku_name: item.sku_name,
    sku_category: item.sku_category,
    daypart: item.daypart,
    p10: item.p10,
    p50: item.p50,
    p90: item.p90,
    opening_stock: item.opening_stock,
    recommended_prep: item.recommended_prep,
    batch_size: item.batch_size,
    waste_cost: item.waste_cost,
    stockout_cost: item.stockout_cost,
    stockout_exposure_rm: item.financial_exposure.stockout_exposure_rm,
    waste_exposure_rm: item.financial_exposure.waste_exposure_rm,
    priority_score: item.priority_score,
    priority_reason: item.priority_reason,
  };

  return (
    <Card className="flex flex-col transition-shadow hover:shadow-md">
      <CardHeader className="pb-2">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground notranslate">{item.outlet_name}</p>
              <Badge variant="outline" className="text-[10px]">{translateDaypart(language, item.daypart.toLowerCase())}</Badge>
            </div>
            <h3 className="mt-1 text-2xl font-bold tracking-tight text-neutral-900">
              {t("planning.recommendation.prepareUnits", "Prepare {{count}} units", { count: item.recommended_prep })}
            </h3>
            <p className="text-sm text-neutral-500 notranslate">{item.sku_name}</p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge variant="outline">{translateStatus(language, item.status)}</Badge>
            {totalExposure > 0 && (
              <Badge variant={isCritical ? "critical" : "high"}>
                {isCritical && `${t("planning.recommendation.criticalRisk", "Critical Risk")}: `}
                {formatCurrency(totalExposure, language, {
                  maximumFractionDigits: 0,
                  minimumFractionDigits: 0,
                })}
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-1 flex-col justify-between gap-4 pb-4">
        <div className="space-y-3">
          <UncertaintyBar
            p10={item.p10}
            p50={item.p50}
            p90={item.p90}
            recommended={item.recommended_prep}
          />

          <div className="flex items-start gap-2 rounded-lg border border-amber-100 bg-amber-50/50 p-3 text-xs text-amber-900">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-600" />
            <span>
              {item.reason_summary === "Stockout cost is higher than waste cost, so prep is slightly above expected demand."
                ? t("planning.reason.stockoutHigh", "Stockout cost is higher than waste cost, so prep is slightly above expected demand.")
                : item.reason_summary === "Waste cost is higher than stockout cost, so prep is conservative."
                ? t("planning.reason.wasteHigh", "Waste cost is higher than stockout cost, so prep is conservative.")
                : t(item.reason_summary, item.reason_summary)}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-lg border border-neutral-100 bg-neutral-50/50 p-2.5">
              <p className="text-[11px] font-medium text-muted-foreground">{t("planning.recommendation.openingStock", "Opening stock")}</p>
              <p className="text-sm font-semibold text-neutral-900">{item.opening_stock}</p>
            </div>
            <div className="rounded-lg border border-neutral-100 bg-neutral-50/50 p-2.5">
              <p className="text-[11px] font-medium text-muted-foreground">{t("planning.recommendation.expectedDemand", "Expected demand")}</p>
              <p className="text-sm font-semibold text-neutral-900">{item.p50}</p>
            </div>
            <div className="rounded-lg border border-neutral-100 bg-neutral-50/50 p-2.5">
              <p className="text-[11px] font-medium text-muted-foreground">{t("planning.recommendation.batchSize", "Batch size")}</p>
              <p className="text-sm font-semibold text-neutral-900">{item.batch_size}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between gap-2 rounded-lg border border-sky-100 bg-sky-50/50 p-3">
            <div className="flex items-start gap-2 text-xs text-sky-900">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-600" />
              <span>{t("planning.recommendation.geminiHelp", "Need a quick explanation? Gemini summarizes this evidence. For tradeoff review, open Agent Council.")}</span>
            </div>
            <ExplainButton
              label={t("planning.recommendation.whyAmount", "Why this amount?")}
              title={t("planning.recommendation.whyTitle", "Why prepare {{count}}?", { count: item.recommended_prep })}
              contextType="recommendation"
              evidence={evidence}
              recommendationId={item.id}
            />
          </div>
        </div>
      </CardContent>

      <CardFooter className="border-t bg-neutral-50/50 px-4 py-3 sm:px-6">
        <div className="flex w-full items-center justify-between gap-3">
          <div className="flex flex-col gap-0.5 text-[11px] font-medium text-muted-foreground">
            <span>
              {t("planning.recommendation.wasteCost", "Waste cost")}{" "}
              {formatCurrency(item.waste_cost, language, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span>
              {t("planning.recommendation.stockoutCost", "Stockout cost")}{" "}
              {formatCurrency(item.stockout_cost, language, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            {onCouncilReview && (
              <Button variant="outline" size="sm" onClick={() => onCouncilReview(item)}>
                {t("planning.recommendation.agentCouncil", "Review with Agent Council")}
              </Button>
            )}
            <Button variant="secondary" size="sm" onClick={() => onOpen(item)}>
              {t("planning.recommendation.reviewDecision", "Review decision")}
            </Button>
          </div>
        </div>
      </CardFooter>
    </Card>
  );
}
