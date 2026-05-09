import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateDaypart } from "@/lib/i18n";
import type { ApplyAdjustmentResponse, ManagerNoteResponse } from "@/lib/api/planning";

interface Props {
  onParse: (note: string) => Promise<ManagerNoteResponse | null>;
  onApply: (adjustment: ManagerNoteResponse["parsed_adjustment"]) => Promise<ApplyAdjustmentResponse | null>;
  onCouncilPreview?: (adjustment: ManagerNoteResponse["parsed_adjustment"], note: string) => Promise<void>;
}

export default function ManagerNotePanel({ onParse, onApply, onCouncilPreview }: Props) {
  const { t, language } = useLanguage();
  const [note, setNote] = useState("");
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<ManagerNoteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [adjustmentPct, setAdjustmentPct] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [applyResult, setApplyResult] = useState<ApplyAdjustmentResponse | null>(null);

  function sourceLabel(value: string): string {
    if (value === "llm_validated") return t("planning.managerNote.sourceLlmValidated", "Gemini validated");
    if (value === "llm_rephrased") return t("planning.managerNote.sourceLlmRephrased", "Gemini explanation");
    return value;
  }

  function applicationModeLabel(value: string): string {
    if (value === "prep_edit_only") return t("planning.managerNote.modePrepOnly", "prep edit only");
    if (value === "forecast_override_recompute") {
      return t("planning.managerNote.modeForecastRecompute", "forecast override recompute");
    }
    return value;
  }

  async function handleParse() {
    setParsing(true);
    setError(null);
    try {
      const response = await onParse(note);
      setResult(response);
      setApplyResult(null);
      setAdjustmentPct(String(response?.parsed_adjustment.suggested_adjustment_pct ?? 0));
      setAdjustmentReason(response?.parsed_adjustment.reason ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("planning.managerNote.error", "Unable to parse note"));
      setResult(null);
    } finally {
      setParsing(false);
    }
  }

  async function handleApply() {
    if (!result) {
      return;
    }
    const parsedPct = Number.parseFloat(adjustmentPct);
    setApplying(true);
    setError(null);
    try {
      const response = await onApply({
        ...result.parsed_adjustment,
        suggested_adjustment_pct: Number.isNaN(parsedPct) ? result.parsed_adjustment.suggested_adjustment_pct : parsedPct,
        reason: adjustmentReason.trim() || result.parsed_adjustment.reason,
        requires_confirmation: true,
      });
      setApplyResult(response);
      setResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("planning.managerNote.applyFailed", "Unable to apply note"));
    } finally {
      setApplying(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("planning.managerNote.title", "Manager note parser")}</CardTitle>
        <div className="mt-2 flex flex-wrap gap-2 text-xs text-neutral-500">
          <span className="rounded-full bg-neutral-100 px-2 py-1 font-semibold">
            {t("planning.managerNote.flowParse", "1. Parse note")}
          </span>
          <span className="rounded-full bg-neutral-100 px-2 py-1 font-semibold">
            {t("planning.managerNote.flowReview", "2. Review assumptions")}
          </span>
          <span className="rounded-full bg-neutral-100 px-2 py-1 font-semibold">
            {t("planning.managerNote.flowConfirm", "3. Confirm impact")}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <textarea
          className="min-h-[90px] w-full rounded-lg border border-neutral-200 p-3 text-sm"
          placeholder={t(
            "planning.managerNote.placeholder",
            "School group visiting Cheras community center tomorrow morning, expect more pastries."
          )}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleParse} disabled={parsing || note.length < 10}>
            {parsing
              ? t("planning.managerNote.parsing", "Parsing...")
              : t("planning.managerNote.parse", "Parse note")}
          </Button>
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>

        {result && (
          <div className="space-y-3 rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-sm">
            <div className="rounded-md border border-sky-100 bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("planning.managerNote.stepParsed", "Step 1: Parsed context")}
              </p>
              <p className="mt-2 font-semibold text-neutral-900">
                {result.parsed_adjustment.outlet_id} /{" "}
                {translateDaypart(language, result.parsed_adjustment.daypart.toLowerCase())} /{" "}
                {result.parsed_adjustment.sku_category}
              </p>
              <p className="text-xs text-neutral-500">
                {result.parsed_adjustment.suggested_adjustment_pct > 0 ? "+" : ""}
                {result.parsed_adjustment.suggested_adjustment_pct}% / {result.parsed_adjustment.reason}
              </p>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-sky-50 px-2 py-1 font-semibold text-sky-700">
                  {t("planning.managerNote.parseSource", "Parse source")}:{" "}
                  {sourceLabel(result.parsed_adjustment.parse_source)}
                </span>
                <span className="rounded-full bg-sky-50 px-2 py-1 font-semibold text-sky-700">
                  {t("planning.managerNote.sourceType", "Explanation source")}:{" "}
                  {sourceLabel(result.source_type)}
                </span>
              </div>
              {result.parsed_adjustment.uncertainty_reason && (
                <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                  {result.parsed_adjustment.uncertainty_reason}
                </p>
              )}
              <p className="mt-2 text-xs text-neutral-500">{result.explanation}</p>
            </div>

            <div className="rounded-md border border-amber-100 bg-white p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {t("planning.managerNote.stepImpact", "Step 2: What will happen")}
              </p>
              <div className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
                {t("planning.managerNote.applicationMode", "Application mode")}:{" "}
                {t("planning.managerNote.modePrepOnly", "prep edit only")}
              </div>
              <ul className="mt-2 space-y-1 text-xs text-neutral-600">
                <li>{t("planning.managerNote.modeCopy", "Mode: prep edit only")}</li>
                <li>{t("planning.managerNote.noForecastRerun", "Forecast will not be rerun.")}</li>
                <li>{t("planning.managerNote.matchingLines", "Matching prep lines will be adjusted after confirmation.")}</li>
                <li>{t("planning.managerNote.replenishmentRefreshes", "Replenishment will refresh after prep changes.")}</li>
                <li>{t("planning.managerNote.auditRecorded", "Audit events will record the confirmed change.")}</li>
              </ul>
            </div>

            <div className="mt-3 grid gap-2 sm:grid-cols-[120px_1fr]">
              <label className="text-xs text-neutral-500">
                {t("planning.managerNote.adjustmentPct", "Adjustment %")}
                <input
                  className="mt-1 w-full rounded-md border border-neutral-200 px-2 py-1 text-sm text-neutral-900"
                  type="number"
                  value={adjustmentPct}
                  onChange={(event) => setAdjustmentPct(event.target.value)}
                />
              </label>
              <label className="text-xs text-neutral-500">
                {t("planning.managerNote.reason", "Reason")}
                <input
                  className="mt-1 w-full rounded-md border border-neutral-200 px-2 py-1 text-sm text-neutral-900"
                  value={adjustmentReason}
                  onChange={(event) => setAdjustmentReason(event.target.value)}
                />
              </label>
            </div>

            {result.parsed_adjustment.requires_confirmation && (
              <p className="mt-2 rounded-md border border-amber-200 bg-amber-50 px-2 py-1 text-xs text-amber-900">
                {t(
                  "planning.managerNote.confirmationRequired",
                  "Nothing is applied yet. Confirming will update prep and refresh replenishment."
                )}
              </p>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {onCouncilPreview && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    onCouncilPreview(result.parsed_adjustment, note).catch((err) => {
                      setError(err instanceof Error ? err.message : t("planning.managerNote.councilFailed", "Council preview failed"));
                    });
                  }}
                >
                  {t("planning.managerNote.runCouncil", "Run Agent Council Preview")}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleApply} disabled={applying}>
                {applying
                  ? t("planning.managerNote.applying", "Applying...")
                  : t("planning.managerNote.applyDirect", "Apply directly without council")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setResult(null)}>
                {t("planning.managerNote.ignore", "Ignore")}
              </Button>
            </div>
            <p className="text-xs text-neutral-500">
              {t(
                "planning.managerNote.directApplyWarning",
                "Direct apply skips Agent Council review and immediately applies prep_edit_only."
              )}
            </p>
          </div>
        )}

        {applyResult && (
          <div className="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-sm text-emerald-950">
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">
              {t("planning.managerNote.appliedTitle", "Manager note applied")}
            </p>
            <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
              <span>
                {t("planning.managerNote.applicationMode", "Application mode")}:{" "}
                {applicationModeLabel(applyResult.application_mode)}
              </span>
              <span>{t("planning.managerNote.affectedLines", "Affected lines")}: {applyResult.updated_line_ids.length}</span>
              <span>{t("planning.managerNote.auditCount", "Audit events")}: {applyResult.audit_event_ids.length}</span>
              <span>
                {t("planning.managerNote.replenishment", "Replenishment")}:{" "}
                {applyResult.replenishment_plan_id
                  ? t("planning.managerNote.refreshed", "refreshed")
                  : t("planning.managerNote.unavailable", "unavailable")}
              </span>
            </div>
            {applyResult.line_changes && applyResult.line_changes.length > 0 && (
              <div className="mt-3 space-y-1">
                {applyResult.line_changes.slice(0, 5).map((change) => (
                  <p key={change.line_id} className="rounded-md bg-white/70 px-2 py-1 text-xs">
                    {t("planning.managerNote.lineChangeDetailed", "{{outlet}} / {{sku}} / {{daypart}}: {{before}} -> {{after}} units", {
                      outlet: change.outlet_name,
                      sku: change.sku_name,
                      daypart: translateDaypart(language, change.daypart.toLowerCase()),
                      before: change.before_prep,
                      after: change.after_prep,
                    })}
                    <span className="ml-2 text-[10px] text-emerald-700">
                      {t("planning.managerNote.lineId", "line")} {change.line_id}
                    </span>
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
