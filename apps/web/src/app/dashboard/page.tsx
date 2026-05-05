"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CheckCircle2, Clock, Database, ListChecks } from "lucide-react";

import Header from "@/components/Header";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
  const stockoutExposure = topActions.reduce(
    (sum, action) => sum + action.financial_exposure.stockout_exposure_rm,
    0
  );
  const wasteExposure = topActions.reduce(
    (sum, action) => sum + action.financial_exposure.waste_exposure_rm,
    0
  );
  const shortageCount = useMemo(
    () =>
      topActions.flatMap((action) => action.replenishment).filter((line) => line.shortage_qty > 0)
        .length,
    [topActions]
  );
  const pendingActions = topActions.filter((action) => action.status !== "accepted").length;

  return (
    <div className="min-h-screen">
      <Header title={t("dashboard.title", "Business Overview")} date={date}>
        <label className="flex items-center gap-2 text-sm text-neutral-500">
          {t("common.planDate", "Plan date")}
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>
      </Header>

      <main className="mx-auto max-w-6xl space-y-6 p-6">
        {planQuery.error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {t("dashboard.failedDailyPlan", "Failed to load daily plan")}:{" "}
            {planQuery.error instanceof Error ? planQuery.error.message : "unknown error"}
          </div>
        )}

        {planQuery.isLoading && (
          <Card>
            <CardContent className="py-8 text-sm text-neutral-500">
              {t("dashboard.loadingDailyPlan", "Loading daily plan...")}
            </CardContent>
          </Card>
        )}

        {!planQuery.isLoading && !plan && !planQuery.error && (
          <Card>
            <CardContent className="py-8 text-sm text-neutral-500">
              {t("dashboard.noDailyPlan", "No backend daily plan is available for this date.")}
            </CardContent>
          </Card>
        )}

        {plan && (
          <>
            <DashboardBriefCard topActions={topActions} />
        <section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
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

          <Card>
            <CardHeader>
              <CardTitle>{t("dashboard.modelDataStatus", "Model and data status")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div className="flex items-center justify-between gap-3">
                <span className="text-neutral-500">{t("planning.source", "Source")}</span>
                <Badge variant="success">{plan.data_source}</Badge>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-neutral-500">{t("planning.engine", "Engine")}</span>
                <span className="font-medium text-neutral-900">{plan?.engine_name ?? "-"}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-neutral-500">{t("planning.wape", "WAPE")}</span>
                <span className="font-medium text-neutral-900">
                  {plan ? `${(plan.metrics.wape * 100).toFixed(1)}%` : "-"}
                </span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span className="text-neutral-500">{t("planning.coverage", "Coverage")}</span>
                <span className="font-medium text-neutral-900">
                  {plan ? `${(plan.metrics.p10_p90_coverage * 100).toFixed(0)}%` : "-"}
                </span>
              </div>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-4 md:grid-cols-4">
          <ImpactCard label={t("dashboard.mismatchCost", "Estimated mismatch cost")} value={`RM ${Math.round(stockoutExposure + wasteExposure)}`} />
          <ImpactCard label={t("dashboard.stockoutExposure", "Stockout exposure")} value={`RM ${Math.round(stockoutExposure)}`} />
          <ImpactCard label={t("dashboard.wasteExposure", "Waste exposure")} value={`RM ${Math.round(wasteExposure)}`} />
          <ImpactCard label={t("dashboard.pendingActions", "Pending actions")} value={String(pendingActions)} />
        </section>

        <section>
          <div className="mb-3 flex items-center justify-between gap-3">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {t("dashboard.topExceptions", "Top 3 exceptions")}
            </h2>
            <Link
              href="/daily-planning"
              className="inline-flex items-center gap-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-600"
            >
              {t("dashboard.reviewDailyPlan", "Review Tomorrow's Daily Plan")}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {planQuery.isLoading ? (
            <div className="space-y-2">
              {[0, 1, 2].map((index) => (
                <div key={index} className="h-20 animate-pulse rounded-lg bg-neutral-100" />
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
          </>
        )}
      </main>
    </div>
  );
}

function ImpactCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{label}</p>
        <p className="mt-2 text-2xl font-bold text-neutral-900">{value}</p>
      </CardContent>
    </Card>
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
    <Card className="border-l-4 border-l-amber-500 bg-amber-50">
      <CardHeader className="pb-2">
        <CardTitle className="text-amber-900">{t("dashboard.tomorrowBrief", "Tomorrow Brief")}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-amber-800">{brief}</p>
      </CardContent>
    </Card>
  );
}
