import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateDaypart } from "@/lib/i18n";
import type { ManagerNoteResponse } from "@/lib/api/planning";

interface Props {
  onParse: (note: string) => Promise<ManagerNoteResponse | null>;
  onApply: (adjustment: ManagerNoteResponse["parsed_adjustment"]) => Promise<void>;
}

export default function ManagerNotePanel({ onParse, onApply }: Props) {
  const { t, language } = useLanguage();
  const [note, setNote] = useState("");
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<ManagerNoteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);
  const [adjustmentPct, setAdjustmentPct] = useState("");
  const [adjustmentReason, setAdjustmentReason] = useState("");

  async function handleParse() {
    setParsing(true);
    setError(null);
    try {
      const response = await onParse(note);
      setResult(response);
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
    await onApply({
      ...result.parsed_adjustment,
      suggested_adjustment_pct: Number.isNaN(parsedPct) ? result.parsed_adjustment.suggested_adjustment_pct : parsedPct,
      reason: adjustmentReason.trim() || result.parsed_adjustment.reason,
      requires_confirmation: true,
    });
    setApplying(false);
    setResult(null);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("planning.managerNote.title", "Manager note parser")}</CardTitle>
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
          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-sm">
            <p className="text-xs uppercase tracking-wide text-neutral-500">
              {t("planning.managerNote.suggested", "Suggested adjustment")}
            </p>
            <p className="font-semibold text-neutral-900">
              {result.parsed_adjustment.outlet_id} /{" "}
              {translateDaypart(language, result.parsed_adjustment.daypart.toLowerCase())} /{" "}
              {result.parsed_adjustment.sku_category}
            </p>
            <p className="text-xs text-neutral-500">
              {result.parsed_adjustment.suggested_adjustment_pct > 0 ? "+" : ""}
              {result.parsed_adjustment.suggested_adjustment_pct}% / {result.parsed_adjustment.reason}
            </p>
            <p className="mt-2 text-xs text-neutral-500">{result.explanation}</p>

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
              <Button variant="primary" size="sm" onClick={handleApply} disabled={applying}>
                {applying
                  ? t("planning.managerNote.applying", "Applying...")
                  : t("planning.managerNote.apply", "Confirm and apply")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setResult(null)}>
                {t("planning.managerNote.ignore", "Ignore")}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
