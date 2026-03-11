"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import type { ScenarioResult } from "@/types";

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
        <section className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-neutral-700 mb-3">Daily Brief</h2>
          <button
            onClick={() => briefMutation.mutate()}
            disabled={briefMutation.isPending}
            className="rounded-md bg-amber-500 hover:bg-amber-600 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
          >
            {briefMutation.isPending ? "Generating…" : "Generate Brief"}
          </button>
          {briefMutation.error && (
            <p className="mt-3 text-sm text-red-600">
              {briefMutation.error instanceof Error
                ? briefMutation.error.message
                : "Failed to generate brief"}
            </p>
          )}
          {brief && (
            <div className="mt-4 rounded-lg bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-neutral-800 whitespace-pre-wrap leading-relaxed">
              {brief}
            </div>
          )}
        </section>

        {/* Scenario runner */}
        <section className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-neutral-700 mb-3">What-If Scenario</h2>
          <textarea
            rows={3}
            placeholder='e.g. "What if we increase croissant production by 20% tomorrow?"'
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
          <button
            onClick={() => scenarioMutation.mutate()}
            disabled={scenarioMutation.isPending || !scenario.trim()}
            className="mt-3 rounded-md bg-neutral-800 hover:bg-neutral-900 text-white px-4 py-1.5 text-sm font-medium disabled:opacity-60 transition-colors"
          >
            {scenarioMutation.isPending ? "Running…" : "Run Scenario"}
          </button>

          {scenarioMutation.error && (
            <p className="mt-3 text-sm text-red-600">
              {scenarioMutation.error instanceof Error
                ? scenarioMutation.error.message
                : "Scenario failed"}
            </p>
          )}

          {scenarioMutation.data && (
            <div className="mt-4 space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Baseline waste alerts</p>
                  <p className="text-xl font-bold text-neutral-800">
                    {scenarioMutation.data.baseline_waste_alerts}
                  </p>
                </div>
                <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Projected waste alerts</p>
                  <p className="text-xl font-bold text-amber-600">
                    {scenarioMutation.data.projected_waste_alerts}
                  </p>
                </div>
                <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Baseline stockout alerts</p>
                  <p className="text-xl font-bold text-neutral-800">
                    {scenarioMutation.data.baseline_stockout_alerts}
                  </p>
                </div>
                <div className="rounded-lg bg-neutral-50 border border-neutral-200 p-3">
                  <p className="text-xs text-neutral-500 mb-1">Projected stockout alerts</p>
                  <p className="text-xl font-bold text-red-600">
                    {scenarioMutation.data.projected_stockout_alerts}
                  </p>
                </div>
              </div>
              <div className="rounded-lg bg-amber-50 border border-amber-100 px-4 py-3 text-sm text-neutral-800 whitespace-pre-wrap leading-relaxed">
                {scenarioMutation.data.explanation}
              </div>
              {scenarioMutation.data.affected_skus?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {scenarioMutation.data.affected_skus.map((sku, i) => (
                    <span
                      key={i}
                      className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600"
                    >
                      {sku}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
