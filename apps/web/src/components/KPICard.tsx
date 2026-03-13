import { cn } from "@/lib/utils";
import { Area, AreaChart, ResponsiveContainer } from "recharts";

interface Props {
  title: string;
  value: string | number;
  sub?: string;
  risk?: "low" | "medium" | "high";
  loading?: boolean;
  sparklineData?: any[];
}

const riskStyles: Record<string, string> = {
  low:    "text-green-600",
  medium: "text-yellow-600",
  high:   "text-red-600",
};

const riskBorder: Record<string, string> = {
  low:    "border-green-200",
  medium: "border-yellow-200",
  high:   "border-red-200",
};

export default function KPICard({ title, value, sub, risk = "low", loading, sparklineData }: Props) {
  // Use risk color for the sparkline stroke/fill
  const riskColorHex = {
    low: "#16a34a", // green-600
    medium: "#ca8a04", // yellow-600
    high: "#dc2626", // red-600
  }[risk];

  return (
    <div
      className={cn(
        "bg-white rounded-xl border p-5 shadow-sm flex flex-col gap-1 min-w-0 relative overflow-hidden",
        riskBorder[risk]
      )}
    >
      <div className="relative z-10 flex flex-col gap-1">
        <span className="text-xs font-medium text-neutral-500 uppercase tracking-wide">
          {title}
        </span>
        {loading ? (
          <div className="h-8 w-24 bg-neutral-100 animate-pulse rounded mt-1" />
        ) : (
          <span className={cn("text-2xl font-bold", riskStyles[risk])}>{value}</span>
        )}
        {sub && !loading && (
          <span className="text-xs text-neutral-400">{sub}</span>
        )}
      </div>

      {sparklineData && !loading && (
        <div className="absolute bottom-0 left-0 right-0 h-12 opacity-10 pointer-events-none">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparklineData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke={riskColorHex} 
                fill={riskColorHex} 
                strokeWidth={2}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
