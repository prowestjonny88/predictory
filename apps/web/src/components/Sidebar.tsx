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
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard",      label: "Dashboard",      icon: LayoutDashboard },
  { href: "/forecast",       label: "Forecast",       icon: TrendingUp },
  { href: "/prep-plan",      label: "Prep Plan",      icon: ClipboardList },
  { href: "/replenishment",  label: "Replenishment",  icon: ShoppingCart },
  { href: "/risk-center",    label: "Risk Centre",    icon: AlertTriangle },
  { href: "/copilot",        label: "AI Copilot",     icon: Bot },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 w-60 bg-white border-r border-neutral-200 flex flex-col z-30">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-5 border-b border-neutral-100">
        <ChefHat className="h-6 w-6 text-amber-500" />
        <span className="font-bold text-lg tracking-tight text-neutral-900">
          Bake<span className="text-amber-500">Wise</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto scrollbar-hide">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                active
                  ? "bg-amber-50 text-amber-700"
                  : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
              )}
            >
              <Icon className={cn("h-4 w-4", active ? "text-amber-500" : "text-neutral-400")} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-neutral-100 text-xs text-neutral-400">
        BakeWise v1 · Day 1 Build
      </div>
    </aside>
  );
}
