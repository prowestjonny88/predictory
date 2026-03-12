"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import { formatDateLabel } from "@/lib/i18n";

interface Props {
  title: string;
  date?: string;
  children?: React.ReactNode;
}

export default function Header({ title, date, children }: Props) {
  const { language, t } = useLanguage();

  return (
    <header className="sticky top-0 z-20 bg-white/80 backdrop-blur border-b border-neutral-200 px-6 py-4 flex items-center justify-between gap-4">
      <div>
        <h1 className="text-lg font-bold text-neutral-900">{title}</h1>
        {date && (
          <p className="text-xs text-neutral-400 mt-0.5">
            {t("common.planDate", "Plan date")}:{" "}
            <span className="font-medium text-neutral-600">{formatDateLabel(date, language)}</span>
          </p>
        )}
      </div>
      {children && <div className="flex items-center gap-3">{children}</div>}
    </header>
  );
}
