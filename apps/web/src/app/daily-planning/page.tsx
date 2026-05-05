"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Header from "@/components/Header";
import ActionSummaryCard from "@/components/planning/ActionSummaryCard";
import ApprovalDrawer from "@/components/planning/ApprovalDrawer";
import FilterTabs, { type FilterKey } from "@/components/planning/FilterTabs";
import ManagerNotePanel from "@/components/planning/ManagerNotePanel";
import ModelBadge from "@/components/planning/ModelBadge";
import ModelEvidenceDrawer from "@/components/planning/ModelEvidenceDrawer";
import RecommendationCard from "@/components/planning/RecommendationCard";
import ReplenishmentBreakdown from "@/components/planning/ReplenishmentBreakdown";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { planningApi, type DailyPlanLatestResponse, type DailyPlanTopAction, type ManagerNoteResponse } from "@/lib/api/planning";

function tomorrowISO() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return date.toISOString().split("T")[0];
}

export default function DailyPlanningPage() {
  const { t } = useLanguage();
  const [planDate] = useState(tomorrowISO);
  const [plan, setPlan] = useState<DailyPlanLatestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>("top");
  const [selectedAction, setSelectedAction] = useState<DailyPlanTopAction | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [auditEvents, setAuditEvents] = useState<
    { id: string; action: string; final_prep: number; reason?: string; timestamp: string }[]
  >([]);
  const [role, setRole] = useState("global");
  const [outletFilter, setOutletFilter] = useState("KLCC Mall");
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const loadLatestPlan = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const response = await planningApi.latestPlan(planDate);
      setPlan(response);
      setSelectedAction((current) => {
        if (current) {
          return response.top_actions.find((item) => item.id === current.id) ?? response.top_actions[0] ?? null;
        }
        return response.top_actions[0] ?? null;
      });
      setOutletFilter((current) => {
        const outlets = new Set(response.top_actions.map((item) => item.outlet_name));
        return outlets.has(current) ? current : response.top_actions[0]?.outlet_name ?? current;
      });
    } catch (error) {
      setPlan(null);
      setSelectedAction(null);
      setLoadError(error instanceof Error ? error.message : "Failed to load daily plan");
    } finally {
      setLoading(false);
    }
  }, [planDate]);

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
      .sort((a, b) => b.line.shortage_qty - a.line.shortage_qty)[0];
    const topRisk = [...visibleActions]
      .sort(
        (a, b) =>
          b.financial_exposure.stockout_exposure_rm + b.financial_exposure.waste_exposure_rm -
          (a.financial_exposure.stockout_exposure_rm + a.financial_exposure.waste_exposure_rm)
      )[0];

    return [
      {
        label: t("planning.summary.topPrep", "Top prep action"),
        value: topPrep
          ? `${topPrep.recommended_prep} ${topPrep.sku_name} at ${topPrep.outlet_name}`
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
          ? `${topRisk.outlet_name} ${topRisk.sku_name} (RM ${topRisk.financial_exposure.stockout_exposure_rm})`
          : t("planning.summary.noRisks", "No risks detected"),
      },
      {
        label: t("planning.summary.mismatchCost", "Mismatch cost"),
        value: t(
          "planning.summary.mismatchValue",
          "{{percent}}% validation-window delta",
          { percent: Math.abs(plan.metrics.estimated_mismatch_cost_delta_pct * 100).toFixed(0) }
        ),
      },
    ];
  }, [plan, t, visibleActions]);

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
      const response = await planningApi.regeneratePlan({ date: planDate, reason: "manual_refresh" });
      setStatusMessage(response.message);
      await loadLatestPlan();
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Regenerate failed");
    }
  }

  async function handleParse(note: string) {
    if (!plan) {
      throw new Error("Load a backend plan before parsing a manager note.");
    }
    return planningApi.parseManagerNote({ forecast_run_id: plan.forecast_run_id, note });
  }

  async function handleApply(adjustment: ManagerNoteResponse["parsed_adjustment"]) {
    if (!plan) {
      throw new Error("Load a backend plan before applying a manager note.");
    }
    try {
      await planningApi.applyManagerNote({
        forecast_run_id: plan.forecast_run_id,
        confirmed: true,
        adjustment,
      });
      await loadLatestPlan();
      setStatusMessage(t("planning.status.noteApplied", "Manager note applied after confirmation."));
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Manager note apply failed");
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
        operator_reason: payload.reason || "Approved in Daily Planning Workspace",
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
      setStatusMessage(error instanceof Error ? error.message : "Decision failed");
    }
  }

  async function handleOpenRecommendation(item: DailyPlanTopAction) {
    setSelectedAction(item);
    setDrawerOpen(true);
    if (!item.explanation && item.plan_id) {
      try {
        const response = await planningApi.explainRecommendation(item.id);
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
        setStatusMessage(error instanceof Error ? error.message : "Explanation request failed");
      }
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

        {loading && (
          <Card>
            <CardContent className="text-sm text-neutral-500">
              {t("planning.loadingPlan", "Loading latest plan...")}
            </CardContent>
          </Card>
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
          dataSource={plan.data_source}
          modelStatus={plan.model_status}
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
          <ManagerNotePanel onParse={handleParse} onApply={handleApply} />
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
        dataSource={plan.data_source}
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
    </div>
  );
}
