import type { Metadata } from "next";
import "./globals.css";
import Providers from "./providers";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "BakeWise – Bakery Intelligence",
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
          <Sidebar />
          <div className="ml-60 flex-1 overflow-auto">{children}</div>
        </Providers>
      </body>
    </html>
  );
}
