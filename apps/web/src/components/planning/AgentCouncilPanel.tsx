import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateDaypart } from "@/lib/i18n";
import type { CouncilConfirmResponse, CouncilReviewResponse } from "@/lib/api/agentic";

interface Props {
  review: CouncilReviewResponse | null;
  beforeReview?: CouncilReviewResponse | null;
  afterReview?: CouncilReviewResponse | null;
  loading?: boolean;
  error?: string | null;
  confirming?: boolean;
  confirmResult?: CouncilConfirmResponse | null;
  onConfirm?: (operatorReason: string, selectedPrep: number) => Promise<void>;
}

function sourceLabel(value: string, t: (key: string, fallback: string) => string): string {
  if (value === "lightgbm") return t("planning.source.lightgbm", "LightGBM");
  if (value === "optimizer") return t("planning.source.optimizer", "Optimizer");
  if (value === "judge_synthesized") return t("planning.source.judgeSynthesized", "Judge synthesized");
  if (value === "llm_rephrased") return t("planning.source.llmRephrased", "LLM rephrased");
  if (value === "manager_note") return t("planning.source.managerNote", "Manager note");
  if (value === "rules_based") return t("planning.source.rulesBased", "Rules based");
  return value;
}

function applicationModeLabel(value: string, t: (key: string, fallback: string) => string): string {
  if (value === "prep_edit_only") return t("planning.managerNote.modePrepOnly", "prep edit only");
  if (value === "forecast_override_recompute") {
    return t("planning.managerNote.modeForecastRecompute", "forecast override recompute");
  }
  return value;
}

function formatEvidenceKey(key: string, t: (key: string, fallback: string) => string): string {
  const labels: Record<string, [string, string]> = {
    p10: ["explain.key.lowDemand", "Low-demand scenario"],
    p50: ["explain.key.expectedDemand", "Expected-demand scenario"],
    p90: ["explain.key.highDemand", "High-demand scenario"],
    recommended_prep: ["explain.key.recommendedPrep", "Recommended prep"],
    opening_stock: ["explain.key.openingStock", "Opening stock"],
    stockout_exposure_rm: ["explain.key.stockoutExposure", "Stockout exposure"],
    waste_exposure_rm: ["explain.key.wasteExposure", "Waste exposure"],
    priority_score: ["explain.key.priorityScore", "Priority score"],
    shortage_qty: ["explain.key.shortageQty", "Shortage quantity"],
    reorder_qty: ["explain.key.reorderQuantity", "Reorder quantity"],
  };
  const label = labels[key];
  return label ? t(label[0], label[1]) : key;
}

function formatEvidence(value: unknown, t: (key: string, fallback: string) => string): string {
  if (value == null) return t("planning.managerNote.unavailable", "unavailable");
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export default function AgentCouncilPanel({
  review,
  beforeReview,
  afterReview,
  loading,
  error,
  confirming,
  confirmResult,
  onConfirm,
}: Props) {
  const { t, language } = useLanguage();
  const [operatorReason, setOperatorReason] = useState(t("planning.council.defaultReason", "Approved Agent Council recommendation."));
  const [traceOpen, setTraceOpen] = useState(false);
  const [agentTraceOpen, setAgentTraceOpen] = useState(false);
  const [selectedPrep, setSelectedPrep] = useState<number | null>(null);

  useEffect(() => {
    setSelectedPrep(review?.judge_recommendation.recommended_prep ?? null);
  }, [review?.recommendation_id, review?.judge_recommendation.recommended_prep]);

  if (loading) {
    return <p className="text-sm text-neutral-500">{t("planning.council.loading", "Running Agent Council review...")}</p>;
  }

  if (error) {
    return <p className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p>;
  }

  if (!review) {
    return <p className="text-sm text-neutral-500">{t("planning.council.empty", "Choose a recommendation to review.")}</p>;
  }

  const judge = review.judge_recommendation;
  const selectedCandidate = review.candidate_quantities.find((candidate) => candidate.quantity === selectedPrep) ?? null;
  const beforePrep = beforeReview?.judge_recommendation.recommended_prep;
  const afterPrep = afterReview?.judge_recommendation.recommended_prep;
  const hasBeforeAfter = beforePrep != null && afterPrep != null;
  const delta = hasBeforeAfter ? afterPrep - beforePrep : 0;

  return (
    <div className="space-y-4">
      {hasBeforeAfter && (
        <Card className="border-sky-200 bg-sky-50">
          <CardContent className="grid gap-2 p-3 text-sm text-sky-950 sm:grid-cols-3">
            <p>
              <span className="font-semibold">{t("planning.council.beforeNote", "Before manager note")}:</span>{" "}
              {t("planning.council.unitsValue", "{{count}} units", { count: beforePrep ?? 0 })}
            </p>
            <p>
              <span className="font-semibold">{t("planning.council.afterNote", "After manager note")}:</span>{" "}
              {t("planning.council.unitsValue", "{{count}} units", { count: afterPrep ?? 0 })}
            </p>
            <p>
              <span className="font-semibold">{t("planning.council.delta", "Delta")}:</span>{" "}
              {t("planning.council.unitsValue", "{{count}} units", {
                count: `${delta > 0 ? "+" : ""}${delta}`,
              })}
            </p>
          </CardContent>
        </Card>
      )}

      {judge.source === "fallback" && (
        <Card className="border-amber-300 bg-amber-50">
          <CardContent className="p-3 text-sm text-amber-950">
            {t(
              "planning.council.fallbackWarning",
              "Judge fallback used. The recommendation was selected deterministically from server-generated candidates."
            )}
          </CardContent>
        </Card>
      )}

      <Card className="border-amber-200 bg-amber-50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-amber-700">
                {t("planning.council.judge", "Judge Agent")}
              </p>
              <CardTitle className="text-2xl">
                {t("planning.council.prepareUnits", "Prepare {{count}} units", {
                  count: judge.recommended_prep,
                })}
              </CardTitle>
              <p className="mt-1 text-sm text-amber-950">{judge.reasoning_summary}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">{sourceLabel(judge.source, t)}</Badge>
              <Badge variant="outline">{judge.agent_consensus}</Badge>
              {judge.requires_confirmation && <Badge variant="high">{t("planning.council.confirmation", "Needs confirmation")}</Badge>}
            </div>
          </div>
        </CardHeader>
        {judge.primary_conflict && (
          <CardContent className="pt-0 text-sm text-amber-900">
            {t("planning.council.primaryConflict", "Primary conflict")}: {judge.primary_conflict}
          </CardContent>
        )}
      </Card>

      <div>
        <h3 className="text-sm font-semibold text-neutral-900">{t("planning.council.candidates", "Candidate prep quantities")}</h3>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {review.candidate_quantities.map((candidate) => (
            <label
              key={`${candidate.source}-${candidate.quantity}`}
              className="rounded-lg border border-neutral-200 bg-white p-3"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`candidate-${review.recommendation_id}`}
                    checked={selectedPrep === candidate.quantity}
                    onChange={() => setSelectedPrep(candidate.quantity)}
                  />
                  <p className="text-lg font-semibold text-neutral-900">
                    {t("planning.council.unitsValue", "{{count}} units", { count: candidate.quantity })}
                  </p>
                </div>
                <div className="flex flex-wrap justify-end gap-1">
                  <Badge variant={candidate.source === judge.selected_candidate_source ? "high" : "outline"}>
                    {sourceLabel(candidate.source, t)}
                  </Badge>
                  {candidate.quantity === judge.recommended_prep && (
                    <Badge variant="outline">{t("planning.council.judgePick", "Judge pick")}</Badge>
                  )}
                </div>
              </div>
              <p className="mt-1 text-xs text-neutral-600">{candidate.reason}</p>
              {candidate.alternate_sources && candidate.alternate_sources.length > 0 && (
                <p className="mt-1 text-[11px] text-neutral-500">
                  {t("planning.council.alsoMatches", "Also matches")}: {candidate.alternate_sources.join(", ")}
                </p>
              )}
            </label>
          ))}
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="text-sm font-semibold text-neutral-900">{t("planning.council.agentArguments", "Specialist agent arguments")}</h3>
        <div className="mt-2 space-y-2">
          {review.agent_arguments.map((argument) => (
            <Card key={`${argument.agent}-${argument.stance}`}>
              <CardContent className="p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-neutral-900">{argument.agent}</p>
                    <p className="text-sm text-neutral-700">{argument.claim}</p>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline">{sourceLabel(argument.source, t)}</Badge>
                    <Badge variant="outline">{argument.severity}</Badge>
                  </div>
                </div>
                {Object.keys(argument.evidence).length > 0 && (
                  <div className="mt-2 grid gap-1 text-xs text-neutral-500 sm:grid-cols-2">
                    {Object.entries(argument.evidence).slice(0, 6).map(([key, value]) => (
                      <span key={key} className="rounded bg-neutral-50 px-2 py-1">
                        {formatEvidenceKey(key, t)}: {formatEvidence(value, t)}
                      </span>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {onConfirm && (
        <Card>
          <CardContent className="space-y-2 p-3">
            <p className="text-sm font-semibold text-neutral-900">{t("planning.council.confirmTitle", "Confirm council recommendation")}</p>
            <input
              className="w-full rounded-md border border-neutral-200 px-3 py-2 text-sm"
              value={operatorReason}
              onChange={(event) => setOperatorReason(event.target.value)}
            />
            <Button
              onClick={() => selectedPrep != null && onConfirm(operatorReason, selectedPrep)}
              disabled={confirming || selectedPrep == null}
            >
              {confirming
                ? t("planning.council.confirming", "Applying...")
                : selectedPrep === judge.recommended_prep
                  ? t("planning.council.confirmJudgeButton", "Apply Judge recommendation")
                  : t("planning.council.confirmSelectedButton", "Apply selected candidate")}
            </Button>
            {selectedCandidate && (
              <p className="text-xs text-neutral-500">
                {t("planning.council.selectedCandidate", "Selected candidate")}:{" "}
                {t("planning.council.unitsValue", "{{count}} units", { count: selectedCandidate.quantity })} /{" "}
                {sourceLabel(selectedCandidate.source, t)}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {confirmResult && (
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="space-y-2 p-3 text-sm text-emerald-950">
            <p className="font-semibold">{confirmResult.message}</p>
            <p>
              {t("planning.council.applicationMode", "Application mode")}:{" "}
              {applicationModeLabel(confirmResult.application_mode, t)}
            </p>
            {confirmResult.warnings?.map((warning) => (
              <p key={warning} className="rounded border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {warning}
              </p>
            ))}
            {confirmResult.line_changes.map((change) => (
              <p key={change.line_id} className="rounded bg-white/70 px-2 py-1 text-xs">
                {t("planning.council.lineChange", "{{outlet}} / {{sku}} / {{daypart}}: {{before}} -> {{after}} units", {
                  outlet: change.outlet_name,
                  sku: change.sku_name,
                  daypart: translateDaypart(language, change.daypart),
                  before: change.before_prep,
                  after: change.after_prep,
                })}
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      <div>
        <Button variant="ghost" size="sm" onClick={() => setAgentTraceOpen((value) => !value)}>
          {agentTraceOpen ? t("planning.council.hideAgentTrace", "Hide agent trace") : t("planning.council.showAgentTrace", "Show agent trace")}
        </Button>
        {agentTraceOpen && (
          <div className="mt-2 space-y-2">
            {review.agent_trace.map((item, index) => (
              <Card key={`${item.agent}-${item.role}-${index}`}>
                <CardContent className="p-3 text-xs">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-neutral-900">{item.agent} / {item.role}</p>
                      <p className="mt-1 text-neutral-700">{item.claim}</p>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Badge variant="outline">{sourceLabel(item.source, t)}</Badge>
                      <Badge variant="outline">{item.severity}</Badge>
                    </div>
                  </div>
                  {Object.keys(item.evidence).length > 0 && (
                    <pre className="mt-2 max-h-40 overflow-auto rounded bg-neutral-50 p-2 text-[11px] text-neutral-700">
                      {JSON.stringify(item.evidence, null, 2)}
                    </pre>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <div>
        <Button variant="ghost" size="sm" onClick={() => setTraceOpen((value) => !value)}>
          {traceOpen ? t("planning.council.hideTrace", "Hide technical trace") : t("planning.council.showTrace", "Show technical trace")}
        </Button>
        {traceOpen && (
          <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-neutral-950 p-3 text-xs text-neutral-100">
            {JSON.stringify(review.graph_trace, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}

