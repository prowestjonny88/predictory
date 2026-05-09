import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import ExplainButton from "@/components/copilot/ExplainButton";
import StockNeedBar from "@/components/StockNeedBar";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import type { DailyPlanTopAction } from "@/lib/api/planning";

interface Props {
  item: DailyPlanTopAction | null;
}

export default function ReplenishmentBreakdown({ item }: Props) {
  const { t } = useLanguage();
  if (!item) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>{t("planning.replenishment.title", "Replenishment breakdown")}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-neutral-500">
          {t("planning.replenishment.empty", "Select a recommendation to see ingredient needs and shortages.")}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>{t("planning.replenishment.title", "Replenishment breakdown")}</CardTitle>
        <Badge variant="outline">{item.sku_name}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {item.replenishment.length === 0 && (
          <p className="text-sm text-neutral-500">
            {t("planning.replenishment.noShortages", "No ingredient shortages detected.")}
          </p>
        )}
        {item.replenishment.map((line) => (
          <div key={line.ingredient_id} className="rounded-lg border border-neutral-100 p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-neutral-900">{line.ingredient_name}</p>
                <p className="text-xs text-neutral-500">
                  {t("planning.replenishment.required", "Required")} {line.required_qty} {line.unit}
                </p>
              </div>
              <Badge variant={line.shortage_qty > 0 ? "high" : "low"}>
                {t("planning.replenishment.short", "Short")} {line.shortage_qty} {line.unit}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-neutral-500">
              {t("planning.replenishment.currentStock", "Current stock")}: {line.current_stock} {line.unit}
            </p>
            <div className="mt-3">
              <StockNeedBar
                stock={line.current_stock}
                need={line.required_qty}
                unit={line.unit}
              />
            </div>
            <p className="mt-1 text-xs text-neutral-500">
              {t("planning.replenishment.reorder", "Reorder need")}: {line.reorder_qty} {line.unit}
            </p>
            <div className="mt-3">
              <ExplainButton
                label={t("planning.replenishment.whyReorder", "Why reorder?")}
                title={t("planning.replenishment.whyReorderTitle", "Why reorder {{ingredient}}?", {
                  ingredient: line.ingredient_name,
                })}
                contextType="replenishment"
                evidence={{
                  outlet_name: item.outlet_name,
                  sku_name: item.sku_name,
                  daypart: item.daypart,
                  recommended_prep: item.recommended_prep,
                  ingredient_name: line.ingredient_name,
                  required_qty: line.required_qty,
                  current_stock: line.current_stock,
                  shortage_qty: line.shortage_qty,
                  reorder_qty: line.reorder_qty,
                  unit: line.unit,
                  source: "backend_replenishment_breakdown",
                }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
