"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import type { LanguageCode } from "@/types";

const OPTIONS: Array<{ value: LanguageCode; label: string }> = [
  { value: "en", label: "English" },
  { value: "ms", label: "Bahasa Melayu" },
  { value: "zh-CN", label: "中文简体" },
];

export default function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();

  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-neutral-500">
      <span>{t("language.label", "Language")}</span>
      <select
        value={language}
        onChange={(event) => setLanguage(event.target.value as LanguageCode)}
        className="rounded-md border border-neutral-300 bg-white px-2 py-1.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-amber-400"
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
