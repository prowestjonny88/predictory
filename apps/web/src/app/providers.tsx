"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";

import { CurrencyProvider } from "@/components/CurrencyProvider";
import { LanguageProvider } from "@/components/i18n/LanguageProvider";

export default function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 120_000,
            gcTime: 10 * 60_000,
            retry: 1,
            refetchOnWindowFocus: false,
            refetchOnReconnect: false,
          },
        },
      })
  );

  return (
    <LanguageProvider>
      <CurrencyProvider>
        <QueryClientProvider client={client}>{children}</QueryClientProvider>
      </CurrencyProvider>
    </LanguageProvider>
  );
}
