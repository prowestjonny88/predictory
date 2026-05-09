"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Header from "@/components/Header";
import { useCurrency } from "@/components/CurrencyProvider";
import ActionSummaryCard from "@/components/planning/ActionSummaryCard";
import ApprovalDrawer from "@/components/planning/ApprovalDrawer";
import FilterTabs, { type FilterKey } from "@/components/planning/FilterTabs";
import AgentCouncilPanel from "@/components/planning/AgentCouncilPanel";
import ManagerNotePanel from "@/components/planning/ManagerNotePanel";
import ModelBadge from "@/components/planning/ModelBadge";
import ModelEvidenceDrawer from "@/components/planning/ModelEvidenceDrawer";
import RecommendationCard from "@/components/planning/RecommendationCard";
import ReplenishmentBreakdown from "@/components/planning/ReplenishmentBreakdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { planningApi, type ApplyAdjustmentResponse, type DailyPlanLatestResponse, type DailyPlanTopAction, type ManagerNoteResponse } from "@/lib/api/planning";
import { agenticApi, type CouncilConfirmResponse, type CouncilReviewResponse } from "@/lib/api/agentic";
import { tomorrowISO } from "@/lib/utils";

const latestPlanCache = new Map<string, DailyPlanLatestResponse>();

export default function DailyPlanningPage() {
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();
  const [planDate] = useState(tomorrowISO);
  const [plan, setPlan] = useState<DailyPlanLatestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [readinessBlockers, setReadinessBlockers] = useState<string[]>([]);
  const [filter, setFilter] = useState<FilterKey>("top");
  const [selectedAction, setSelectedAction] = useState<DailyPlanTopAction | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [councilOpen, setCouncilOpen] = useState(false);
  const [councilReview, setCouncilReview] = useState<CouncilReviewResponse | null>(null);
  const [councilBeforeReview, setCouncilBeforeReview] = useState<CouncilReviewResponse | null>(null);
  const [councilAfterReview, setCouncilAfterReview] = useState<CouncilReviewResponse | null>(null);
  const [councilError, setCouncilError] = useState<string | null>(null);
  const [councilLoading, setCouncilLoading] = useState(false);
  const [councilConfirming, setCouncilConfirming] = useState(false);
  const [councilConfirmResult, setCouncilConfirmResult] = useState<CouncilConfirmResponse | null>(null);
  const [councilManagerAdjustment, setCouncilManagerAdjustment] = useState<ManagerNoteResponse["parsed_adjustment"] | null>(null);
  const [auditEvents, setAuditEvents] = useState<
    { id: string; action: string; final_prep: number; reason?: string; timestamp: string }[]
  >([]);
  const [role, setRole] = useState("global");
  const [outletFilter, setOutletFilter] = useState("");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const applyPlan = useCallback((response: DailyPlanLatestResponse) => {
    setPlan(response);
    setSelectedAction((current) => {
      if (current) {
        return response.top_actions.find((item) => item.id === current.id) ?? response.top_actions[0] ?? null;
      }
      return response.top_actions[0] ?? null;
    });
    setOutletFilter((current) => {
      const outlets = new Set(response.top_actions.map((item) => item.outlet_name));
      return current && outlets.has(current) ? current : response.top_actions[0]?.outlet_name ?? "";
    });
  }, []);

  const loadLatestPlan = useCallback(async () => {
    const cached = latestPlanCache.get(planDate) ?? null;
    if (cached) {
      applyPlan(cached);
    }
    setLoading(!cached);
    setLoadError(null);
    setReadinessBlockers([]);
    try {
      const readiness = await planningApi.forecastReadiness(planDate);
      if (!readiness.ready) {
        setPlan(null);
        setSelectedAction(null);
        setReadinessBlockers(readiness.blockers);
        return;
      }
      const response = await planningApi.latestPlan(planDate);
      latestPlanCache.set(planDate, response);
      applyPlan(response);
    } catch (error) {
      if (!cached) {
        setPlan(null);
        setSelectedAction(null);
      }
      setLoadError(error instanceof Error ? error.message : t("dashboard.failedDailyPlan", "Failed to load daily plan"));
    } finally {
      setLoading(false);
    }
  }, [applyPlan, planDate, t]);

  useEffect(() => {
    loadLatestPlan();
  }, [loadLatestPlan]);

  const visibleActions = useMemo(() => {
    const actions = plan?.top_actions ?? [];
    if (role === "outlet_manager") {
      return actions.filter((item) => item.outlet_name === outletFilter);
    }
    return actions;
  }, [plan?.top_actions, outletFilter, role]);

  const actionSummaryItems = useMemo(() => {
    if (!plan) {
      return [];
    }
    const topPrep = visibleActions[0];
    const topShortage = visibleActions
      .flatMap((item) => item.replenishment.map((line) => ({ item, line })))
      .filter((a) => a.line.shortage_qty > 0)
      .sort((a, b) => b.line.shortage_qty - a.line.shortage_qty)[0];
    const topRisk = [...visibleActions]
      .filter((a) => a.financial_exposure.stockout_exposure_rm + a.financial_exposure.waste_exposure_rm > 0)
      .sort(
        (a, b) =>
          b.financial_exposure.stockout_exposure_rm + b.financial_exposure.waste_exposure_rm -
          (a.financial_exposure.stockout_exposure_rm + a.financial_exposure.waste_exposure_rm)
      )[0];

    const items = [
      {
        label: t("planning.summary.topPrep", "Top prep action"),
        value: topPrep
          ? t("planning.summary.topPrepValue", "{{prep}} {{sku}} at {{outlet}}", {
              prep: topPrep.recommended_prep,
              sku: topPrep.sku_name,
              outlet: topPrep.outlet_name,
            })
          : t("planning.summary.noActions", "No actions"),
      },
      {
        label: t("planning.summary.topReorder", "Top reorder action"),
        value: topShortage
          ? `${topShortage.line.ingredient_name} +${topShortage.line.shortage_qty} ${topShortage.line.unit}`
          : t("planning.summary.noShortages", "No shortages detected"),
      },
      {
        label: t("planning.summary.topRisk", "Top risk"),
        value: topRisk
          ? `${topRisk.outlet_name} ${topRisk.sku_name} (${formatCurrency(
              topRisk.financial_exposure.stockout_exposure_rm + topRisk.financial_exposure.waste_exposure_rm,
              language,
              { maximumFractionDigits: 0, minimumFractionDigits: 0 }
            )})`
          : t("planning.summary.noMajorFinancialRisk", "No major financial risk detected"),
      },
    ];

    if (plan.metrics.estimated_mismatch_cost_delta_pct != null) {
      items.push({
        label: t("planning.summary.mismatchCost", "Mismatch cost"),
        value: t(
          "planning.summary.mismatchValue",
          "{{percent}}% validation-window delta",
          { percent: Math.abs(plan.metrics.estimated_mismatch_cost_delta_pct * 100).toFixed(0) }
        ),
      });
    }

    return items;
  }, [formatCurrency, language, plan, t, visibleActions]);

  const groupedByOutlet = useMemo(() => {
    const map = new Map<string, DailyPlanTopAction[]>();
    visibleActions.forEach((item) => {
      const list = map.get(item.outlet_name) ?? [];
      list.push(item);
      map.set(item.outlet_name, list);
    });
    return Array.from(map.entries());
  }, [visibleActions]);

  const groupedBySku = useMemo(() => {
    const map = new Map<string, DailyPlanTopAction[]>();
    visibleActions.forEach((item) => {
      const list = map.get(item.sku_name) ?? [];
      list.push(item);
      map.set(item.sku_name, list);
    });
    return Array.from(map.entries());
  }, [visibleActions]);

  async function handleRegenerate() {
    setStatusMessage(null);
    try {
      const readiness = await planningApi.forecastReadiness(planDate);
      if (!readiness.ready) {
        setReadinessBlockers(readiness.blockers);
        setPlan(null);
        setSelectedAction(null);
        return;
      }
      const response = await planningApi.regeneratePlan({ date: planDate, reason: "manual_refresh" });
      setStatusMessage(response.message);
      await loadLatestPlan();
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : t("planning.status.regenerateFailed", "Regenerate failed"));
    }
  }

  async function handleParse(note: string) {
    if (!plan) {
      throw new Error(t("planning.error.loadPlanBeforeParse", "Load a backend plan before parsing a manager note."));
    }
    return planningApi.parseManagerNote({ forecast_run_id: plan.forecast_run_id, note, language });
  }

  async function handleApply(adjustment: ManagerNoteResponse["parsed_adjustment"]) {
    if (!plan) {
      throw new Error(t("planning.error.loadPlanBeforeApply", "Load a backend plan before applying a manager note."));
    }
    try {
      const response = await planningApi.applyManagerNote({
        forecast_run_id: plan.forecast_run_id,
        confirmed: true,
        adjustment,
      });
      await loadLatestPlan();
      setStatusMessage(formatManagerNoteResult(response, t));
      return response;
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : t("planning.managerNote.applyFailed", "Unable to apply note"));
      throw error;
    }
  }

  async function handleDecision(payload: { action: "approved" | "edited" | "rejected"; finalPrep: number; reason?: string }) {
    if (!selectedAction) {
      return;
    }
    try {
      const response = await planningApi.submitDecision(selectedAction, {
        operator_action: payload.action,
        final_prep: payload.finalPrep,
        operator_reason: payload.reason || t("planning.decision.defaultReason", "Approved in Daily Planning Workspace"),
        role: role === "outlet_manager" ? "outlet_manager" : "planner",
      });
      await loadLatestPlan();
      setAuditEvents((current) => [
        {
          id: `${response.audit_event_ids[0] ?? selectedAction.id}`,
          action: payload.action,
          final_prep: payload.finalPrep,
          reason: payload.reason,
          timestamp: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
        },
        ...current,
      ]);
      setDrawerOpen(false);
      setStatusMessage(t("planning.status.decisionRecorded", "Decision recorded and audit log created."));
      return;
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : t("planning.decision.failed", "Decision failed"));
    }
  }

  async function handleOpenRecommendation(item: DailyPlanTopAction) {
    setSelectedAction(item);
    setDrawerOpen(true);
    if (!item.explanation && item.plan_id) {
      try {
        const response = await planningApi.explainRecommendation(item.id, language);
        setPlan((current) => current ? ({
          ...current,
          top_actions: current.top_actions.map((candidate) =>
            candidate.id === item.id ? { ...candidate, explanation: response.explanation } : candidate
          ),
        }) : current);
        setSelectedAction((current) =>
          current?.id === item.id ? { ...current, explanation: response.explanation } : current
        );
      } catch (error) {
        setStatusMessage(error instanceof Error ? error.message : t("planning.explanation.failed", "Explanation request failed"));
      }
    }
  }

  async function handleOpenCouncilReview(item: DailyPlanTopAction) {
    setSelectedAction(item);
    setCouncilOpen(true);
    setCouncilLoading(true);
    setCouncilError(null);
    setCouncilReview(null);
    setCouncilBeforeReview(null);
    setCouncilAfterReview(null);
    setCouncilConfirmResult(null);
    setCouncilManagerAdjustment(null);
    try {
      const response = await agenticApi.reviewCouncil(item.id, language);
      setCouncilReview(response);
    } catch (error) {
      setCouncilError(error instanceof Error ? error.message : t("planning.council.reviewFailed", "Agent Council review failed"));
    } finally {
      setCouncilLoading(false);
    }
  }

  async function handleManagerNoteCouncilPreview(adjustment: ManagerNoteResponse["parsed_adjustment"], note: string) {
    const matchingActions = (plan?.top_actions ?? []).filter(
      (item) =>
        item.outlet_name === adjustment.outlet_id &&
        item.daypart.toLowerCase() === adjustment.daypart.toLowerCase() &&
        item.sku_category === adjustment.sku_category
    );
    const actionForNote = matchingActions[0];
    if (!actionForNote) {
      throw new Error(t("planning.managerNote.noMatch", "No daily-planning recommendation matches the parsed manager note target."));
    }
    if (matchingActions.length > 1) {
      setStatusMessage(
        t("planning.managerNote.multipleMatches", "Multiple matching recommendations found; using the first match: {{sku}} at {{outlet}} ({{daypart}}).", {
          sku: actionForNote.sku_name,
          outlet: actionForNote.outlet_name,
          daypart: actionForNote.daypart,
        })
      );
    }
    setSelectedAction(actionForNote);
    setCouncilOpen(true);
    setCouncilLoading(true);
    setCouncilError(null);
    setCouncilReview(null);
    setCouncilBeforeReview(null);
    setCouncilAfterReview(null);
    setCouncilConfirmResult(null);
    setCouncilManagerAdjustment(adjustment);
    try {
      const response = await agenticApi.reviewCouncilWithNote(actionForNote.id, adjustment, note, language);
      setCouncilBeforeReview(response.before_review);
      setCouncilAfterReview(response.after_review);
      setCouncilReview(response.after_review);
    } catch (error) {
      const message = error instanceof Error ? error.message : t("planning.managerNote.councilFailed", "Council preview failed");
      setCouncilError(message);
      throw error;
    } finally {
      setCouncilLoading(false);
    }
  }

  async function handleConfirmCouncil(operatorReason: string, selectedPrep: number) {
    if (!councilReview) {
      return;
    }
    setCouncilConfirming(true);
    setCouncilError(null);
    try {
      const response = await agenticApi.confirmCouncilRecommendation({
        recommendation_id: councilReview.recommendation_id,
        selected_prep: selectedPrep,
        manager_adjustment: councilManagerAdjustment ?? undefined,
        operator_reason: operatorReason,
        language,
      });
      setCouncilConfirmResult(response);
      setStatusMessage(response.message);
      await loadLatestPlan();
    } catch (error) {
      setCouncilError(error instanceof Error ? error.message : t("planning.council.confirmFailed", "Agent Council confirm failed"));
    } finally {
      setCouncilConfirming(false);
    }
  }

  function renderActionList(items: DailyPlanTopAction[]) {
    if (items.length === 0) {
      return <p className="text-sm text-neutral-500">{t("planning.noActionsFilter", "No actions for this filter.")}</p>;
    }
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {items.map((item) => (
          <RecommendationCard
            key={item.id}
            item={item}
            onOpen={handleOpenRecommendation}
            onCouncilReview={handleOpenCouncilReview}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className="min-h-screen"
      style={{
        fontFamily: '"Space Grotesk", "DM Sans", "Segoe UI", sans-serif',
        background:
          "radial-gradient(circle at top right, rgba(251, 191, 36, 0.25), transparent 40%), radial-gradient(circle at 20% 20%, rgba(14, 165, 233, 0.15), transparent 35%), #f8fafc",
      }}
    >
      <Header title={t("planning.title", "Daily Planning Workspace")} date={planDate}>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded-md border border-neutral-200 bg-white px-3 py-1 text-xs"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="global">{t("planning.role.global", "Global planner")}</option>
            <option value="outlet_manager">{t("planning.role.outlet", "Outlet manager")}</option>
          </select>
          {role === "outlet_manager" && (
            <select
              className="rounded-md border border-neutral-200 bg-white px-3 py-1 text-xs"
              value={outletFilter}
              onChange={(event) => setOutletFilter(event.target.value)}
            >
              {Array.from(new Set((plan?.top_actions ?? []).map((item) => item.outlet_name))).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}
          <Button variant="outline" size="sm" onClick={handleRegenerate} disabled={loading}>
            {t("planning.regenerate", "Regenerate plan")}
          </Button>
        </div>
      </Header>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:px-8">
        {loadError && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="text-sm text-red-800">{loadError}</CardContent>
          </Card>
        )}

        {readinessBlockers.length > 0 && (
          <Card className="border-amber-200 bg-amber-50">
            <CardContent className="text-sm text-amber-900">
              <p className="font-semibold">{t("forecast.notReady", "Forecast cannot run yet.")}</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {readinessBlockers.slice(0, 8).map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="space-y-4">
            <Skeleton className="h-28" />
            <div className="grid gap-4 lg:grid-cols-2">
              {[0, 1, 2, 3].map((index) => (
                <Skeleton key={index} className="h-80" />
              ))}
            </div>
          </div>
        )}

        {!loading && !plan && !loadError && (
          <Card>
            <CardContent className="text-sm text-neutral-500">
              {t("planning.noBackendPlan", "No backend daily plan is available for this date.")}
            </CardContent>
          </Card>
        )}

        {plan && (
          <>
        <ActionSummaryCard
          title={t("planning.actionSummary.title", "Tomorrow action summary")}
          items={actionSummaryItems}
          subtext={t(
            "planning.actionSummary.subtext",
            "This view prioritizes cost-aware prep and replenishment decisions from the backend planning engine."
          )}
        />

        <ModelBadge
          engineName={plan.engine_name}
          activeEngineName={plan.active_engine_name}
          dataSource={plan.data_source}
          modelStatus={plan.model_status}
          modelArtifactStatus={plan.model_artifact_status}
          modelArtifactAvailable={plan.model_artifact_available}
          forecastSourceLabel={plan.forecast_source_label}
          validationWindow={plan.validation_window}
          wape={plan.metrics.wape}
          coverage={plan.metrics.p10_p90_coverage}
          onOpenEvidence={() => setEvidenceOpen(true)}
        />

        {statusMessage && (
          <Card className="border-emerald-200 bg-emerald-50">
            <CardContent className="text-sm text-emerald-900">{statusMessage}</CardContent>
          </Card>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-neutral-900">
              {t("planning.recommendations", "Recommendations")}
            </h2>
            <p className="text-xs text-neutral-500">
              {t("planning.showingActions", "Showing {{count}} actions", { count: visibleActions.length })}
            </p>
          </div>
          <FilterTabs value={filter} onChange={setFilter} />
        </div>

          <div className="space-y-4">
            {filter === "top" && renderActionList(visibleActions)}
            {filter === "outlet" &&
              groupedByOutlet.map(([outlet, items]) => (
                <div key={outlet} className="space-y-3">
                  <h3 className="text-sm font-semibold text-neutral-900">{outlet}</h3>
                  {renderActionList(items)}
                </div>
              ))}
            {filter === "sku" &&
              groupedBySku.map(([sku, items]) => (
                <div key={sku} className="space-y-3">
                  <h3 className="text-sm font-semibold text-neutral-900">{sku}</h3>
                  {renderActionList(items)}
                </div>
              ))}
            {filter === "risk" &&
              renderActionList(
                [...visibleActions].sort(
                  (a, b) =>
                    b.financial_exposure.stockout_exposure_rm + b.financial_exposure.waste_exposure_rm -
                    (a.financial_exposure.stockout_exposure_rm + a.financial_exposure.waste_exposure_rm)
                )
              )}
          </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <ManagerNotePanel
            onParse={handleParse}
            onApply={handleApply}
            onCouncilPreview={handleManagerNoteCouncilPreview}
          />
          <ReplenishmentBreakdown item={selectedAction} />
        </div>

        {selectedAction?.explanation && (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle>{t("planning.geminiExplanation", "Gemini explanation (grounded)")}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-neutral-600">
              {selectedAction.explanation}
            </CardContent>
          </Card>
        )}
          </>
        )}
      </div>

      {plan && (
        <ModelEvidenceDrawer
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        modelVersion={plan.model_version}
        modelStatus={plan.model_status}
        engineName={plan.engine_name}
        activeEngineName={plan.active_engine_name}
        dataSource={plan.data_source}
        modelArtifactStatus={plan.model_artifact_status}
        modelArtifactAvailable={plan.model_artifact_available}
        forecastSourceLabel={plan.forecast_source_label}
        validationWindow={plan.validation_window}
        metrics={plan.metrics}
      />
      )}

      <ApprovalDrawer
        open={drawerOpen}
        item={selectedAction}
        auditEvents={auditEvents}
        onClose={() => setDrawerOpen(false)}
        onSubmit={handleDecision}
      />

      <Sheet open={councilOpen} onOpenChange={setCouncilOpen}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>{t("planning.council.title", "Agent Council Review")}</SheetTitle>
            <SheetDescription>
              {t(
                "planning.council.description",
                "Tool-backed agents argue from backend evidence. The Judge may only choose a server-generated prep candidate."
              )}
            </SheetDescription>
          </SheetHeader>
          <div className="mt-6">
            <AgentCouncilPanel
              review={councilReview}
              beforeReview={councilBeforeReview}
              afterReview={councilAfterReview}
              loading={councilLoading}
              error={councilError}
              confirming={councilConfirming}
              confirmResult={councilConfirmResult}
              onConfirm={handleConfirmCouncil}
            />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

function formatManagerNoteResult(
  response: ApplyAdjustmentResponse,
  t: (key: string, fallback: string, values?: Record<string, string | number>) => string
) {
  const firstChange = response.line_changes?.[0];
  const mode = response.application_mode === "prep_edit_only"
    ? t("planning.managerNote.modePrepOnly", "prep edit only")
    : t("planning.managerNote.modeForecastRecompute", "forecast override recompute");
  const replenishment = response.replenishment_plan_id
    ? t("planning.managerNote.replenishmentRefreshed", "replenishment refreshed")
    : t("planning.managerNote.replenishmentNotRefreshed", "replenishment not refreshed");
  const changeText = firstChange
    ? t("planning.managerNote.firstChange", "first line {{before}} -> {{after}} units", {
        before: firstChange.before_prep,
        after: firstChange.after_prep,
      })
    : t("planning.managerNote.noLineChange", "no line quantity change returned");
  return t(
    "planning.status.noteAppliedMode",
    "Manager note applied as {{mode}} across {{count}} line(s); {{changeText}}; {{replenishment}}.",
    {
      mode,
      count: response.updated_line_ids.length,
      changeText,
      replenishment,
    }
  );
}
   
 