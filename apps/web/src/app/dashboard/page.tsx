"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO, scoreToRisk } from "@/lib/utils";
import Header from "@/components/Header";
import KPICard from "@/components/KPICard";
import AlertCard from "@/components/AlertCard";
import { TrendingUp, Flame, ShoppingCart, ListChecks } from "lucide-react";
import type { DailyPlan } from "@/types";

export default function DashboardPage() {
  const [date, setDate] = useState(todayISO);

  const { data, isLoading, error } = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const summary = data?.summary;

  const wasteRisk  = scoreToRisk(summary?.waste_risk_score);
  const stockRisk  = scoreToRisk(summary?.stockout_risk_score);
  const actionCount = summary?.top_actions?.length ?? 0;

  return (
    <div className="min-h-screen">
      <Header title="Executive Overview" date={date}>
        <label className="flex items-center gap-2 text-sm text-neutral-500">
          Plan date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>
      </Header>

      <main className="p-6 space-y-6 max-w-6xl">
        {/* Error banner */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            Failed to load daily plan:{" "}
            {error instanceof Error ? error.message : "unknown error"}
          </div>
        )}

        {/* KPI row */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Tomorrow at a Glance
          </h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Predicted Sales */}
            <div className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Predicted Sales</span>
                <TrendingUp className="h-4 w-4 text-neutral-300" />
              </div>
              {isLoading ? (
                <div className="h-8 w-24 bg-neutral-100 animate-pulse rounded" />
              ) : (
                <span className="text-2xl font-bold text-neutral-900">
                  {summary ? summary.total_predicted_sales : "—"}
                </span>
              )}
              <span className="text-xs text-neutral-400">units forecast</span>
            </div>

            {/* Waste Risk */}
            <KPICard
              title="Waste Risk"
              value={summary ? summary.waste_risk_score : "—"}
              sub="0 = no risk · 100 = critical"
              risk={wasteRisk}
              loading={isLoading}
            />

            {/* Stockout Risk */}
            <KPICard
              title="Stockout Risk"
              value={summary ? summary.stockout_risk_score : "—"}
              sub="0 = no risk · 100 = critical"
              risk={stockRisk}
              loading={isLoading}
            />

            {/* Actions */}
            <div className="bg-white rounded-xl border border-neutral-200 shadow-sm p-5 flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-neutral-400 uppercase tracking-wide">Actions</span>
                <ListChecks className="h-4 w-4 text-neutral-300" />
              </div>
              {isLoading ? (
                <div className="h-8 w-12 bg-neutral-100 animate-pulse rounded" />
              ) : (
                <span className="text-2xl font-bold text-neutral-900">{actionCount}</span>
              )}
              <span className="text-xs text-neutral-400">recommended today</span>
            </div>
          </div>
        </section>

        {/* Top Actions */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Recommended Actions
          </h2>
          {isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((k) => (
                <div key={k} className="h-11 bg-neutral-100 animate-pulse rounded-lg" />
              ))}
            </div>
          ) : actionCount === 0 ? (
            <div className="bg-white rounded-xl border border-neutral-200 px-5 py-8 text-sm text-neutral-400 text-center">
              No actions yet — select a date with a generated plan to see recommendations.
            </div>
          ) : (
            <ul className="bg-white rounded-xl border border-neutral-200 shadow-sm divide-y divide-neutral-100">
              {summary!.top_actions.map((action, i) => (
                <li key={i} className="px-5 py-3 text-sm text-neutral-700 flex items-start gap-3">
                  <span className="mt-0.5 h-5 w-5 shrink-0 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  {action}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* At-risk outlets */}
        {(summary?.at_risk_outlets?.length ?? 0) > 0 && (
          <section>
            <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              At-Risk Outlets
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {summary!.at_risk_outlets.map((outlet, i) => (
                <AlertCard
                  key={i}
                  riskLevel={outlet.risk_level}
                  title={outlet.outlet_name ?? `Outlet ${outlet.outlet_id}`}
                  subtitle={outlet.message ?? outlet.reason}
                />
              ))}
            </div>
          </section>
        )}

        {/* Two-column: waste + stockout alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Waste alerts */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Flame className="h-3.5 w-3.5 text-amber-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                Waste Alerts
              </h2>
              {!isLoading && (
                <span className="ml-auto text-xs text-neutral-400">
                  {data?.waste_alerts?.length ?? 0} item{(data?.waste_alerts?.length ?? 0) !== 1 && "s"}
                </span>
              )}
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((k) => (
                  <div key={k} className="h-16 bg-neutral-100 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : (data?.waste_alerts?.length ?? 0) === 0 ? (
              <p className="text-sm text-neutral-400 py-4">No waste alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {data!.waste_alerts.map((a, i) => (
                  <AlertCard
                    key={i}
                    riskLevel={a.risk_level}
                    title={a.sku_name ?? `SKU ${a.sku_id}`}
                    subtitle={a.reason}
                    meta={[
                      a.outlet_name ? `Outlet: ${a.outlet_name}` : null,
                      a.waste_rate_pct != null ? `Waste rate: ${a.waste_rate_pct.toFixed(1)}%` : null,
                    ].filter(Boolean).join(" · ") || undefined}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Stockout alerts */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <ShoppingCart className="h-3.5 w-3.5 text-red-500" />
              <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide">
                Stockout Alerts
              </h2>
              {!isLoading && (
                <span className="ml-auto text-xs text-neutral-400">
                  {data?.stockout_alerts?.length ?? 0} item{(data?.stockout_alerts?.length ?? 0) !== 1 && "s"}
                </span>
              )}
            </div>
            {isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((k) => (
                  <div key={k} className="h-16 bg-neutral-100 animate-pulse rounded-lg" />
                ))}
              </div>
            ) : (data?.stockout_alerts?.length ?? 0) === 0 ? (
              <p className="text-sm text-neutral-400 py-4">No stockout alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {data!.stockout_alerts.map((a, i) => (
                  <AlertCard
                    key={i}
                    riskLevel={a.risk_level}
                    title={a.sku_name ?? `SKU ${a.sku_id}`}
                    subtitle={a.reason ?? a.message}
                    meta={[
                      a.outlet_name ? `Outlet: ${a.outlet_name}` : null,
                      a.coverage_pct != null ? `Stock coverage: ${a.coverage_pct.toFixed(1)}%` : null,
                    ].filter(Boolean).join(" · ") || undefined}
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
