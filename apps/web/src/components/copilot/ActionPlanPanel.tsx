"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateRiskLevel } from "@/lib/i18n";
import type { AgentAction, DailyActionsResponse } from "@/types";

interface Props {
  actionPlan: DailyActionsResponse;
  compact?: boolean;
}

function targetLabel(action: AgentAction): string | null {
  if (action.target.sku_name && action.target.outlet_name) {
    return `${action.target.sku_name} at ${action.target.outlet_name}`;
  }
  if (action.target.ingredient_name) {
    return action.target.ingredient_name;
  }
  if (action.target.outlet_name) {
    return action.target.outlet_name;
  }
  if (action.target.sku_name) {
    return action.target.sku_name;
  }
  return null;
}

function urgencyClass(urgency: AgentAction["urgency"]): string {
  switch (urgency) {
    case "critical":
      return "bg-red-100 text-red-700";
    case "high":
      return "bg-orange-100 text-orange-700";
    case "medium":
      return "bg-yellow-100 text-yellow-700";
    default:
      return "bg-green-100 text-green-700";
  }
}

function ActionRow({ action }: { action: AgentAction }) {
  const { language, t } = useLanguage();
  const target = targetLabel(action);

  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold uppercase text-neutral-600">
          {t(`actionType.${action.action_type}`, action.action_type)}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${urgencyClass(action.urgency)}`}>
          {translateRiskLevel(language, action.urgency)}
        </span>
        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold uppercase text-neutral-600">
          {action.source_type === "llm_rephrased"
            ? t("common.source.ai", "AI phrased")
            : t("common.source.deterministic", "Deterministic")}
        </span>
      </div>
      <p className="mt-2 text-sm font-semibold text-neutral-800">{action.action_text}</p>
      <p className="mt-1 text-xs text-neutral-500">{action.estimated_impact}</p>
      {target && (
        <p className="mt-1 text-xs text-neutral-400">
          {t("common.target", "Target")}: {target}
        </p>
      )}
      {action.evidence.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {action.evidence.map((item) => (
            <span
              key={`${action.action_text}-${item}`}
              className="rounded-md border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] text-neutral-600"
            >
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ActionSection({
  title,
  actions,
}: {
  title: string;
  actions: AgentAction[];
}) {
  if (actions.length === 0) {
    return null;
  }

  return (
    <section className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">{title}</h3>
      <div className="space-y-3">
        {actions.map((action, index) => (
          <ActionRow key={`${title}-${index}-${action.action_text}`} action={action} />
        ))}
      </div>
    </section>
  );
}

export default function ActionPlanPanel({ actionPlan, compact = false }: Props) {
  const { t } = useLanguage();

  return (
    <div className="space-y-4 rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold text-neutral-800">{t("actionPlan.title", "AI Action Plan")}</h2>
        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold text-neutral-600">
          {actionPlan.date}
        </span>
        {actionPlan.fallback_mode && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
            {t("actionPlan.fallbackMode", "Fallback mode")}
          </span>
        )}
      </div>

      <div className="rounded-lg border border-amber-100 bg-amber-50 px-4 py-4 text-sm leading-relaxed text-neutral-800 whitespace-pre-wrap">
        {actionPlan.brief}
      </div>

      <section className="space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {t("actionPlan.topActions", "Top Actions")}
        </h3>
        {actionPlan.top_actions.length === 0 ? (
          <p className="text-sm text-neutral-500">{t("actionPlan.noActions", "No AI actions returned for this date.")}</p>
        ) : (
          <div className="space-y-3">
            {actionPlan.top_actions.map((action, index) => (
              <ActionRow key={`top-${index}-${action.action_text}`} action={action} />
            ))}
          </div>
        )}
      </section>

      {!compact && (
        <>
          <ActionSection title={t("actionPlan.prepActions", "Prep Actions")} actions={actionPlan.prep_actions} />
          <ActionSection title={t("actionPlan.reorderActions", "Reorder Actions")} actions={actionPlan.reorder_actions} />
          <ActionSection title={t("actionPlan.riskWarnings", "Risk Warnings")} actions={actionPlan.risk_warnings} />
          <ActionSection
            title={t("actionPlan.rebalanceSuggestions", "Rebalance Suggestions")}
            actions={actionPlan.rebalance_suggestions}
          />
        </>
      )}
    </div>
  );
}
