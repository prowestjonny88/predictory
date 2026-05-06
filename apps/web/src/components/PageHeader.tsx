"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import { formatDateLabel } from "@/lib/i18n";
import { cn } from "@/lib/utils";

interface Props {
  title: string;
  description?: string;
  date?: string;
  children?: React.ReactNode;
  className?: string;
}

export default function PageHeader({ title, description, date, children, className }: Props) {
  const { language, t } = useLanguage();

  return (
    <div className={cn("flex flex-col gap-4 pb-6 md:flex-row md:items-center md:justify-between", className)}>
      <div className="space-y-1.5">
        <h1 className="text-2xl font-bold tracking-tight text-neutral-900 md:text-3xl">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
        {date && (
          <p className="text-sm text-muted-foreground">
            {t("common.planDate", "Plan date")}:{" "}
            <span className="font-semibold text-neutral-700">{formatDateLabel(date, language)}</span>
          </p>
        )}
      </div>
      {children && (
        <div className="flex flex-wrap items-center gap-3">
          {children}
        </div>
      )}
    </div>
  );
}
