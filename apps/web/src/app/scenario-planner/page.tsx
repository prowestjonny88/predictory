"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { GitBranch, Sparkles, ArrowRight, Zap } from "lucide-react";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import type { ScenarioResult } from "@/types";

const PRESETS = [
  {
    id: "cut-croissant",
    label: "Cut croissant prep −15%",
    text: "Reduce croissant preparation by 15% at all outlets for tomorrow due to lower demand forecast.",
  },
  {
    id: "butter-delay",
    label: "Butter delivery delayed",
    text: "Butter ingredient delivery is delayed by 1 day. Adjust all butter-dependent recipes for tomorrow.",
  },
  {
    id: "demand-spike",
    label: "+30% weekend demand spike",
    text: "Expect a 30% demand spike at all outlets tomorrow due to a major weekend event nearby.",
  },
] as const;

function DeltaBadge({
  baseline,
  projected,
}: {
  baseline: number;
  projected: number;
}) {
  const delta = projected - baseline;
  const pct = baseline > 0 ? Math.round((delta / baseline) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="text-2xl font-bold tabular-nums text-neutral-800">{projected}</span>
      {delta !== 0 && (
        <span
          className={`text-xs font-semibold px-1.5 py-0.5 rounded ${
            delta < 0 ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          }`}
        >
          {delta > 0 ? "+" : ""}
          {pct}%
        </span>
      )}
    </div>
  );
}

export default function ScenarioPlannerPage() {
  const [date, setDate] = useState(todayISO);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [customText, setCustomText] = useState("");

  const scenarioText = selectedPreset
    ? (PRESETS.find((p) => p.id === selectedPreset)?.text ?? "")
    : customText;

  const mutation = useMutation<ScenarioResult, Error>({
    mutationFn: () => api.runScenario(scenarioText, date),
  });

  const result = mutation.data;

  return (
    <div className="min-h-screen">
      <Header title="Scenario Planner" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="p-6 space-y-6 max-w-4xl">
        {/* Presets */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Quick Scenarios
          </h2>
          <div className="flex flex-wrap gap-3">
            {PRESETS.map((p) => (
              <button
                key={p.id}
                onClick={() => {
                  setSelectedPreset((prev) => (prev === p.id ? null : p.id));
                  setCustomText("");
                }}
                className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  selectedPreset === p.id
                    ? "border-amber-400 bg-amber-50 text-amber-700"
                    : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50"
                }`}
              >
                <Zap
                  className={`h-3.5 w-3.5 ${
                    selectedPreset === p.id ? "text-amber-500" : "text-neutral-400"
                  }`}
                />
                {p.label}
              </button>
            ))}
          </div>
        </section>

        {/* Custom input */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Describe a Scenario
          </h2>
          <textarea
            rows={3}
            placeholder="e.g. What if we increase croissant stock by 20% on weekends?"
            value={scenarioText}
            onChange={(e) => {
              setSelectedPreset(null);
              setCustomText(e.target.value);
            }}
            className="w-full rounded-lg border border-neutral-300 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-neutral-400">
              BakeWise models the downstream impact on prep, replenishment, and alert levels.
            </p>
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || !scenarioText.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 hover:bg-amber-600 text-white px-5 py-2 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {mutation.isPending ? (
                <>
                  <Sparkles className="h-4 w-4 animate-spin" />
                  Modelling…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Run Scenario
                </>
              )}
            </button>
          </div>
        </section>

        {/* Error */}
        {mutation.error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {mutation.error.message}
          </div>
        )}

        {/* Results */}
        {result && (
          <section className="space-y-5">
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-violet-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                Impact Analysis
              </h2>
            </div>

            {/* Scenario label */}
            <div className="rounded-lg border border-violet-100 bg-violet-50 px-4 py-3">
              <p className="text-sm font-medium text-violet-800 italic">
                &ldquo;{result.scenario_text}&rdquo;
              </p>
            </div>

            {/* Comparison grid */}
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-xl border border-neutral-200 bg-white p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400 mb-4">
                  Baseline
                </p>
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-neutral-500 mb-1">Waste Alerts</p>
                    <p className="text-2xl font-bold tabular-nums text-neutral-800">
                      {result.baseline_waste_alerts}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 mb-1">Stockout Alerts</p>
                    <p className="text-2xl font-bold tabular-nums text-neutral-800">
                      {result.baseline_stockout_alerts}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
                <div className="flex items-center gap-2 mb-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-amber-600">
                    Projected
                  </p>
                  <ArrowRight className="h-3 w-3 text-amber-400" />
                </div>
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-neutral-500 mb-1">Waste Alerts</p>
                    <DeltaBadge
                      baseline={result.baseline_waste_alerts}
                      projected={result.projected_waste_alerts}
                    />
                  </div>
                  <div>
                    <p className="text-xs text-neutral-500 mb-1">Stockout Alerts</p>
                    <DeltaBadge
                      baseline={result.baseline_stockout_alerts}
                      projected={result.projected_stockout_alerts}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* AI Explanation */}
            {result.explanation && (
              <div className="rounded-xl border border-violet-100 bg-white p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-violet-500 mb-3">
                  AI Analysis
                </p>
                <p className="text-sm text-neutral-700 leading-relaxed">{result.explanation}</p>
              </div>
            )}

            {/* Affected SKUs */}
            {result.affected_skus && result.affected_skus.length > 0 && (
              <div className="rounded-xl border border-neutral-200 bg-white p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-400 mb-3">
                  Affected SKUs
                </p>
                <div className="flex flex-wrap gap-2">
                  {result.affected_skus.map((sku, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-700"
                    >
                      {sku}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  );
}
