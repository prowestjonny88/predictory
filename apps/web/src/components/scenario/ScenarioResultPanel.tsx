"use client";

import type { ScenarioResult } from "@/types";

interface Props {
  result: ScenarioResult;
}

function readNumber(record: Record<string, number | string>, key: string): number {
  const value = record[key];
  return typeof value === "number" ? value : 0;
}

function DeltaBadge({ value }: { value: number }) {
  if (value === 0) {
    return <span className="text-xs text-neutral-400">No change</span>;
  }

  return (
    <span className={`text-xs font-semibold ${value < 0 ? "text-green-600" : "text-red-600"}`}>
      {value > 0 ? "+" : ""}
      {value}
    </span>
  );
}

export default function ScenarioResultPanel({ result }: Props) {
  const baselineWaste = readNumber(result.baseline, "waste_alerts");
  const baselineStockout = readNumber(result.baseline, "stockout_alerts");
  const modifiedWaste = readNumber(result.modified, "waste_alerts");
  const modifiedStockout = readNumber(result.modified, "stockout_alerts");
  const wasteDelta =
    typeof result.delta.waste_change === "number"
      ? result.delta.waste_change
      : modifiedWaste - baselineWaste;
  const stockoutDelta =
    typeof result.delta.stockout_change === "number"
      ? result.delta.stockout_change
      : modifiedStockout - baselineStockout;

  return (
    <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="rounded-lg border border-violet-100 bg-violet-50 px-4 py-3">
        <p className="text-sm font-medium italic text-violet-800">&ldquo;{result.scenario}&rdquo;</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Waste Alerts</p>
          <p className="mt-2 text-2xl font-bold text-neutral-900">
            {baselineWaste}
            <span className="mx-2 text-neutral-300">-&gt;</span>
            {modifiedWaste}
          </p>
          <DeltaBadge value={wasteDelta} />
        </div>
        <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Stockout Alerts</p>
          <p className="mt-2 text-2xl font-bold text-neutral-900">
            {baselineStockout}
            <span className="mx-2 text-neutral-300">-&gt;</span>
            {modifiedStockout}
          </p>
          <DeltaBadge value={stockoutDelta} />
        </div>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Recommendation</p>
        <p className="mt-2 text-sm leading-relaxed text-neutral-800">{result.recommendation}</p>
      </div>

      <div className="rounded-lg border border-neutral-200 bg-white px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Interpretation</p>
        <p className="mt-2 text-sm leading-relaxed text-neutral-800">{result.interpretation}</p>
      </div>
    </div>
  );
}
