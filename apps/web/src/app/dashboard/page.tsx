"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO, scoreToRisk } from "@/lib/utils";
import Header from "@/components/Header";
import KPICard from "@/components/KPICard";
import AlertCard from "@/components/AlertCard";
import type { DailyPlan } from "@/types";

export default function DashboardPage() {
  const [date, setDate] = useState(todayISO);

  const { data, isLoading, error } = useQuery<DailyPlan>({
    queryKey: ["dailyPlan", date],
    queryFn: () => api.dailyPlan(date),
  });

  const summary = data?.summary;

  return (
    <div className="min-h-screen">
      <Header title="Dashboard" date={date}>
        <label className="flex items-center gap-2 text-sm text-neutral-600">
          Date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>
      </Header>

      <main className="p-6 space-y-6">
        {/* Error state */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            Failed to load daily plan:{" "}
            {error instanceof Error ? error.message : "unknown error"}
          </div>
        )}

        {/* KPIs */}
        <section>
          <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            Today at a Glance
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <KPICard
              title="Predicted Sales"
              value={summary ? `${summary.total_predicted_sales} units` : "—"}
              risk="low"
              loading={isLoading}
            />
            <KPICard
              title="Waste Risk Score"
              value={summary ? summary.waste_risk_score : "—"}
              sub="0 = no risk · 100 = critical"
              risk={summary ? scoreToRisk(summary.waste_risk_score) : "low"}
              loading={isLoading}
            />
            <KPICard
              title="Stockout Risk Score"
              value={summary ? summary.stockout_risk_score : "—"}
              sub="0 = no risk · 100 = critical"
              risk={summary ? scoreToRisk(summary.stockout_risk_score) : "low"}
              loading={isLoading}
            />
          </div>
        </section>

        {/* Top Actions */}
        {(summary?.top_actions?.length ?? 0) > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Top Actions
            </h2>
            <ul className="bg-white rounded-xl border border-neutral-200 shadow-sm divide-y divide-neutral-100">
              {summary!.top_actions.map((action, i) => (
                <li
                  key={i}
                  className="px-5 py-3 text-sm text-neutral-700 flex items-start gap-2"
                >
                  <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full bg-amber-100 text-amber-700 text-xs font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  {action}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* At-risk outlets */}
        {(summary?.at_risk_outlets?.length ?? 0) > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              At-Risk Outlets
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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
            <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Waste Alerts ({data?.waste_alerts?.length ?? 0})
            </h2>
            {isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((k) => (
                  <div
                    key={k}
                    className="h-16 bg-neutral-100 animate-pulse rounded-lg"
                  />
                ))}
              </div>
            ) : (data?.waste_alerts?.length ?? 0) === 0 ? (
              <p className="text-sm text-neutral-400">No waste alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {data!.waste_alerts.map((a, i) => (
                  <AlertCard
                    key={i}
                    riskLevel={a.risk_level}
                    title={a.sku_name ?? `SKU ${a.sku_id}`}
                    subtitle={a.reason}
                    meta={
                      a.waste_rate_pct != null
                        ? `Waste rate: ${a.waste_rate_pct.toFixed(1)}%`
                        : undefined
                    }
                  />
                ))}
              </div>
            )}
          </section>

          {/* Stockout alerts */}
          <section>
            <h2 className="text-sm font-semibold text-neutral-500 uppercase tracking-wide mb-3">
              Stockout Alerts ({data?.stockout_alerts?.length ?? 0})
            </h2>
            {isLoading ? (
              <div className="space-y-2">
                {[0, 1, 2].map((k) => (
                  <div
                    key={k}
                    className="h-16 bg-neutral-100 animate-pulse rounded-lg"
                  />
                ))}
              </div>
            ) : (data?.stockout_alerts?.length ?? 0) === 0 ? (
              <p className="text-sm text-neutral-400">No stockout alerts for this date.</p>
            ) : (
              <div className="space-y-2">
                {data!.stockout_alerts.map((a, i) => (
                  <AlertCard
                    key={i}
                    riskLevel={a.risk_level}
                    title={a.sku_name ?? `SKU ${a.sku_id}`}
                    subtitle={a.reason ?? a.message}
                    meta={
                      a.coverage_pct != null
                        ? `Stock coverage: ${a.coverage_pct.toFixed(1)}%`
                        : undefined
                    }
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
