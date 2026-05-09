"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ASEAN_CURRENCIES,
  CURRENCY_STORAGE_KEY,
  DEFAULT_CURRENCY,
  formatCurrencyAmount,
  normalizeCurrencyCode,
  type AseanCurrencyCode,
  type CurrencyInfo,
} from "@/lib/currency";
import type { LanguageCode } from "@/types";

interface CurrencyContextValue {
  currency: CurrencyInfo;
  setCurrencyCode: (code: AseanCurrencyCode) => void;
  formatCurrency: (
    value: number,
    language: LanguageCode,
    options?: Intl.NumberFormatOptions
  ) => string;
}

const CurrencyContext = createContext<CurrencyContextValue | null>(null);

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const [currencyCode, setCurrencyCodeState] = useState<AseanCurrencyCode>(DEFAULT_CURRENCY.code);

  useEffect(() => {
    setCurrencyCodeState(normalizeCurrencyCode(window.localStorage.getItem(CURRENCY_STORAGE_KEY)));
  }, []);

  const setCurrencyCode = (code: AseanCurrencyCode) => {
    setCurrencyCodeState(code);
    window.localStorage.setItem(CURRENCY_STORAGE_KEY, code);
  };

  const value = useMemo<CurrencyContextValue>(() => {
    const currency = ASEAN_CURRENCIES[currencyCode] ?? DEFAULT_CURRENCY;
    return {
      currency,
      setCurrencyCode,
      formatCurrency: (amount, language, options) =>
        formatCurrencyAmount(amount, currency, language, options),
    };
  }, [currencyCode]);

  return <CurrencyContext.Provider value={value}>{children}</CurrencyContext.Provider>;
}

export function useCurrency() {
  const context = useContext(CurrencyContext);
  if (!context) {
    throw new Error("useCurrency must be used within CurrencyProvider");
  }
  return context;
}
