"use client";

import { usePathname } from "next/navigation";

import Sidebar from "@/components/Sidebar";
import SkipLink from "@/components/i18n/SkipLink";
import { SidebarProvider, SidebarTrigger, SidebarInset } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

import { TooltipProvider } from "@/components/ui/tooltip";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  if (isLandingPage) {
    return (
      <main id="main-content" className="flex flex-1 flex-col overflow-auto">
        {children}
      </main>
    );
  }

  return (
    <TooltipProvider>
      <SidebarProvider>
        <SkipLink />
        <Sidebar />
        <SidebarInset>
          <header className="flex h-14 items-center gap-2 border-b bg-white px-4 md:hidden">
            <SidebarTrigger />
            <span className="font-bold tracking-tight text-neutral-900">
              Predict<span className="text-amber-500">ory</span>
            </span>
          </header>
          <main id="main-content" className="flex flex-1 flex-col overflow-auto bg-neutral-50">
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
    </TooltipProvider>
  );
}