"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { GitBranch, Sparkles, Zap } from "lucide-react";

import Header from "@/components/Header";
import ScenarioResultPanel from "@/components/scenario/ScenarioResultPanel";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import type { ScenarioResult } from "@/types";

const PRESETS = [
  {
    id: "cut-croissant",
    label: "Cut croissant prep -15%",
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

export default function ScenarioPlannerPage() {
  const [date, setDate] = useState(todayISO);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [customText, setCustomText] = useState("");

  const scenarioText = selectedPreset
    ? (PRESETS.find((preset) => preset.id === selectedPreset)?.text ?? "")
    : customText;

  const scenarioMutation = useMutation<ScenarioResult, Error>({
    mutationFn: () => api.runScenario(scenarioText, date),
  });

  return (
    <div className="min-h-screen">
      <Header title="Scenario Planner" date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => {
            setDate(event.target.value);
            scenarioMutation.reset();
          }}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="max-w-4xl space-y-6 p-6">
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Quick Scenarios
          </h2>
          <div className="flex flex-wrap gap-3">
            {PRESETS.map((preset) => (
              <button
                key={preset.id}
                onClick={() => {
                  setSelectedPreset((current) => (current === preset.id ? null : preset.id));
                  setCustomText("");
                }}
                className={`inline-flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  selectedPreset === preset.id
                    ? "border-amber-400 bg-amber-50 text-amber-700"
                    : "border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300 hover:bg-neutral-50"
                }`}
              >
                <Zap
                  className={`h-3.5 w-3.5 ${
                    selectedPreset === preset.id ? "text-amber-500" : "text-neutral-400"
                  }`}
                />
                {preset.label}
              </button>
            ))}
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Describe a Scenario
          </h2>
          <textarea
            rows={3}
            placeholder="e.g. What if we increase croissant stock by 20% on weekends?"
            value={scenarioText}
            onChange={(event) => {
              setSelectedPreset(null);
              setCustomText(event.target.value);
            }}
            className="w-full resize-none rounded-lg border border-neutral-300 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-neutral-400">
              BakeWise simulates the downstream alert impact using the current heuristic scenario engine.
            </p>
            <button
              onClick={() => scenarioMutation.mutate()}
              disabled={scenarioMutation.isPending || !scenarioText.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {scenarioMutation.isPending ? (
                <>
                  <Sparkles className="h-4 w-4 animate-spin" />
                  Modelling...
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

        {scenarioMutation.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {scenarioMutation.error.message}
          </div>
        )}

        {scenarioMutation.data && (
          <section className="space-y-5">
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-violet-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Impact Analysis
              </h2>
            </div>
            <ScenarioResultPanel result={scenarioMutation.data} />
          </section>
        )}
      </main>
    </div>
  );
}
