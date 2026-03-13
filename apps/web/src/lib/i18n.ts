import type { LanguageCode } from "@/types";

import en from "@/locales/en";
import ms from "@/locales/ms";
import zhCN from "@/locales/zh-CN";

export type Dictionary = Record<string, string>;

export const DEFAULT_LANGUAGE: LanguageCode = "en";
export const LANGUAGE_STORAGE_KEY = "predictory.language";

const localeMap: Record<LanguageCode, string> = {
  en: "en-MY",
  ms: "ms-MY",
  "zh-CN": "zh-CN",
};

const dictionaries: Record<LanguageCode, Dictionary> = {
  en,
  ms,
  "zh-CN": zhCN,
};

export function normalizeLanguage(raw: string | null | undefined): LanguageCode {
  if (raw === "ms" || raw === "zh-CN") {
    return raw;
  }
  return DEFAULT_LANGUAGE;
}

export function getLocale(language: LanguageCode): string {
  return localeMap[language];
}

export function translate(
  language: LanguageCode,
  key: string,
  fallback?: string,
  values?: Record<string, string | number>
): string {
  const template = dictionaries[language][key] ?? dictionaries.en[key] ?? fallback ?? key;
  if (!values) {
    return template;
  }

  return Object.entries(values).reduce(
    (result, [name, value]) => result.replaceAll(`{{${name}}}`, String(value)),
    template
  );
}

export function formatNumber(
  value: number,
  language: LanguageCode,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat(getLocale(language), options).format(value);
}

export function formatPercent(
  value: number,
  language: LanguageCode,
  options?: Intl.NumberFormatOptions
): string {
  return `${formatNumber(value, language, { maximumFractionDigits: 1, ...options })}%`;
}

export function formatDateLabel(value: string, language: LanguageCode): string {
  const parsed = new Date(`${value}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(getLocale(language), {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(parsed);
}

export function translateRiskLevel(language: LanguageCode, risk: string): string {
  return translate(language, `common.risk.${risk}`, risk);
}

export function translateDaypart(language: LanguageCode, daypart: string): string {
  return translate(language, `common.daypart.${daypart}`, daypart);
}

export function translateOverrideType(language: LanguageCode, overrideType: string): string {
  return translate(language, `common.override.${overrideType}`, overrideType);
}

export function translateStatus(language: LanguageCode, status: string): string {
  return translate(language, `common.status.${status}`, status);
}
