import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DailyPlanTopAction } from "@/lib/api/planning";

interface Props {
  item: DailyPlanTopAction | null;
}

export default function ReplenishmentBreakdown({ item }: Props) {
  if (!item) {
    return (
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle>Replenishment breakdown</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-neutral-500">
          Select a recommendation to see ingredient needs and shortages.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <CardTitle>Replenishment breakdown</CardTitle>
        <Badge variant="outline">{item.sku_name}</Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        {item.replenishment.length === 0 && (
          <p className="text-sm text-neutral-500">No ingredient shortages detected.</p>
        )}
        {item.replenishment.map((line) => (
          <div key={line.ingredient_id} className="rounded-lg border border-neutral-100 p-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-neutral-900">{line.ingredient_name}</p>
                <p className="text-xs text-neutral-500">Required {line.required_qty} {line.unit}</p>
              </div>
              <Badge variant={line.shortage_qty > 0 ? "high" : "low"}>
                Short {line.shortage_qty} {line.unit}
              </Badge>
            </div>
            <p className="mt-2 text-xs text-neutral-500">
              Current stock: {line.current_stock} {line.unit}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
