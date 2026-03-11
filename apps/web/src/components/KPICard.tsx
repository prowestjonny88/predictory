import { cn } from "@/lib/utils";

interface Props {
  title: string;
  value: string | number;
  sub?: string;
  risk?: "low" | "medium" | "high";
  loading?: boolean;
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

export default function KPICard({ title, value, sub, risk = "low", loading }: Props) {
  return (
    <div
      className={cn(
        "bg-white rounded-xl border p-5 shadow-sm flex flex-col gap-1 min-w-0",
        riskBorder[risk]
      )}
    >
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
  );
}
