"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock, Database, ListChecks } from "lucide-react";

import PageHeader from "@/components/PageHeader";
import ExplainButton from "@/components/copilot/ExplainButton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { planningApi, type DailyPlanLatestResponse, type DailyPlanTopAction } from "@/lib/api/planning";
import { todayISO } from "@/lib/utils";

export default function DashboardPage() {
  const [date, setDate] = useState(todayISO);
  const { t } = useLanguage();

  const planQuery = useQuery<DailyPlanLatestResponse>({
    queryKey: ["latestDailyPlan", date],
    queryFn: () => planningApi.latestPlan(date),
    staleTime: 30_000,
  });

  const plan = planQuery.data;
  const topActions = useMemo(() => plan?.top_actions ?? [], [plan?.top_actions]);
  const topExceptions = topActions.slice(0, 3);
  const summary = plan?.summary;
  const stockoutExposure = summary?.total_stockout_exposure_rm ?? 0;
  const wasteExposure = summary?.total_waste_exposure_rm ?? 0;
  const shortageCount = summary?.ingredient_shortage_count ?? 0;
  const pendingActions = summary?.pending_action_count ?? 0;

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <PageHeader title={t("dashboard.title", "Business Overview")} description={t("dashboard.description", "Monitor tomorrow's operations, risks, and required actions.")} date={date}>
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          {t("common.planDate", "Plan date")}
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            className="rounded-md border border-input bg-background px-3 py-1.5 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
          />
        </label>
      </PageHeader>

      <main className="mx-auto w-full space-y-6">
        {planQuery.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {t("dashboard.failedDailyPlan", "Failed to load daily plan")}:{" "}
            {planQuery.error instanceof Error ? planQuery.error.message : "unknown error"}
          </div>
        )}

        {planQuery.isLoading && (
          <div className="space-y-6">
            <section className="grid gap-4 lg:grid-cols-2">
              <Skeleton className="h-40" />
              <Skeleton className="h-40" />
            </section>
            <section className="grid gap-4 md:grid-cols-4">
              {[0, 1, 2, 3].map((index) => (
                <Skeleton key={index} className="h-32" />
              ))}
            </section>
          </div>
        )}

        {!planQuery.isLoading && !plan && !planQuery.error && (
          <Card>
            <CardContent className="py-8 text-sm text-neutral-500">
              {t("dashboard.noDailyPlan", "No backend daily plan is available for this date.")}
            </CardContent>
          </Card>
        )}

        {plan && (
          <div className="space-y-6">
            <section className="grid gap-4 lg:grid-cols-2">
              <DashboardBriefCard topActions={topActions} />
              <Card>
                <CardHeader>
                  <CardTitle>{t("dashboard.readiness", "Tomorrow readiness")}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <ReadinessItem
                    icon={<Database className="h-4 w-4" />}
                    label={t("dashboard.forecastRun", "Forecast run")}
                    value={plan?.forecast_run_id || (planQuery.isLoading ? "Loading" : "Missing")}
                    tone={plan?.forecast_run_id ? "ok" : "warn"}
                  />
                  <ReadinessItem
                    icon={<ListChecks className="h-4 w-4" />}
                    label={t("dashboard.prepPlan", "Prep plan")}
                    value={pendingActions > 0 ? `${pendingActions} pending` : "Ready"}
                    tone={pendingActions > 0 ? "warn" : "ok"}
                  />
                  <ReadinessItem
                    icon={<AlertTriangle className="h-4 w-4" />}
                    label={t("dashboard.replenishment", "Replenishment")}
                    value={shortageCount > 0 ? `${shortageCount} shortages` : "No shortage"}
                    tone={shortageCount > 0 ? "warn" : "ok"}
                  />
                  <ReadinessItem
                    icon={<Clock className="h-4 w-4" />}
                    label={t("dashboard.approval", "Approval")}
                    value={pendingActions > 0 ? "Pending review" : "Approved"}
                    tone={pendingActions > 0 ? "warn" : "ok"}
                  />
                </CardContent>
              </Card>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
              <KpiCard
                label={t("dashboard.fullPlanExposure", "Full-plan exposure")}
                value={`RM ${Math.round(stockoutExposure + wasteExposure)}`}
                trendDirection="neutral"
                trend={summary?.scope ?? "full_plan"}
                subtitle={t("dashboard.exposureSubtitle", "Backend full-plan stockout and waste exposure combined.")}
              />
              <KpiCard
                label={t("dashboard.fullPlanStockoutExposure", "Full-plan stockout exposure")}
                value={`RM ${Math.round(stockoutExposure)}`}
                trendDirection="neutral"
                trend="Full plan"
                subtitle={t("dashboard.stockoutSubtitle", "Potential lost margin from under-prep across the backend plan.")}
                action={
                  <ExplainButton
                    label={t("dashboard.explainStockout", "Explain")}
                    title={t("dashboard.explainStockoutTitle", "Stockout exposure")}
                    contextType="kpi"
                    evidence={{
                      metric: "full_plan_stockout_exposure_rm",
                      value_rm: stockoutExposure,
                      scope: summary?.scope ?? "full_plan",
                      pending_action_count: pendingActions,
                      source: "backend_daily_plan_summary",
                    }}
                  />
                }
              />
              <KpiCard
                label={t("dashboard.fullPlanWasteExposure", "Full-plan waste exposure")}
                value={`RM ${Math.round(wasteExposure)}`}
                trendDirection="neutral"
                trend="Full plan"
                subtitle={t("dashboard.wasteSubtitle", "Potential spoilage exposure from over-prep across the backend plan.")}
                action={
                  <ExplainButton
                    label={t("dashboard.explainWaste", "Explain")}
                    title={t("dashboard.explainWasteTitle", "Waste exposure")}
                    contextType="kpi"
                    evidence={{
                      metric: "full_plan_waste_exposure_rm",
                      value_rm: wasteExposure,
                      scope: summary?.scope ?? "full_plan",
                      ingredient_shortage_count: shortageCount,
                      source: "backend_daily_plan_summary",
                    }}
                  />
                }
              />
              <KpiCard
                label={t("dashboard.pendingActions", "Pending Approvals")}
                value={String(pendingActions)}
                trendDirection={pendingActions > 0 ? "down" : "up"}
                trend={pendingActions > 0 ? "Requires Attention" : "All Cleared"}
                subtitle={t("dashboard.pendingSubtitle", "Number of backend planning actions still awaiting manager review.")}
              />
            </section>

            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  {t("dashboard.topExceptions", "Top 3 exceptions")}
                </h2>
                <div className="flex items-center gap-3">
                  <Link
                    href="/daily-planning"
                    className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-600"
                  >
                    {t("dashboard.reviewDailyPlan", "Review Tomorrow's Daily Plan")}
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                  <Link
                    href="/risk-center"
                    className="inline-flex items-center gap-2 rounded-md border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-50"
                  >
                    {t("dashboard.openRiskCenter", "Open Risk Center")}
                  </Link>
                </div>
              </div>

              {planQuery.isLoading ? (
                <div className="space-y-2">
                  {[0, 1, 2].map((index) => (
                    <Skeleton key={index} className="h-20" />
                  ))}
                </div>
              ) : topExceptions.length === 0 ? (
                <Card>
                  <CardContent className="py-8 text-center text-sm text-neutral-500">
                    {t("dashboard.noExceptions", "No exceptions for this plan date.")}
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-3">
                  {topExceptions.map((action, index) => (
                    <Card key={action.id}>
                      <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-start gap-3">
                          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-amber-100 text-sm font-bold text-amber-700">
                            {index + 1}
                          </span>
                          <div>
                            <p className="font-semibold text-neutral-900">
                              {action.outlet_name} - {action.sku_name} - {action.daypart}
                            </p>
                            <p className="text-sm text-neutral-600">
                              Prepare {action.recommended_prep} units. Risk: RM{" "}
                              {Math.round(
                                action.financial_exposure.stockout_exposure_rm +
                                  action.financial_exposure.waste_exposure_rm
                              )}{" "}
                              exposure.
                            </p>
                          </div>
                        </div>
                        <Link
                          href="/daily-planning"
                          className="text-sm font-semibold text-amber-700 hover:text-amber-800"
                        >
                          {t("dashboard.review", "Review")}
                        </Link>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}

function ReadinessItem({
  icon,
  label,
  value,
  tone,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tone: "ok" | "warn";
}) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {icon}
        {label}
      </div>
      <div className="flex items-center gap-2">
        {tone === "ok" ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-amber-600" />
        )}
        <span className="text-sm font-semibold text-neutral-900">{value}</span>
      </div>
    </div>
  );
}

function DashboardBriefCard({ topActions }: { topActions: DailyPlanTopAction[] }) {
  const { t } = useLanguage();
  
  if (topActions.length === 0) return null;
  
  const topAction = topActions[0];
  const shortage = topActions.flatMap(a => a.replenishment).find(l => l.shortage_qty > 0);
  
  let brief = t(
    "dashboard.brief.risk",
    "Tomorrow's main risk involves {{sku}} demand at {{outlet}}.",
    { sku: topAction.sku_name, outlet: topAction.outlet_name }
  );
  
  if (shortage) {
    brief += " " + t(
      "dashboard.brief.shortage",
      "{{ingredient}} shortage affects prep.",
      { ingredient: shortage.ingredient_name }
    );
  }
  
  brief += " " + t("dashboard.brief.cta", "Review and approve the plan.");

  return (
    <Card className="border-l-4 border-l-amber-500 bg-amber-50/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-amber-900">{t("dashboard.tomorrowBrief", "Tomorrow Brief")}</CardTitle>
          <span className="rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">
            {t("dashboard.briefSource", "Operations brief")}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-amber-800">{brief}</p>
      </CardContent>
    </Card>
  );
}
