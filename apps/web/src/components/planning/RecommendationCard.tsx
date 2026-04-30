import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import UncertaintyBar from "@/components/planning/UncertaintyBar";
import type { DailyPlanTopAction } from "@/lib/api/planning";

interface Props {
  item: DailyPlanTopAction;
  onOpen: (item: DailyPlanTopAction) => void;
}

export default function RecommendationCard({ item, onOpen }: Props) {
  return (
    <Card className="p-4">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wide text-neutral-500">{item.outlet_name}</p>
            <h3 className="text-base font-semibold text-neutral-900">{item.sku_name}</h3>
            <p className="text-xs text-neutral-500">{item.daypart} · {item.sku_category}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{item.status.replace("_", " ")}</Badge>
            <Badge variant="high">RM {item.financial_exposure.stockout_exposure_rm}</Badge>
          </div>
        </div>

        <UncertaintyBar
          p10={item.p10}
          p50={item.p50}
          p90={item.p90}
          recommended={item.recommended_prep}
        />

        <div className="grid gap-2 md:grid-cols-3">
          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
            <p className="text-xs text-neutral-500">Opening stock</p>
            <p className="text-sm font-semibold text-neutral-900">{item.opening_stock}</p>
          </div>
          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
            <p className="text-xs text-neutral-500">Recommended prep</p>
            <p className="text-sm font-semibold text-neutral-900">{item.recommended_prep}</p>
          </div>
          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
            <p className="text-xs text-neutral-500">Batch size</p>
            <p className="text-sm font-semibold text-neutral-900">{item.batch_size}</p>
          </div>
        </div>

        <div className="rounded-lg border border-neutral-100 bg-white p-3 text-xs text-neutral-600">
          {item.reason_summary}
        </div>

        <div className="flex items-center justify-between">
          <div className="text-xs text-neutral-500">
            Waste cost RM {item.waste_cost.toFixed(2)} · Stockout cost RM {item.stockout_cost.toFixed(2)}
          </div>
          <Button variant="secondary" size="sm" onClick={() => onOpen(item)}>
            Review decision
          </Button>
        </div>
      </div>
    </Card>
  );
}
