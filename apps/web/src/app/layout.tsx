import type { Metadata } from "next";

import AppShell from "@/components/AppShell";

import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "Predictory - Bakery Intelligence",
  description: "AI-powered daily planning for bakery operations",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="flex min-h-screen bg-neutral-50">
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
