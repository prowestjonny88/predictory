"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactNode, useState } from "react";

import { LanguageProvider } from "@/components/i18n/LanguageProvider";

export default function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            retry: 1,
          },
        },
      })
  );

  return (
    <LanguageProvider>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </LanguageProvider>
  );
}
