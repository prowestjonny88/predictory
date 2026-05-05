"use client";

import { usePathname } from "next/navigation";

import Sidebar from "@/components/Sidebar";
import SkipLink from "@/components/i18n/SkipLink";
import { cn } from "@/lib/utils";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  return (
    <>
      <SkipLink />
      {!isLandingPage && <Sidebar />}
      <main
        id="main-content"
        className={cn("flex-1 overflow-auto", isLandingPage ? "pb-0" : "pb-20 md:ml-60 md:pb-0")}
      >
        {children}
      </main>
    </>
  );
}