"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  BarChart3,
  TrendingUp,
  ClipboardList,
  Bot,
  ShoppingCart,
  ChefHat,
  Package,
  PackageCheck,
  Boxes,
  GitBranch,
} from "lucide-react";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import LanguageSwitcher from "@/components/i18n/LanguageSwitcher";
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

const CORE_NAV = [
  { href: "/dashboard", labelKey: "nav.dashboard", defaultText: "Dashboard", icon: BarChart3 },
  { href: "/daily-planning", labelKey: "nav.dailyPlanning", defaultText: "Daily Planning", icon: ClipboardList },
  { href: "/forecast", labelKey: "nav.forecastEvidence", defaultText: "Forecast Evidence", icon: TrendingUp },
  {
    href: "/replenishment",
    labelKey: "nav.replenishment",
    defaultText: "Replenishment",
    icon: ShoppingCart,
  },
  { href: "/catalog", labelKey: "nav.catalog", defaultText: "SKU Catalog", icon: Package },
];

const MORE_NAV = [
  { href: "/risk-center", labelKey: "nav.riskCenter", defaultText: "Risk Center", icon: AlertTriangle },
  { href: "/prep-plan", labelKey: "nav.approvedPrepSheet", defaultText: "Approved Prep Sheet", icon: PackageCheck },
  { href: "/stock", labelKey: "nav.stock", defaultText: "Stock", icon: Boxes },
  { href: "/copilot", labelKey: "nav.copilot", defaultText: "Copilot", icon: Bot },
  { href: "/scenario-planner", labelKey: "nav.scenarioPlanner", defaultText: "Scenario Planner", icon: GitBranch },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { t } = useLanguage();
  const { setOpenMobile } = useSidebar();

  return (
    <ShadcnSidebar>
      <SidebarHeader className="border-b border-sidebar-border p-4">
        <div className="flex items-center gap-2">
          <ChefHat className="h-6 w-6 text-amber-500" />
          <span className="text-lg font-bold tracking-tight text-neutral-900">
            Predict<span className="text-amber-500">ory</span>
          </span>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <NavGroup
          items={CORE_NAV}
          pathname={pathname}
          title={t("nav.core", "Core")}
          t={t}
          onNavigate={() => setOpenMobile(false)}
        />
        <NavGroup
          items={MORE_NAV}
          pathname={pathname}
          title={t("nav.moreTools", "More Tools")}
          t={t}
          onNavigate={() => setOpenMobile(false)}
        />
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-4 space-y-3">
        <LanguageSwitcher compact={false} />
        <div className="text-xs text-neutral-400">{t("nav.footer", "Predictory v2")}</div>
      </SidebarFooter>
    </ShadcnSidebar>
  );
}

function NavGroup({
  items,
  pathname,
  title,
  t,
  onNavigate,
}: {
  items: typeof CORE_NAV;
  pathname: string;
  title: string;
  t: (key: string, fallback: string) => string;
  onNavigate: () => void;
}) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{title}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map(({ href, labelKey, defaultText, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + "/");
            return (
              <SidebarMenuItem key={href}>
                <SidebarMenuButton
                  asChild
                  isActive={active}
                  tooltip={t(labelKey, defaultText)}
                  onClick={onNavigate}
                >
                  <Link href={href}>
                    <Icon className={active ? "text-amber-600" : "text-neutral-500"} />
                    <span className={active ? "font-semibold text-amber-800" : ""}>
                      {t(labelKey, defaultText)}
                    </span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
