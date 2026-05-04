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
import { translateDaypart } from "@/lib/i18n";

const EMPTY_PLAN: DailyPlanLatestResponse = {
  forecast_run_id: "",
  model_run_id: "",
  model_version: "lightgbm_p50_v1",
  engine_name: "lightgbm_mlops_prototype",
  model_status: "Loading",
  validation_window: "2022-09-01 to 2022-09-30",
  metrics: {
    wape: 0.38011723175212897,
    bias: -0.04164149684340122,
    p10_p90_coverage: 0.8153703703703704,
    estimated_mismatch_cost_delta_pct: -0.12,
  },
  top_actions: [],
};

function tomorrowISO() {
  const date = new Date();
  date.setDate(date.getDate() + 1);
  return date.toISOString().split("T")[0];
}

function buildExplanation(
  item: DailyPlanTopAction,
  t: (key: string, fallback?: string, values?: Record<string, string | number>) => string,
  language: "en" | "ms" | "zh-CN"
) {
  return t(
    "planning.explanation",
    "Prepare {{prep}} {{sku}} for {{outlet}} {{daypart}}. Expected demand is around {{p50}}, with a high scenario of {{p90}}. Stockout cost is higher than waste cost, so prep sits slightly above median demand.",
    {
      prep: item.recommended_prep,
      sku: item.sku_name,
      outlet: item.outlet_name,
      daypart: translateDaypart(language, item.daypart.toLowerCase()),
      p50: item.p50,
      p90: item.p90,
    }
  );
}

export default function DailyPlanningPage() {
  const { t, language } = useLanguage();
  const [planDate] = useState(tomorrowISO);
  const [plan, setPlan] = useState<DailyPlanLatestResponse>(EMPTY_PLAN);
  const [loading, setLoading] = useState(true);
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
    setLoading(false);
  }, [planDate]);

  useEffect(() => {
    let active = true;
    loadLatestPlan().catch(() => {
      if (active) {
        setLoading(false);
      }
    });
    return () => {
      active = false;
    };
  }, [loadLatestPlan]);

  const visibleActions = useMemo(() => {
    if (role === "outlet_manager") {
      return plan.top_actions.filter((item) => item.outlet_name === outletFilter);
    }
    return plan.top_actions;
  }, [plan.top_actions, outletFilter, role]);

  const actionSummaryItems = useMemo(() => {
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
          "{{percent}}% reduction on demo window",
          { percent: Math.abs(plan.metrics.estimated_mismatch_cost_delta_pct * 100).toFixed(0) }
        ),
      },
    ];
  }, [plan.metrics.estimated_mismatch_cost_delta_pct, t, visibleActions]);

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
      const response = await planningApi.regeneratePlan({ date: planDate, reason: "manual_demo_refresh" });
      setStatusMessage(response.message);
      await loadLatestPlan();
    } catch (_error) {
      setStatusMessage(
        t(
          "planning.status.regenerateQueued",
          "Regenerate request queued (demo mode). Using cached run."
        )
      );
    }
  }

  async function handleParse(note: string) {
    try {
      return await planningApi.parseManagerNote({ forecast_run_id: plan.forecast_run_id, note });
    } catch (_error) {
      const action = selectedAction ?? plan.top_actions[0];
      return {
        parsed_adjustment: {
          outlet_id: action?.outlet_name ?? "",
          daypart: action?.daypart ?? "morning",
          sku_category: action?.sku_category ?? "Bakery",
          suggested_adjustment_pct: 10,
          reason: note,
          requires_confirmation: true,
        },
        explanation:
          "Suggested adjustment parsed in demo fallback. No prep or replenishment quantity is changed until Apply is confirmed.",
      };
    }
  }

  async function handleApply(adjustment: ManagerNoteResponse["parsed_adjustment"]) {
    let backendApplied = false;
    try {
      await planningApi.applyManagerNote({
        forecast_run_id: plan.forecast_run_id,
        confirmed: true,
        adjustment,
      });
      backendApplied = true;
      await loadLatestPlan();
      setStatusMessage(t("planning.status.noteApplied", "Manager note applied after confirmation."));
    } catch (_error) {
      backendApplied = false;
    }

    if (backendApplied) {
      return;
    }

    const factor = 1 + adjustment.suggested_adjustment_pct / 100;
    const updated = plan.top_actions.map((item) => {
      if (
        item.outlet_name === adjustment.outlet_id &&
        item.daypart.toLowerCase() === adjustment.daypart.toLowerCase() &&
        item.sku_category === adjustment.sku_category
      ) {
        return {
          ...item,
          p10: Math.round(item.p10 * factor),
          p50: Math.round(item.p50 * factor),
          p90: Math.round(item.p90 * factor),
          recommended_prep: Math.round(item.recommended_prep * factor),
          reason_summary: `${item.reason_summary} ${t(
            "planning.managerNoteApplied",
            "Manager note applied (+{{percent}}%).",
            { percent: adjustment.suggested_adjustment_pct }
          )}`,
        };
      }
      return item;
    });

    setPlan((current) => ({ ...current, top_actions: updated }));
    setSelectedAction((current) => {
      if (!current) {
        return current;
      }
      return updated.find((item) => item.id === current.id) ?? current;
    });
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
    } catch (_error) {
      // Demo fallback only.
    }

    const timestamp = new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
    setAuditEvents((current) => [
      {
        id: `${selectedAction.id}-${current.length + 1}`,
        action: payload.action,
        final_prep: payload.finalPrep,
        reason: payload.reason,
        timestamp,
      },
      ...current,
    ]);
    setPlan((current) => ({
      ...current,
      top_actions: current.top_actions.map((item) =>
        item.id === selectedAction.id
          ? {
              ...item,
              recommended_prep: payload.finalPrep,
              status: payload.action,
            }
          : item
      ),
    }));
    setDrawerOpen(false);
    setStatusMessage(t("planning.status.decisionRecorded", "Decision recorded."));
  }

  async function handleOpenRecommendation(item: DailyPlanTopAction) {
    setSelectedAction(item);
    setDrawerOpen(true);
    if (!item.explanation && item.plan_id) {
      try {
        const response = await planningApi.explainRecommendation(item.id);
        setPlan((current) => ({
          ...current,
          top_actions: current.top_actions.map((candidate) =>
            candidate.id === item.id ? { ...candidate, explanation: response.explanation } : candidate
          ),
        }));
        setSelectedAction((current) =>
          current?.id === item.id ? { ...current, explanation: response.explanation } : current
        );
      } catch (_error) {
        // Local deterministic explanation remains available.
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
              {Array.from(new Set(plan.top_actions.map((item) => item.outlet_name))).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          )}
          <Button variant="outline" size="sm" onClick={handleRegenerate}>
            {t("planning.regenerate", "Regenerate plan")}
          </Button>
        </div>
      </Header>

      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-6 md:px-8">
        <ActionSummaryCard
          title={t("planning.actionSummary.title", "Tomorrow action summary")}
          items={actionSummaryItems}
          subtext={t(
            "planning.actionSummary.subtext",
            "This view prioritizes financially optimal prep and replenishment decisions based on LightGBM demand forecasting."
          )}
        />

        <ModelBadge
          engineName={t("planning.modelBadge", "LightGBM MLOps prototype")}
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

        {loading ? (
          <Card>
            <CardContent className="text-sm text-neutral-500">
              {t("planning.loadingPlan", "Loading latest plan...")}
            </CardContent>
          </Card>
        ) : (
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
        )}

        <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <ManagerNotePanel onParse={handleParse} onApply={handleApply} />
          <ReplenishmentBreakdown item={selectedAction} />
        </div>

        {selectedAction && (
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle>{t("planning.geminiExplanation", "Gemini explanation (grounded)")}</CardTitle>
            </CardHeader>
            <CardContent className="text-sm text-neutral-600">
              {buildExplanation(selectedAction, t, language)}
              {selectedAction.explanation && (
                <p className="mt-3 border-t border-neutral-100 pt-3 text-neutral-700">
                  {selectedAction.explanation}
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      <ModelEvidenceDrawer
        open={evidenceOpen}
        onClose={() => setEvidenceOpen(false)}
        modelVersion={plan.model_version}
        modelStatus={plan.model_status}
        engineName={plan.engine_name}
        validationWindow={plan.validation_window}
        metrics={plan.metrics}
      />

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
