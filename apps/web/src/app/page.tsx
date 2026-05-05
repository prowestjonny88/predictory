"use client";

import Link from "next/link";
import { ArrowRight, Sparkles, TrendingUp, AlertTriangle, Truck, Bot, LogOut } from "lucide-react";

import { useLanguage } from "@/components/i18n/LanguageProvider";

export default function RootPage() {
  const { t } = useLanguage();

  const features = [
    {
      icon: TrendingUp,
      title: t("landing.feature.forecast.title", "Smart Demand Forecasting"),
      description: t(
        "landing.feature.forecast.description",
        "AI-powered predictions based on historical sales, weather, and seasonal patterns to guide your daily bake quantities."
      ),
    },
    {
      icon: AlertTriangle,
      title: t("landing.feature.risk.title", "Waste & Stockout Prevention"),
      description: t(
        "landing.feature.risk.description",
        "Real-time alerts for overstocked items and potential stockouts, helping you minimize waste and lost sales."
      ),
    },
    {
      icon: Truck,
      title: t("landing.feature.replenishment.title", "Optimized Replenishment"),
      description: t(
        "landing.feature.replenishment.description",
        "Automated suggestions for ingredient orders and product transfers between locations based on predicted demand."
      ),
    },
    {
      icon: Bot,
      title: t("landing.feature.copilot.title", "AI Copilot Assistant"),
      description: t(
        "landing.feature.copilot.description",
        "Multilingual chat assistant that answers questions about forecasts, inventory, and provides planning recommendations."
      ),
    },
    {
      icon: LogOut,
      title: t("landing.feature.audit.title", "Manager Approvals & Audit Trail"),
      description: t(
        "landing.feature.audit.description",
        "Track all planning decisions with an audit trail and manager approval workflows for compliance and accountability."
      ),
    },
    {
      icon: Sparkles,
      title: t("landing.feature.interface.title", "Clean, Calm Interface"),
      description: t(
        "landing.feature.interface.description",
        "Designed for bakery teams with a simple, intuitive workspace that reduces cognitive load and accelerates decision-making."
      ),
    },
  ];

  return (
    <div className="page-enter relative overflow-hidden">
      {/* Hero Background with Bakery Image */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage:
            'linear-gradient(135deg, rgba(251, 191, 36, 0.85) 0%, rgba(120, 113, 108, 0.85) 100%), url("https://images.unsplash.com/photo-1555939594-58d7cb561141?w=1600&q=80")',
          backgroundAttachment: "fixed",
        }}
      />

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(251,191,36,0.15),transparent_30%),radial-gradient(circle_at_bottom_right,rgba(245,158,11,0.1),transparent_35%)]" />

      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute left-[-8rem] top-16 h-64 w-64 rounded-full bg-amber-200/20 blur-3xl" />
        <div className="absolute right-[-6rem] bottom-32 h-56 w-56 rounded-full bg-neutral-900/5 blur-3xl" />
      </div>

      <main className="relative mx-auto w-full">
        {/* Header */}
        <header className="flex items-center justify-between border-b border-white/20 bg-white/10 backdrop-blur-md px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/95 text-amber-700 shadow-lg">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-white">Predictory</p>
              <p className="text-xs text-white/80">{t("landing.brandline", "Bakery Intelligence Platform")}</p>
            </div>
          </div>
        </header>

        {/* Hero Section */}
        <section className="flex min-h-[70vh] items-center px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-4xl">
            <div className="space-y-8">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 rounded-full border border-white/30 bg-white/10 px-4 py-2 text-sm font-medium text-white backdrop-blur-sm">
                <Sparkles className="h-4 w-4" />
                {t("landing.badge", "AI-Powered Planning for Modern Bakeries")}
              </div>

              {/* Main Heading */}
              <div className="space-y-6">
                <h1 className="text-5xl font-black tracking-tight text-white drop-shadow-lg sm:text-6xl lg:text-7xl">
                  {t("landing.heroTitle", "Plan smarter. Waste less. Earn more.")}
                </h1>
                <p className="max-w-2xl text-lg leading-8 text-white/95 drop-shadow">
                  {t(
                    "landing.heroDescription",
                    "Predictory is the daily planning dashboard for bakery and café teams. Transform sales forecasts into smart prep plans, prevent waste, and give your managers the clarity they need to make confident decisions."
                  )}
                </p>
              </div>

              {/* Single CTA Button */}
              <div>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-4 text-base font-bold text-amber-900 shadow-2xl transition-all hover:-translate-y-1 hover:shadow-3xl hover:bg-amber-50"
                >
                  {t("landing.cta", "Go to Dashboard")}
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="relative px-4 py-20 sm:px-6 lg:px-8 bg-white/5 backdrop-blur-sm">
          <div className="mx-auto max-w-6xl">
            <div className="mb-16 space-y-4">
              <h2 className="text-3xl font-black text-white drop-shadow sm:text-4xl">
                {t("landing.whatDoes", "What Predictory Does")}
              </h2>
              <p className="max-w-2xl text-lg text-white/90 drop-shadow">
                {t(
                  "landing.featureIntro",
                  "Everything your bakery team needs to plan confidently, reduce waste, and optimize operations—all in one calm, intuitive interface."
                )}
              </p>
            </div>

            {/* Feature Grid */}
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {features.map((feature, index) => {
                const Icon = feature.icon;
                return (
                  <div
                    key={index}
                    className="group rounded-2xl border border-white/20 bg-white/8 p-6 backdrop-blur-sm transition-all hover:border-white/40 hover:bg-white/12"
                  >
                    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-white/20 text-white group-hover:bg-white/30 transition-colors">
                      <Icon className="h-6 w-6" />
                    </div>
                    <h3 className="text-lg font-bold text-white mb-2">{feature.title}</h3>
                    <p className="text-sm leading-6 text-white/80">{feature.description}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="relative px-4 py-16 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-4xl">
            <div className="rounded-2xl border border-white/20 bg-white/10 px-8 py-12 backdrop-blur-sm text-center space-y-6">
              <h2 className="text-3xl font-black text-white drop-shadow">
                {t("landing.ctaHeading", "Ready to transform your bakery operations?")}
              </h2>
              <p className="max-w-2xl mx-auto text-lg text-white/90 drop-shadow">
                {t(
                  "landing.ctaBody",
                  "Join bakery teams that are using Predictory to make smarter decisions and reduce waste by up to 30%."
                )}
              </p>
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-3 text-base font-bold text-amber-900 shadow-xl transition-all hover:-translate-y-0.5 hover:shadow-2xl hover:bg-amber-50"
              >
                {t("landing.ctaSecondary", "Start Planning Today")}
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 bg-white/5 px-4 py-8 text-center text-sm text-white/70 backdrop-blur-sm">
          <p>{t("landing.footer", "© 2026 Predictory. Designed for bakery teams. Built with care.")}</p>
        </footer>
      </main>
    </div>
  );
}
