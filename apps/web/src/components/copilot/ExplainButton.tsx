"use client";

import { useState } from "react";
import { Sparkles } from "lucide-react";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { planningApi, type ExplainRecommendationResponse } from "@/lib/api/planning";
import type { ExplainContextType } from "@/types";

interface ExplainButtonProps {
  label?: string;
  title?: string;
  contextType: ExplainContextType;
  evidence: Record<string, unknown>;
  recommendationId?: string | number;
  disabled?: boolean;
  variant?: "outline" | "secondary" | "ghost";
  size?: "sm" | "default";
}

export default function ExplainButton({
  label,
  title,
  contextType,
  evidence,
  recommendationId,
  disabled,
  variant = "outline",
  size = "sm",
}: ExplainButtonProps) {
  const { t, language } = useLanguage();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ExplainRecommendationResponse | null>(null);

  async function loadExplanation() {
    if (response || loading) return;
    setLoading(true);
    setError(null);
    try {
      const payload = recommendationId
        ? await planningApi.explainRecommendation(String(recommendationId), language)
        : await api.explainEvidence({ context_type: contextType, evidence, language });
      setResponse(payload);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("explain.unavailable", "Gemini explanation unavailable."));
    } finally {
      setLoading(false);
    }
  }

  const visibleEvidence = response?.evidence ?? evidence;

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) void loadExplanation();
      }}
    >
      <SheetTrigger asChild>
        <Button variant={variant} size={size} disabled={disabled}>
          <Sparkles className="mr-1.5 h-3.5 w-3.5" />
          {label ?? t("explain.button", "Explain")}
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>{title ?? t("explain.title", "Gemini explanation")}</SheetTitle>
          <SheetDescription>
            {t(
              "explain.description",
              "Gemini explains the backend evidence shown here. It does not calculate or change these numbers."
            )}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          <div className="inline-flex rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-700">
            {response?.source_type === "llm_rephrased"
              ? t("explain.sourceGemini", "Source: Gemini explanation")
              : t("explain.sourcePending", "Source: backend evidence")}
          </div>

          {loading && (
            <div className="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">
              {t("explain.loading", "Reading backend evidence and asking Gemini...")}
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              {error}
            </div>
          )}

          {response?.explanation && (
            <div className="rounded-lg border border-sky-100 bg-sky-50/50 p-4 text-sm leading-relaxed text-neutral-800">
              {response.explanation}
            </div>
          )}

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {t("explain.evidence", "Evidence used")}
            </p>
            <div className="space-y-2">
              {Object.entries(visibleEvidence).map(([key, value]) => (
                <div
                  key={key}
                  className="grid grid-cols-[140px_1fr] gap-3 rounded-md border border-neutral-100 bg-white px-3 py-2 text-xs"
                >
                  <span className="font-medium text-neutral-500">{key}</span>
                  <span className="break-words text-neutral-800">{formatEvidenceValue(value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}

function formatEvidenceValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unavailable";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return JSON.stringify(value);
}
