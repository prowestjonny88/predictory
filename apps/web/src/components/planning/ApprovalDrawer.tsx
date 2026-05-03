import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import UncertaintyBar from "@/components/planning/UncertaintyBar";
import AuditPreview, { type AuditEventPreview } from "@/components/planning/AuditPreview";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateDaypart } from "@/lib/i18n";
import type { DailyPlanTopAction } from "@/lib/api/planning";

interface Props {
  open: boolean;
  item: DailyPlanTopAction | null;
  auditEvents: AuditEventPreview[];
  onClose: () => void;
  onSubmit: (payload: {
    action: "approved" | "edited" | "rejected";
    finalPrep: number;
    reason?: string;
  }) => Promise<void>;
}

export default function ApprovalDrawer({ open, item, auditEvents, onClose, onSubmit }: Props) {
  const { t, language } = useLanguage();
  const [action, setAction] = useState<"approved" | "edited" | "rejected">("approved");
  const [finalPrep, setFinalPrep] = useState<string>("");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const effectiveFinalPrep = useMemo(() => {
    if (!item) {
      return 0;
    }
    const parsed = Number.parseInt(finalPrep || "", 10);
    if (Number.isNaN(parsed)) {
      return item.recommended_prep;
    }
    return parsed;
  }, [finalPrep, item]);

  if (!open || !item) {
    return null;
  }

  const reasonRequired = action !== "approved";
  const finalPrepRequired = action === "edited";
  const parsedFinalPrep = Number.parseInt(finalPrep || "", 10);
  const hasFinalPrep = !Number.isNaN(parsedFinalPrep);
  const reasonValid = !reasonRequired || reason.trim().length >= 3;
  const finalPrepValid = !finalPrepRequired || hasFinalPrep;
  const submitDisabled = submitting || !reasonValid || !finalPrepValid;

  async function handleSubmit() {
    if (!reasonValid) {
      setValidationError(t("planning.decision.reasonRequired", "Reason is required for edits or rejections."));
      return;
    }
    if (!finalPrepValid) {
      setValidationError(t("planning.decision.finalPrepRequired", "Final prep is required when editing."));
      return;
    }
    setValidationError(null);
    setSubmitting(true);
    await onSubmit({ action, finalPrep: effectiveFinalPrep, reason: reason.trim() || undefined });
    setSubmitting(false);
    setReason("");
    setFinalPrep("");
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/30">
      <div className="flex h-full w-full max-w-lg flex-col bg-white shadow-xl">
        <div className="flex items-center justify-between border-b px-5 py-4">
          <div>
            <h3 className="text-sm font-semibold text-neutral-900">
              {t("planning.decision.title", "Decision drawer")}
            </h3>
            <p className="text-xs text-neutral-500">
              {item.outlet_name} · {item.sku_name} · {translateDaypart(language, item.daypart.toLowerCase())}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            {t("common.close", "Close")}
          </Button>
        </div>
        <div className="flex-1 space-y-4 overflow-auto px-5 py-4">
          <UncertaintyBar
            p10={item.p10}
            p50={item.p50}
            p90={item.p90}
            recommended={item.recommended_prep}
          />

          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-neutral-100 p-3">
              <p className="text-xs text-neutral-500">
                {t("planning.decision.recommendedPrep", "Recommended prep")}
              </p>
              <p className="text-sm font-semibold text-neutral-900">{item.recommended_prep}</p>
            </div>
            <div className="rounded-lg border border-neutral-100 p-3">
              <p className="text-xs text-neutral-500">
                {t("planning.decision.openingStock", "Opening stock")}
              </p>
              <p className="text-sm font-semibold text-neutral-900">{item.opening_stock}</p>
            </div>
          </div>

          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-xs text-neutral-600">
            {item.reason_summary}
          </div>

          <div className="space-y-2">
            <p className="text-xs uppercase tracking-wide text-neutral-500">
              {t("planning.decision.label", "Decision")}
            </p>
            <div className="flex flex-wrap gap-2">
              {["approved", "edited", "rejected"].map((choice) => (
                <button
                  key={choice}
                  className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                    action === choice ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-200 text-neutral-600"
                  }`}
                  onClick={() => setAction(choice as "approved" | "edited" | "rejected")}
                >
                  {choice === "approved"
                    ? t("common.status.approved", "Approved")
                    : choice === "edited"
                    ? t("common.status.edited", "Edited")
                    : t("common.status.rejected", "Rejected")}
                </button>
              ))}
            </div>
          </div>

          {action !== "approved" && (
            <div className="space-y-2">
              <label className="text-xs uppercase tracking-wide text-neutral-500">
                {t("planning.decision.finalPrep", "Final prep")}
              </label>
              <input
                type="number"
                min={0}
                className="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
                placeholder={`${item.recommended_prep}`}
                value={finalPrep}
                onChange={(event) => setFinalPrep(event.target.value)}
              />
              <label className="text-xs uppercase tracking-wide text-neutral-500">
                {t("planning.decision.reason", "Reason")}
              </label>
              <textarea
                className="min-h-[80px] w-full rounded-lg border border-neutral-200 p-3 text-sm"
                placeholder={t("planning.decision.reasonRequired", "Reason required for edits or rejections")}
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </div>
          )}

            {validationError && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {validationError}
              </div>
            )}

          <div className="rounded-lg border border-neutral-100 p-3">
            <p className="text-xs uppercase tracking-wide text-neutral-500">
              {t("planning.decision.auditPreview", "Audit preview")}
            </p>
            <AuditPreview events={auditEvents} />
          </div>
        </div>
        <div className="border-t px-5 py-4">
          <div className="flex items-center justify-between">
            <Badge variant="outline">
              {t("planning.decision.finalPrepBadge", "Final prep {{value}}", { value: effectiveFinalPrep })}
            </Badge>
            <Button variant="primary" onClick={handleSubmit} disabled={submitDisabled}>
              {submitting
                ? t("planning.decision.saving", "Saving...")
                : t("planning.decision.submit", "Submit decision")}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
