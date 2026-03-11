"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO, cn } from "@/lib/utils";
import Header from "@/components/Header";
import { Bot, Zap } from "lucide-react";
import type { ScenarioResult } from "@/types";

function DeltaBadge({ baseline, projected }: { baseline: number; projected: number }) {
  const diff = projected - baseline;
  if (diff === 0) return <span className="text-neutral-400 text-xs">no change</span>;
  return (
    <span className={cn("text-xs font-semibold", diff < 0 ? "text-green-600" : "text-red-600")}>
      {diff > 0 ? "+" : ""}{diff} ({diff < 0 ? "better" : "worse"})
    </span>
  );
}

export default function CopilotPage() {
  const [date, setDate] = useState(todayISO);
  const [scenario, setScenario] = useState("");
  const [brief, setBrief] = useState<string | null>(null);

  const briefMutation = useMutation({
    mutationFn: () => api.dailyBrief(date),
    onSuccess: (data) => setBrief(data.brief),
  });

  const scenarioMutation = useMutation<ScenarioResult>({
    mutationFn: () => api.runScenario(scenario, date),
  });

  return (
    <div className="min-h-screen">
      <Header title="AI Copilot" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => {
            setDate(e.target.value);
            setBrief(null);
          }}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="p-6 space-y-6 max-w-3xl">
        {/* Daily brief */}
        <section className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-neutral-700">Daily Brief</h2>
          </div>
          <p className="text-xs text-neutral-500">
            Generate a plain-language summary of tomorrow&apos;s plan: forecast, top risks, and recommended actions.
          </p>
          <button
            onClick={() => briefMutation.mutate()}
            disabled={briefMutation.isPending}
            className="rounded-md bg-amber-500 hover:bg-amber-600 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
          >
            {briefMutation.isPending ? "Generating…" : "Generate Brief"}
          </button>
          {briefMutation.error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {briefMutation.error instanceof Error
                ? briefMutation.error.message
                : "Failed to generate brief"}
            </div>
          )}
          {brief && (
            <div className="rounded-lg bg-amber-50 border border-amber-100 px-4 py-4 text-sm text-neutral-800 whitespace-pre-wrap leading-relaxed">
              {brief}
            </div>
          )}
        </section>

        {/* Scenario runner */}
        <section className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-violet-500" />
            <h2 className="text-sm font-semibold text-neutral-700">What-If Scenario</h2>
          </div>
          <p className="text-xs text-neutral-500">
            Describe a change and see how it would affect waste and stockout risk.
          </p>
          <textarea
            rows={3}
            placeholder='e.g. &quot;What if I increase croissant prep by 20% at all outlets tomorrow?&quot;'
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
          <button
            onClick={() => scenarioMutation.mutate()}
            disabled={scenarioMutation.isPending || !scenario.trim()}
            className="rounded-md bg-neutral-800 hover:bg-neutral-900 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
          >
            {scenarioMutation.isPending ? "Running…" : "Run Scenario"}
          </button>

          {scenarioMutation.error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {scenarioMutation.error instanceof Error
                ? scenarioMutation.error.message
                : "Scenario failed"}
            </div>
          )}

          {scenarioMutation.data && (
            <div className="space-y-4 pt-1">
              {/* Delta grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Waste alerts</p>
                  <p className="text-xl font-bold text-neutral-800">
                    {scenarioMutation.data.baseline_waste_alerts}
                    <span className="text-neutral-300 mx-1">→</span>
                    {scenarioMutation.data.projected_waste_alerts}
                  </p>
                  <DeltaBadge
                    baseline={scenarioMutation.data.baseline_waste_alerts}
                    projected={scenarioMutation.data.projected_waste_alerts}
                  />
                </div>
                <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Stockout alerts</p>
                  <p className="text-xl font-bold text-neutral-800">
                    {scenarioMutation.data.baseline_stockout_alerts}
                    <span className="text-neutral-300 mx-1">→</span>
                    {scenarioMutation.data.projected_stockout_alerts}
                  </p>
                  <DeltaBadge
                    baseline={scenarioMutation.data.baseline_stockout_alerts}
                    projected={scenarioMutation.data.projected_stockout_alerts}
                  />
                </div>
              </div>

              {/* Explanation */}
              <div className="rounded-lg bg-violet-50 border border-violet-100 px-4 py-4 text-sm text-neutral-800 whitespace-pre-wrap leading-relaxed">
                {scenarioMutation.data.explanation}
              </div>

              {/* Affected SKUs */}
              {scenarioMutation.data.affected_skus?.length > 0 && (
                <div>
                  <p className="text-xs text-neutral-500 mb-1.5">Affected SKUs</p>
                  <div className="flex flex-wrap gap-1">
                    {scenarioMutation.data.affected_skus.map((sku, i) => (
                      <span
                        key={i}
                        className="rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 text-xs text-neutral-700"
                      >
                        {sku}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
