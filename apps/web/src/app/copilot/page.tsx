"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Sparkles, Zap } from "lucide-react";

import ActionPlanPanel from "@/components/copilot/ActionPlanPanel";
import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import ScenarioResultPanel from "@/components/scenario/ScenarioResultPanel";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import type { DailyActionsResponse, DailyBriefResponse, ScenarioResult } from "@/types";

export default function CopilotPage() {
  const [date, setDate] = useState(todayISO);
  const [scenario, setScenario] = useState("");
  const { language, t } = useLanguage();

  const briefMutation = useMutation<DailyBriefResponse>({
    mutationFn: () => api.dailyBrief(date, language),
  });

  const dailyActionsMutation = useMutation<DailyActionsResponse>({
    mutationFn: () => api.dailyActions(date, 5, language),
  });

  const scenarioMutation = useMutation<ScenarioResult>({
    mutationFn: () => api.runScenario(scenario, date, language),
  });

  return (
    <div className="min-h-screen">
      <Header title={t("copilot.title", "AI Copilot")} date={date}>
        <input
          type="date"
          value={date}
          onChange={(event) => {
            setDate(event.target.value);
            briefMutation.reset();
            dailyActionsMutation.reset();
            scenarioMutation.reset();
          }}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="max-w-4xl space-y-6 p-6">
        <section className="space-y-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-amber-500" />
            <h2 className="text-sm font-semibold text-neutral-700">
              {t("copilot.dailyBrief", "Daily Brief")}
            </h2>
          </div>
          <p className="text-xs text-neutral-500">
            {t(
              "copilot.dailyBriefHelp",
              "Generate a plain-language summary of forecast, risks, and recommended next steps."
            )}
          </p>
          <button
            onClick={() => briefMutation.mutate()}
            disabled={briefMutation.isPending}
            className="rounded-md bg-amber-500 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-60"
          >
            {briefMutation.isPending
              ? t("common.generating", "Generating...")
              : t("copilot.generateBrief", "Generate Brief")}
          </button>
          {briefMutation.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {briefMutation.error instanceof Error
                ? briefMutation.error.message
                : t("copilot.failedBrief", "Failed to generate brief")}
            </div>
          )}
          {briefMutation.data && (
            <div className="whitespace-pre-wrap rounded-lg border border-amber-100 bg-amber-50 px-4 py-4 text-sm leading-relaxed text-neutral-800">
              {briefMutation.data.brief}
            </div>
          )}
        </section>

        <section className="space-y-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-500" />
            <h2 className="text-sm font-semibold text-neutral-700">
              {t("copilot.dailyActions", "Daily Actions")}
            </h2>
          </div>
          <p className="text-xs text-neutral-500">
            {t(
              "copilot.dailyActionsHelp",
              "Generate the structured AI action plan only when you want the copilot layer."
            )}
          </p>
          <button
            onClick={() => dailyActionsMutation.mutate()}
            disabled={dailyActionsMutation.isPending}
            className="rounded-md bg-neutral-800 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-neutral-900 disabled:opacity-60"
          >
            {dailyActionsMutation.isPending
              ? t("common.generating", "Generating...")
              : t("copilot.generateActionPlan", "Generate Action Plan")}
          </button>
          {dailyActionsMutation.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {dailyActionsMutation.error instanceof Error
                ? dailyActionsMutation.error.message
                : t("copilot.failedActionPlan", "Failed to generate action plan")}
            </div>
          )}
          {dailyActionsMutation.data && <ActionPlanPanel actionPlan={dailyActionsMutation.data} />}
        </section>

        <section className="space-y-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Zap className="h-4 w-4 text-sky-500" />
            <h2 className="text-sm font-semibold text-neutral-700">
              {t("copilot.whatIf", "What-If Scenario")}
            </h2>
          </div>
          <p className="text-xs text-neutral-500">
            {t(
              "copilot.whatIfHelp",
              "Describe a change and inspect the heuristic effect on waste and stockout alerts."
            )}
          </p>
          <textarea
            rows={3}
            placeholder={t(
              "copilot.scenarioPlaceholder",
              "e.g. \"Cut croissant prep at Bangsar by 15%\""
            )}
            value={scenario}
            onChange={(event) => setScenario(event.target.value)}
            className="w-full resize-none rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
          <button
            onClick={() => scenarioMutation.mutate()}
            disabled={scenarioMutation.isPending || !scenario.trim()}
            className="rounded-md bg-neutral-800 px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-neutral-900 disabled:opacity-60"
          >
            {scenarioMutation.isPending
              ? t("common.running", "Running...")
              : t("copilot.runScenario", "Run Scenario")}
          </button>

          {scenarioMutation.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
              {scenarioMutation.error instanceof Error
                ? scenarioMutation.error.message
                : t("copilot.failedScenario", "Scenario failed")}
            </div>
          )}

          {scenarioMutation.data && <ScenarioResultPanel result={scenarioMutation.data} />}
        </section>
      </main>
    </div>
  );
}
