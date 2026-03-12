"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import { translateRiskLevel } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/types";

interface Props {
  riskLevel: RiskLevel;
  title: string;
  subtitle?: string;
  meta?: string;
  children?: React.ReactNode;
}

const borderColors: Record<RiskLevel, string> = {
  critical: "border-l-red-600",
  high:     "border-l-orange-500",
  medium:   "border-l-yellow-500",
  low:      "border-l-green-500",
};

const badgeColors: Record<RiskLevel, string> = {
  critical: "bg-red-100 text-red-700",
  high:     "bg-orange-100 text-orange-700",
  medium:   "bg-yellow-100 text-yellow-700",
  low:      "bg-green-100 text-green-700",
};

export default function AlertCard({ riskLevel, title, subtitle, meta, children }: Props) {
  const { language } = useLanguage();

  return (
    <div
      className={cn(
        "bg-white rounded-lg border border-l-4 px-4 py-3 shadow-sm",
        borderColors[riskLevel]
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-neutral-800 truncate">{title}</p>
          {subtitle && (
            <p className="text-xs text-neutral-500 mt-0.5">{subtitle}</p>
          )}
          {meta && <p className="text-xs text-neutral-400 mt-0.5">{meta}</p>}
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold capitalize",
            badgeColors[riskLevel]
          )}
        >
          {translateRiskLevel(language, riskLevel)}
        </span>
      </div>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}
