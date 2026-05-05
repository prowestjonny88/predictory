"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { GitBranch, Sparkles, Zap } from "lucide-react";

import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import ScenarioResultPanel from "@/components/scenario/ScenarioResultPanel";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import type { ScenarioResult } from "@/types";

import { useQuery } from "@tanstack/react-query";

export default function ScenarioPlannerPage() {
  const [date, setDate] = useState(todayISO);
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const [customText, setCustomText] = useState("");
  const { language, t } = useLanguage();

  const { data: outlets = [] } = useQuery({ queryKey: ["outlets"], queryFn: api.outlets });
  const { data: skus = [] } = useQuery({ queryKey: ["skus"], queryFn: api.skus });

  const outlet1 = outlets[0]?.name ?? "Bangsar";
  const outlet2 = outlets[1]?.name ?? "KLCC";
  const outlet3 = outlets[2]?.name ?? "Mid Valley";
  const sku1 = skus.find(s => s.name.toLowerCase().includes("croissant"))?.name ?? skus[0]?.name ?? "Croissant";

  const getPresets = () => {
    switch (language) {
      case "ms":
        return [
          { id: "cut", text: `Kurangkan prep ${sku1} di ${outlet1} sebanyak 15%`, label: `Kurangkan prep ${sku1} di ${outlet1} sebanyak 15%` },
          { id: "promo", text: `Promosi di ${outlet2} sebanyak 25%`, label: `Promosi di ${outlet2} sebanyak 25%` },
          { id: "spike", text: `Tingkatkan prep ${sku1} di ${outlet3} sebanyak 30%`, label: `Tingkatkan prep ${sku1} di ${outlet3} sebanyak 30%` },
        ];
      case "zh-CN":
        return [
          { id: "cut", text: `将 ${outlet1} 的 ${sku1} 备货减少 15%`, label: `将 ${outlet1} 的 ${sku1} 备货减少 15%` },
          { id: "promo", text: `在 ${outlet2} 做 25% 促销活动`, label: `在 ${outlet2} 做 25% 促销活动` },
          { id: "spike", text: `将 ${outlet3} 的 ${sku1} 备货增加 30%`, label: `将 ${outlet3} 的 ${sku1} 备货增加 30%` },
        ];
      default:
        return [
          { id: "cut", text: `Reduce ${sku1} prep at ${outlet1} by 15%`, label: `Reduce ${sku1} prep at ${outlet1} by 15%` },
          { id: "promo", text: `Promo at ${outlet2} by 25%`, label: `Promo at ${outlet2} by 25%` },
          { id: "spike", text: `Increase ${sku1} prep at ${outlet3} by 30%`, label: `Increase ${sku1} prep at ${outlet3} by 30%` },
        ];
    }
  };

  const presets = getPresets();
  const scenarioText = selectedPreset
    ? (presets.find((preset) => preset.id === selectedPreset)?.text ?? "")
    : customText;

  const scenarioMutation = useMutation<ScenarioResult, Error>({
    mutationFn: () => api.runScenario(scenarioText, date, language),
  });

  return (
    <div className="min-h-screen">
      <Header title={t("scenario.title", "Scenario Planner")} date={date}>
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

      <main className="max-w-4xl space-y-6 p-6 page-enter">
        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {t("scenario.quickScenarios", "Quick Scenarios")}
          </h2>
          <div className="flex flex-wrap gap-3">
            {presets.map((preset) => (
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
            {t("scenario.describe", "Describe a Scenario")}
          </h2>
          <textarea
            rows={3}
            placeholder={t(
              "scenario.placeholder",
              "e.g. What if we increase croissant stock by 20% on weekends?"
            )}
            value={scenarioText}
            onChange={(event) => {
              setSelectedPreset(null);
              setCustomText(event.target.value);
            }}
            className="w-full resize-none rounded-lg border border-neutral-300 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <div className="mt-3 flex items-center justify-between">
            <p className="text-xs text-neutral-400">
              {t(
                "scenario.heuristicHelp",
                "Predictory simulates the downstream alert impact using the current heuristic scenario engine."
              )}
            </p>
            <button
              onClick={() => scenarioMutation.mutate()}
              disabled={scenarioMutation.isPending || !scenarioText.trim()}
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-5 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {scenarioMutation.isPending ? (
                <>
                  <Sparkles className="h-4 w-4 animate-spin" />
                  {t("scenario.modelling", "Modelling...")}
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  {t("scenario.run", "Run Scenario")}
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

        {scenarioMutation.data ? (
          <section className="space-y-5 animate-fade-in">
            <div className="flex items-center gap-2">
              <GitBranch className="h-4 w-4 text-violet-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("scenario.impactAnalysis", "Impact Analysis")}
              </h2>
            </div>
            <ScenarioResultPanel result={scenarioMutation.data} />
          </section>
        ) : !scenarioMutation.isPending && !scenarioMutation.error && (
          <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-neutral-200 bg-white py-16 text-center">
            <GitBranch className="h-10 w-10 text-neutral-200" />
            <p className="text-sm font-medium text-neutral-500">
              {t("scenario.emptyTitle", "Run a scenario to see the impact analysis")}
            </p>
            <p className="text-xs text-neutral-400 max-w-xs">
              {t(
                "scenario.emptySubtitle",
                "Choose a quick scenario above or describe your own, then click Run Scenario to model the downstream effects on waste, stockout, and prep volumes."
              )}
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
