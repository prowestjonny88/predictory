import type { Metadata } from "next";

import Sidebar from "@/components/Sidebar";
import SkipLink from "@/components/i18n/SkipLink";

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
          <SkipLink />
          <Sidebar />
          <main id="main-content" className="flex-1 overflow-auto pb-20 md:ml-60 md:pb-0">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
