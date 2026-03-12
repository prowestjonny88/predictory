"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import type { LanguageCode } from "@/types";

const OPTIONS: Array<{ value: LanguageCode; label: string }> = [
  { value: "en", label: "English (Malaysia/Singapore)" },
  { value: "ms", label: "Bahasa Melayu (Malaysia/Brunei)" },
  { value: "zh-CN", label: "Chinese Simplified (Singapore)" },
];

interface Props {
  compact?: boolean;
}

export default function LanguageSwitcher({ compact = false }: Props) {
  const { language, setLanguage, t } = useLanguage();

  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-neutral-500">
      {!compact && <span>{t("language.label", "Language")}</span>}
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as LanguageCode)}
        aria-label={t("language.label", "Language")}
        className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm text-neutral-700"
      >
        {OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
