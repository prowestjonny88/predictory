import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  label: string;
  value: string;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  className?: string;
}

export function KpiCard({ label, value, trend, trendDirection, className }: KpiCardProps) {
  return (
    <Card className={cn("overflow-hidden transition-all hover:shadow-md", className)}>
      <CardContent className="p-6">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className="mt-2 flex items-baseline gap-2">
          <p className="text-3xl font-bold tracking-tight text-neutral-900">{value}</p>
          {trend && (
            <span
              className={cn(
                "text-sm font-medium",
                trendDirection === "up" ? "text-emerald-600" : "",
                trendDirection === "down" ? "text-red-600" : "",
                trendDirection === "neutral" ? "text-neutral-500" : ""
              )}
            >
              {trendDirection === "up" && "↑ "}
              {trendDirection === "down" && "↓ "}
              {trendDirection === "neutral" && "— "}
              {trend}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
