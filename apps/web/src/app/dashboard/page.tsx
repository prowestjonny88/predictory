"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock, Database, ListChecks } from "lucide-react";

import PageHeader from "@/components/PageHeader";
import { useCurrency } from "@/components/CurrencyProvider";
import ExplainButton from "@/components/copilot/ExplainButton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KpiCard } from "@/components/ui/kpi-card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { planningApi, type DailyPlanLatestResponse, type DailyPlanTopAction } from "@/lib/api/planning";
import { translateDaypart } from "@/lib/i18n";
import { tomorrowISO } from "@/lib/utils";

export default function DashboardPage() {
  const [date, setDate] = useState(tomorrowISO);
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();

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
  const priorityActionCount = topActions.length;
  const reviewedPriorityCount = topActions.filter((action) => action.status !== "pending").length;
  const reviewProgressPct =
    priorityActionCount > 0 ? Math.round((reviewedPriorityCount / priorityActionCount) * 100) : 100;

  return (
    <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
      <PageHeader
        title={t("dashboard.title", "Tomorrow Operations Brief")}
        description={t(
          "dashboard.description",
          "Review tomorrow's bake plan, waste risk, stockout risk, and pending manager decisions."
        )}
        date={date}
      >
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
            {planQuery.error instanceof Error ? planQuery.error.message : t("common.unknownError", "Unknown error")}
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
              <DashboardBriefCard
                topActions={topActions}
                stockoutExposure={stockoutExposure}
                wasteExposure={wasteExposure}
                pendingActions={pendingActions}
              />
              <Card>
                <CardHeader>
                  <CardTitle>{t("dashboard.readiness", "Tomorrow readiness")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <ReadinessItem
                      icon={<Database className="h-4 w-4" />}
                      label={t("dashboard.forecastRun", "Forecast run")}
                      value={plan?.forecast_run_id || (planQuery.isLoading ? t("common.loading", "Loading...") : t("planning.missing", "missing"))}
                      tone={plan?.forecast_run_id ? "ok" : "warn"}
                    />
                    <ReadinessItem
                      icon={<ListChecks className="h-4 w-4" />}
                      label={t("dashboard.priorityPlan", "Priority plan")}
                      value={
                        pendingActions > 0
                          ? t("dashboard.priorityRatio", "{{priority}} priority / {{total}} total", {
                              priority: priorityActionCount,
                              total: pendingActions,
                            })
                          : t("common.ready", "Ready")
                      }
                      tone={pendingActions > 0 ? "warn" : "ok"}
                    />
                    <ReadinessItem
                      icon={<AlertTriangle className="h-4 w-4" />}
                      label={t("dashboard.replenishment", "Replenishment")}
                      value={
                        shortageCount > 0
                          ? t("dashboard.shortages", "{{count}} shortages", { count: shortageCount })
                          : t("dashboard.noShortage", "No shortage")
                      }
                      tone={shortageCount > 0 ? "warn" : "ok"}
                    />
                    <ReadinessItem
                      icon={<Clock className="h-4 w-4" />}
                      label={t("dashboard.approval", "Approval")}
                      value={
                        pendingActions > 0
                          ? t("dashboard.pendingReview", "Pending review")
                          : t("common.status.approved", "Approved")
                      }
                      tone={pendingActions > 0 ? "warn" : "ok"}
                    />
                  </div>
                  <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                    <div className="mb-2 flex items-center justify-between text-xs font-medium text-neutral-500">
                      <span>
                        {t("dashboard.reviewProgress", "{{reviewed}} of {{total}} priority decisions reviewed", {
                          reviewed: reviewedPriorityCount,
                          total: priorityActionCount,
                        })}
                      </span>
                      <span>{reviewProgressPct}%</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-neutral-200">
                      <div className="h-full rounded-full bg-amber-500" style={{ width: `${reviewProgressPct}%` }} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </section>

            <section className="grid gap-4 md:grid-cols-4">
              <KpiCard
                label={t("dashboard.fullPlanExposure", "Full-plan exposure")}
                value={formatCurrency(stockoutExposure + wasteExposure, language, {
                  maximumFractionDigits: 0,
                  minimumFractionDigits: 0,
                })}
                trendDirection="neutral"
                trend={summary?.scope === "full_plan" || !summary?.scope ? t("common.fullPlan", "Full plan") : summary.scope}
                subtitle={t("dashboard.exposureSubtitle", "Backend full-plan stockout and waste exposure combined.")}
              />
              <KpiCard
                label={t("dashboard.fullPlanStockoutExposure", "Full-plan stockout exposure")}
                value={formatCurrency(stockoutExposure, language, {
                  maximumFractionDigits: 0,
                  minimumFractionDigits: 0,
                })}
                trendDirection="neutral"
                trend={t("common.fullPlan", "Full plan")}
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
                value={formatCurrency(wasteExposure, language, {
                  maximumFractionDigits: 0,
                  minimumFractionDigits: 0,
                })}
                trendDirection="neutral"
                trend={t("common.fullPlan", "Full plan")}
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
                label={t("dashboard.priorityDecisions", "Priority Decisions")}
                value={String(priorityActionCount)}
                trendDirection={pendingActions > 0 ? "down" : "up"}
                trend={
                  pendingActions > 0
                    ? t("dashboard.totalPlanLines", "{{count}} total plan lines", { count: pendingActions })
                    : t("dashboard.allCleared", "All Cleared")
                }
                subtitle={t(
                  "dashboard.prioritySubtitle",
                  "Managers review priority decisions first and bulk-approve low-risk lines."
                )}
              />
            </section>

            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  {t("dashboard.topDecisions", "Top decisions to review")}
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
                              {action.outlet_name} - {action.sku_name} - {translateDaypart(language, action.daypart)}
                            </p>
                            <p className="text-sm text-neutral-600">
                              {t("dashboard.actionRiskSummary", "Prepare {{units}} units. Risk: {{amount}} exposure.", {
                                units: action.recommended_prep,
                                amount: formatCurrency(
                                  action.financial_exposure.stockout_exposure_rm +
                                    action.financial_exposure.waste_exposure_rm,
                                  language,
                                  { maximumFractionDigits: 0, minimumFractionDigits: 0 }
                                ),
                              })}
                            </p>
                          </div>
                        </div>
                        <Link
                          href="/daily-planning"
                          className="text-sm font-semibold text-amber-700 hover:text-amber-800"
                        >
                          {t("dashboard.reviewDecision", "Review decision")}
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

function DashboardBriefCard({
  topActions,
  stockoutExposure,
  wasteExposure,
  pendingActions,
}: {
  topActions: DailyPlanTopAction[];
  stockoutExposure: number;
  wasteExposure: number;
  pendingActions: number;
}) {
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();
  
  if (topActions.length === 0) return null;
  
  const topAction = topActions[0];
  const totalExposure = stockoutExposure + wasteExposure;
  const dominantRisk =
    stockoutExposure >= wasteExposure
      ? t("dashboard.brief.stockoutDominant", "Stockout risk is the dominant exposure.")
      : t("dashboard.brief.wasteDominant", "Waste risk is the dominant exposure.");
  const topDecision = t(
    "dashboard.brief.topDecision",
    "Top decision: prepare {{units}} units of {{sku}} for {{outlet}} {{daypart}}.",
    {
      units: topAction.recommended_prep,
      sku: topAction.sku_name,
      outlet: topAction.outlet_name,
      daypart: topAction.daypart,
    }
  );

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
      <CardContent className="space-y-2 text-sm text-amber-900">
        <p>{dominantRisk}</p>
        <p>
          {t("dashboard.brief.exposureCurrency", "Full-plan exposure: {{amount}}.", {
            amount: formatCurrency(totalExposure, language, {
              maximumFractionDigits: 0,
              minimumFractionDigits: 0,
            }),
          })}
        </p>
        <p>{topDecision}</p>
        <p>
          {t("dashboard.brief.nextStep", "Next step: review the {{count}} priority decisions before bulk approval.", {
            count: topActions.length,
          })}
          {pendingActions > topActions.length
            ? ` ${t("dashboard.brief.totalLines", "{{count}} total plan lines remain in the backend plan.", {
                count: pendingActions,
              })}`
            : ""}
        </p>
      </CardContent>
    </Card>
  );
}
