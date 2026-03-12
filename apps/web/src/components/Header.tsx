"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import LanguageSwitcher from "@/components/i18n/LanguageSwitcher";
import { formatDateLabel } from "@/lib/i18n";

interface Props {
  title: string;
  date?: string;
  children?: React.ReactNode;
}

export default function Header({ title, date, children }: Props) {
  const { language, t } = useLanguage();

  return (
    <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 px-4 py-3 backdrop-blur md:px-6 md:py-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-lg font-bold leading-tight text-neutral-900 md:text-xl">{title}</h1>
        {date && (
          <p className="mt-0.5 text-xs text-neutral-500">
            {t("common.planDate", "Plan date")}:{" "}
            <span className="font-semibold text-neutral-700">{formatDateLabel(date, language)}</span>
          </p>
        )}
        </div>
        {children && (
          <div className="flex flex-wrap items-center gap-2 md:justify-end md:gap-3">{children}</div>
        )}
        <div className="md:hidden">
          <LanguageSwitcher compact />
        </div>
      </div>
    </header>
  );
}
