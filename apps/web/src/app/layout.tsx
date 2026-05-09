import type { Metadata } from "next";

import AppShell from "@/components/AppShell";

import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Predictory",
  description: "Predictory",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="flex min-h-screen bg-neutral-50" suppressHydrationWarning>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
