import { cn } from "@/lib/utils";

interface Props {
  p10: number;
  p50: number;
  p90: number;
  recommended: number;
  className?: string;
}

export default function UncertaintyBar({ p10, p50, p90, recommended, className }: Props) {
  const min = Math.min(p10, p50, p90, recommended);
  const max = Math.max(p10, p50, p90, recommended);
  const span = Math.max(max - min, 1);

  const p10Pos = ((p10 - min) / span) * 100;
  const p50Pos = ((p50 - min) / span) * 100;
  const p90Pos = ((p90 - min) / span) * 100;
  const recPos = ((recommended - min) / span) * 100;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="relative h-2 rounded-full bg-neutral-200">
        <div
          className="absolute left-0 top-0 h-2 rounded-full bg-emerald-200"
          style={{ left: `${p10Pos}%`, right: `${100 - p90Pos}%` }}
        />
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-neutral-900"
          style={{ left: `calc(${p50Pos}% - 6px)` }}
          aria-label="p50"
        />
        <div
          className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full border-2 border-amber-500 bg-white"
          style={{ left: `calc(${recPos}% - 6px)` }}
          aria-label="recommended"
        />
      </div>
      <div className="flex justify-between text-[11px] text-neutral-500">
        <span>p10 {p10}</span>
        <span>p50 {p50}</span>
        <span>p90 {p90}</span>
      </div>
    </div>
  );
}
