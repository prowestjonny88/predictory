import type { Metadata } from "next";

import Sidebar from "@/components/Sidebar";

import "./globals.css";
import Providers from "./providers";

export const metadata: Metadata = {
  title: "BakeWise - Bakery Intelligence",
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
          <a href="#main-content" className="skip-link">
            Skip to main content
          </a>
          <Sidebar />
          <main id="main-content" className="flex-1 overflow-auto pb-20 md:ml-60 md:pb-0">
            {children}
          </main>
        </Providers>
      </body>
    </html>
  );
}
