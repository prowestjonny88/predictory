import type { LanguageCode } from "@/types";

import { formatNumber } from "@/lib/i18n";

export type AseanCurrencyCode =
  | "BND"
  | "KHR"
  | "IDR"
  | "LAK"
  | "MYR"
  | "MMK"
  | "PHP"
  | "SGD"
  | "THB"
  | "VND";

export interface CurrencyInfo {
  code: AseanCurrencyCode;
  symbol: string;
  name: string;
  country: string;
  minorUnitDigits: number;
  directTokens: string[];
  localeTokens: string[];
}

export interface CurrencyDetection {
  currency: CurrencyInfo;
  confidence: "high" | "medium" | "low";
  detectedFrom: "currency_marker" | "country_marker";
}

export const CURRENCY_STORAGE_KEY = "predictory.currency";

export const ASEAN_CURRENCIES: Record<AseanCurrencyCode, CurrencyInfo> = {
  BND: {
    code: "BND",
    symbol: "B$",
    name: "Brunei Dollar",
    country: "Brunei",
    minorUnitDigits: 2,
    directTokens: ["BND", "B$", "BRUNEI DOLLAR"],
    localeTokens: ["BRUNEI", "BANDAR SERI BEGAWAN"],
  },
  KHR: {
    code: "KHR",
    symbol: "៛",
    name: "Cambodian Riel",
    country: "Cambodia",
    minorUnitDigits: 0,
    directTokens: ["KHR", "៛", "RIEL"],
    localeTokens: ["CAMBODIA", "PHNOM PENH", "SIEM REAP"],
  },
  IDR: {
    code: "IDR",
    symbol: "Rp",
    name: "Indonesian Rupiah",
    country: "Indonesia",
    minorUnitDigits: 0,
    directTokens: ["IDR", "RP", "RUPIAH"],
    localeTokens: ["INDONESIA", "JAKARTA", "BALI", "SURABAYA", "BANDUNG"],
  },
  LAK: {
    code: "LAK",
    symbol: "₭",
    name: "Lao Kip",
    country: "Laos",
    minorUnitDigits: 0,
    directTokens: ["LAK", "₭", "KIP"],
    localeTokens: ["LAOS", "LAO", "VIENTIANE", "LUANG PRABANG"],
  },
  MYR: {
    code: "MYR",
    symbol: "RM",
    name: "Malaysian Ringgit",
    country: "Malaysia",
    minorUnitDigits: 2,
    directTokens: ["MYR", "RM", "RINGGIT"],
    localeTokens: ["MALAYSIA", "KUALA LUMPUR", "SELANGOR", "JOHOR", "PENANG", "KLCC", "BANGSAR"],
  },
  MMK: {
    code: "MMK",
    symbol: "K",
    name: "Myanmar Kyat",
    country: "Myanmar",
    minorUnitDigits: 0,
    directTokens: ["MMK", "KYAT"],
    localeTokens: ["MYANMAR", "YANGON", "MANDALAY", "NAYPYIDAW"],
  },
  PHP: {
    code: "PHP",
    symbol: "₱",
    name: "Philippine Peso",
    country: "Philippines",
    minorUnitDigits: 2,
    directTokens: ["PHP", "₱", "PHILIPPINE PESO"],
    localeTokens: ["PHILIPPINES", "MANILA", "CEBU", "QUEZON"],
  },
  SGD: {
    code: "SGD",
    symbol: "S$",
    name: "Singapore Dollar",
    country: "Singapore",
    minorUnitDigits: 2,
    directTokens: ["SGD", "S$", "SINGAPORE DOLLAR"],
    localeTokens: ["SINGAPORE"],
  },
  THB: {
    code: "THB",
    symbol: "฿",
    name: "Thai Baht",
    country: "Thailand",
    minorUnitDigits: 2,
    directTokens: ["THB", "฿", "BAHT"],
    localeTokens: ["THAILAND", "BANGKOK", "CHIANG MAI", "PHUKET"],
  },
  VND: {
    code: "VND",
    symbol: "₫",
    name: "Vietnamese Dong",
    country: "Vietnam",
    minorUnitDigits: 0,
    directTokens: ["VND", "₫", "DONG"],
    localeTokens: ["VIETNAM", "HANOI", "HO CHI MINH", "SAIGON", "DA NANG"],
  },
};

export const DEFAULT_CURRENCY = ASEAN_CURRENCIES.MYR;

export function normalizeCurrencyCode(value: string | null | undefined): AseanCurrencyCode {
  const code = value?.trim().toUpperCase();
  return code && code in ASEAN_CURRENCIES ? (code as AseanCurrencyCode) : DEFAULT_CURRENCY.code;
}

export function detectCurrencyFromCsvText(text: string): CurrencyDetection | null {
  const sample = text.slice(0, 200_000).toUpperCase();
  const scores = Object.values(ASEAN_CURRENCIES)
    .map((currency) => {
      const directScore = currency.directTokens.reduce(
        (score, token) => score + countToken(sample, token.toUpperCase()) * 4,
        0
      );
      const localeScore = currency.localeTokens.reduce(
        (score, token) => score + countToken(sample, token.toUpperCase()),
        0
      );
      return { currency, directScore, localeScore, score: directScore + localeScore };
    })
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score);

  const best = scores[0];
  if (!best) {
    return null;
  }

  return {
    currency: best.currency,
    confidence: best.directScore > 0 ? "high" : best.localeScore >= 2 ? "medium" : "low",
    detectedFrom: best.directScore > 0 ? "currency_marker" : "country_marker",
  };
}

export function formatCurrencyAmount(
  value: number,
  currency: CurrencyInfo,
  language: LanguageCode,
  options?: Intl.NumberFormatOptions
): string {
  const maximumFractionDigits = options?.maximumFractionDigits ?? currency.minorUnitDigits;
  const minimumFractionDigits = options?.minimumFractionDigits ?? maximumFractionDigits;
  const formatted = formatNumber(value, language, {
    minimumFractionDigits,
    maximumFractionDigits,
    ...options,
  });

  return `${currency.symbol} ${formatted}`;
}

function countToken(sample: string, token: string): number {
  if (!token) {
    return 0;
  }
  const escaped = token.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = /^[A-Z0-9 ]+$/.test(token)
    ? new RegExp(`(^|[^A-Z0-9])${escaped}($|[^A-Z0-9])`, "g")
    : new RegExp(escaped, "g");
  return sample.match(pattern)?.length ?? 0;
}
