"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Flame, ListChecks, ShoppingCart, TrendingUp } from "lucide-react";

import Header from "@/components/Header";
import KPICard from "@/components/KPICard";
import AlertCard from "@/components/AlertCard";
import ActionPlanPanel from "@/components/copilot/ActionPlanPanel";
import { api } from "@/lib/api";
import { scoreToRisk, todayISO } from "@/lib/utils";
import type { DailyActionsResponse, DailyPlan } from "@/types";

export default function DashboardPage() {
  const [date, setDate] = useState(todayISO);

  const dailyPlanQuery = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const actionPlanMutation = useMutation<DailyActionsResponse>({
    mutationFn: () => api.dailyActions(date),
  });

  const summary = dailyPlanQuery.data?.summary;
  const wasteRisk = scoreToRisk(summary?.waste_risk_score);
  const stockRisk = scoreToRisk(summary?.stockout_risk_score);
  const actionCount = summary?.top_actions.length ?? 0;

  return (
    <div className="min-h-screen">
      <Header title="Executive Overview" date={date}>
        <label className="flex items-center gap-2 text-sm text-neutral-500">
          Plan date
          <input
            type="date"
            value={date}
            onChange={(event) => {
              setDate(event.target.value);
              actionPlanMutation.reset();
            }}
            className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>
      </Header>

      <main className="max-w-6xl space-y-6 p-6">
        {dailyPlanQuery.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            Failed to load daily plan:{" "}
            {dailyPlanQuery.error instanceof Error ? dailyPlanQuery.error.message : "unknown error"}
          </div>
        )}

        <section>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Tomorrow at a Glance
          </h2>
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <div className="flex flex-col gap-2 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
                  Predicted Sales
                </span>
                <TrendingUp className="h-4 w-4 text-neutral-300" />
              </div>
              {dailyPlanQuery.isLoading ? (
                <div className="h-8 w-24 animate-pulse rounded bg-neutral-100" />
              ) : (
                <span className="text-2xl font-bold text-neutral-900">
                  {summary ? summary.total_predicted_sales : "-"}
                </span>
              )}
              <span className="text-xs text-neutral-400">units forecast</span>
            </div>

            <KPICard
              title="Waste Risk"
              value={summary ? summary.waste_risk_score : "-"}
              sub="0 = no risk | 100 = critical"
              risk={wasteRisk}
              loading={dailyPlanQuery.isLoading}
            />

            <KPICard
              title="Stockout Risk"
              value={summary ? summary.stockout_risk_score : "-"}
              sub="0 = no risk | 100 = critical"
              risk={stockRisk}
              loading={dailyPlanQuery.isLoading}
            />

            <div className="flex flex-col gap-2 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wide text-neutral-400">
                  Actions
                </span>
                <ListChecks className="h-4 w-4 text-neutral-300" />
              </div>
              {dailyPlanQuery.isLoading ? (
                <div className="h-8 w-12 animate-pulse rounded bg-neutral-100" />
              ) : (
                <span className="text-2xl font-bold text-neutral-900">{actionCount}</span>
              )}
              <span className="text-xs text-neutral-400">deterministic recommendations</span>
            </div>
          </div>
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              Recommended Actions
            </h2>
          </div>
          {dailyPlanQuery.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((index) => (
                <div key={index} className="h-11 animate-pulse rounded-lg bg-neutral-100" />
              ))}
            </div>
          ) : actionCount === 0 ? (
            <div className="rounded-xl border border-neutral-200 bg-white px-5 py-8 text-center text-sm text-neutral-400">
              No actions yet. Generate a plan for this date to see recommendations.
            </div>
          ) : (
            <ul className="divide-y divide-neutral-100 rounded-xl border border-neutral-200 bg-white shadow-sm">
              {summary?.top_actions.map((action, index) => (
                <li key={`${action}-${index}`} className="flex items-start gap-3 px-5 py-3 text-sm text-neutral-700">
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-100 text-xs font-bold text-amber-700">
                    {index + 1}
                  </span>
                  {action}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                AI Action Plan
              </h2>
              <p className="mt-1 text-sm text-neutral-500">
                Generate a structured copilot action plan only when you need an AI summary.
              </p>
            </div>
            <button
              onClick={() => actionPlanMutation.mutate()}
              disabled={actionPlanMutation.isPending}
              className="rounded-md bg-neutral-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-900 disabled:opacity-60"
            >
              {actionPlanMutation.isPending ? "Generating..." : "Generate AI Action Plan"}
            </button>
          </div>

          {actionPlanMutation.error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {actionPlanMutation.error instanceof Error
                ? actionPlanMutation.error.message
                : "Failed to generate action plan"}
            </div>
          )}

          {actionPlanMutation.data && <ActionPlanPanel actionPlan={actionPlanMutation.data} compact />}
        </section>

        {(summary?.at_risk_outlets.length ?? 0) > 0 && (
          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
              At-Risk Outlets
            </h2>
            <div className="flex flex-wrap gap-3">
              {summary?.at_risk_outlets.map((outletName) => (
                <div
                  key={outletName}
                  className="rounded-full border border-orange-200 bg-orange-50 px-4 py-2 text-sm font-medium text-orange-700"
                >
                  {outletName}
                </div>
              ))}
            </div>
          </section>
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Flame className="h-3.5 w-3.5 text-amber-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Waste Alerts
              </h2>
              {!dailyPlanQuery.isLoading && (
                <span className="ml-auto text-xs text-neutral-400">
                  {dailyPlanQuery.data?.waste_alerts.length ?? 0} item
                  {(dailyPlanQuery.data?.waste_alerts.length ?? 0) !== 1 && "s"}
                </span>
              )}
            </div>
            {dailyPlanQuery.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((index) => (
                  <div key={index} className="h-16 animate-pulse rounded-lg bg-neutral-100" />
                ))}
              </div>
            ) : (dailyPlanQuery.data?.waste_alerts.length ?? 0) === 0 ? (
              <p className="py-4 text-sm text-neutral-400">No waste alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {dailyPlanQuery.data?.waste_alerts.map((alert, index) => (
                  <AlertCard
                    key={`${alert.outlet_name}-${alert.sku_name}-${index}`}
                    riskLevel={alert.risk_level}
                    title={alert.sku_name}
                    subtitle={alert.reason}
                    meta={`Outlet: ${alert.outlet_name} | Daypart: ${alert.daypart}`}
                  />
                ))}
              </div>
            )}
          </section>

          <section>
            <div className="mb-3 flex items-center gap-2">
              <ShoppingCart className="h-3.5 w-3.5 text-red-500" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                Stockout Alerts
              </h2>
              {!dailyPlanQuery.isLoading && (
                <span className="ml-auto text-xs text-neutral-400">
                  {dailyPlanQuery.data?.stockout_alerts.length ?? 0} item
                  {(dailyPlanQuery.data?.stockout_alerts.length ?? 0) !== 1 && "s"}
                </span>
              )}
            </div>
            {dailyPlanQuery.isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((index) => (
                  <div key={index} className="h-16 animate-pulse rounded-lg bg-neutral-100" />
                ))}
              </div>
            ) : (dailyPlanQuery.data?.stockout_alerts.length ?? 0) === 0 ? (
              <p className="py-4 text-sm text-neutral-400">No stockout alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {dailyPlanQuery.data?.stockout_alerts.map((alert, index) => (
                  <AlertCard
                    key={`${alert.outlet_name}-${alert.sku_name}-${index}`}
                    riskLevel={alert.risk_level}
                    title={alert.sku_name}
                    subtitle={alert.reason}
                    meta={`Outlet: ${alert.outlet_name} | Daypart: ${alert.daypart}`}
                  />
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
