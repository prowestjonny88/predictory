"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  TrendingUp,
  ClipboardList,
  ShoppingCart,
  AlertTriangle,
  Bot,
  ChefHat,
  GitBranch,
} from "lucide-react";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import LanguageSwitcher from "@/components/i18n/LanguageSwitcher";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", labelKey: "nav.dashboard", fallback: "Dashboard", icon: LayoutDashboard },
  { href: "/forecast", labelKey: "nav.forecast", fallback: "Forecast", icon: TrendingUp },
  { href: "/prep-plan", labelKey: "nav.prepPlan", fallback: "Prep Plan", icon: ClipboardList },
  {
    href: "/replenishment",
    labelKey: "nav.replenishment",
    fallback: "Replenishment",
    icon: ShoppingCart,
  },
  {
    href: "/risk-center",
    labelKey: "nav.riskCenter",
    fallback: "Risk Centre",
    icon: AlertTriangle,
  },
  {
    href: "/scenario-planner",
    labelKey: "nav.scenarioPlanner",
    fallback: "Scenario Planner",
    icon: GitBranch,
  },
  { href: "/copilot", labelKey: "nav.copilot", fallback: "AI Copilot", icon: Bot },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { t } = useLanguage();

  return (
    <>
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 flex-col border-r border-neutral-200 bg-white md:flex">
        <div className="flex items-center gap-2 border-b border-neutral-100 px-5 py-5">
          <ChefHat className="h-6 w-6 text-amber-500" />
          <span className="text-lg font-bold tracking-tight text-neutral-900">
            Bake<span className="text-amber-500">Wise</span>
          </span>
        </div>

        <nav aria-label="Primary" className="scrollbar-hide flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV.map(({ href, labelKey, fallback, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "border border-amber-200 bg-amber-50 text-amber-800"
                    : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
                )}
              >
                <Icon className={cn("h-4 w-4", active ? "text-amber-600" : "text-neutral-400")} />
                {t(labelKey, fallback)}
              </Link>
            );
          })}
        </nav>

        <div className="space-y-3 border-t border-neutral-100 px-5 py-4">
          <LanguageSwitcher compact={false} />
          <div className="text-xs text-neutral-400">{t("nav.footer", "BakeWise v1 · ASEAN demo build")}</div>
        </div>
      </aside>

      <nav
        aria-label="Bottom"
        className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white/95 px-2 py-2 backdrop-blur md:hidden"
      >
        <ul className="scrollbar-hide flex gap-1 overflow-x-auto">
          {NAV.map(({ href, labelKey, fallback, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <li key={href} className="min-w-[84px] shrink-0">
                <Link
                  href={href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex flex-col items-center gap-1 rounded-md px-1 py-2 text-[11px] font-medium",
                    active ? "bg-amber-50 text-amber-700" : "text-neutral-500"
                  )}
                >
                  <Icon className={cn("h-4 w-4", active ? "text-amber-600" : "text-neutral-400")} />
                  <span className="truncate">{t(labelKey, fallback)}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
