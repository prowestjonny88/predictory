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

type NavItem = {
  href: string;
  labelKey: string;
  defaultText: string;
  icon: typeof BarChart3;
};

const CORE_NAV: NavItem[] = [
  { href: "/dashboard", labelKey: "nav.dashboard", defaultText: "Dashboard", icon: BarChart3 },
  { href: "/daily-planning", labelKey: "nav.dailyPlanning", defaultText: "Daily Planning", icon: ClipboardList },
  { href: "/risk-center", labelKey: "nav.riskCenter", defaultText: "Risk Centre", icon: AlertTriangle },
  {
    href: "/replenishment",
    labelKey: "nav.replenishment",
    defaultText: "Replenishment",
    icon: ShoppingCart,
  },
];

const DECISION_NAV: NavItem[] = [
  { href: "/scenario-planner", labelKey: "nav.scenarioPlanner", defaultText: "Scenario Planner", icon: GitBranch },
];

const ADMIN_NAV: NavItem[] = [
  { href: "/forecast", labelKey: "nav.forecastEvidence", defaultText: "Forecast Evidence", icon: TrendingUp },
  { href: "/catalog", labelKey: "nav.catalog", defaultText: "SKU Catalog", icon: Package },
  { href: "/stock", labelKey: "nav.stock", defaultText: "Current Stock", icon: Boxes },
  { href: "/prep-plan", labelKey: "nav.kitchenPrepSheet", defaultText: "Kitchen Prep Sheet", icon: PackageCheck },
  { href: "/copilot", labelKey: "nav.aiCopilot", defaultText: "AI Copilot", icon: Bot },
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
          title={t("nav.coreWorkflow", "Core Workflow")}
          t={t}
          onNavigate={() => setOpenMobile(false)}
        />
        <NavGroup
          items={DECISION_NAV}
          pathname={pathname}
          title={t("nav.decisionTools", "Decision Tools")}
          t={t}
          onNavigate={() => setOpenMobile(false)}
        />
        <NavGroup
          items={ADMIN_NAV}
          pathname={pathname}
          title={t("nav.dataAdmin", "Data / Admin")}
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
  items: NavItem[];
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
