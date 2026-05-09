"use client";

import Image from "next/image";
import Link from "next/link";
import { AlertTriangle, ArrowRight, Bot, Sparkles, TrendingUp, Truck } from "lucide-react";

import { useLanguage } from "@/components/i18n/LanguageProvider";

const imageProps = {
  priority: true,
  unoptimized: true,
} as const;

export default function RootPage() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900 selection:bg-brand-amber selection:text-white">
      <nav className="fixed top-0 z-50 w-full border-b border-stone-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-brand-amber text-white shadow-sm">
                <Sparkles className="h-4 w-4" />
              </div>
              <span className="text-xl font-bold tracking-tight text-stone-800">Predictory</span>
            </div>
          </div>
        </div>
      </nav>

      <section className="relative min-h-[86vh] overflow-hidden pt-24 sm:pt-28 lg:pt-32">
        <div className="absolute inset-0">
          <Image
            src="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&q=80"
            alt="Bakery counter"
            fill
            className="object-cover opacity-25"
            {...imageProps}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-stone-50 via-stone-50/90 to-stone-50/60" />
          <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-white to-transparent" />
        </div>

        <div className="relative z-10 mx-auto grid max-w-7xl items-center gap-10 px-4 pb-16 sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:px-8 lg:pb-20">
          <div className="max-w-3xl pt-8 lg:pt-10">
            <div className="mb-6 inline-flex items-center gap-2 rounded-md border border-brand-amber/25 bg-brand-amber-light px-3 py-2 text-sm font-semibold text-brand-amber-dark">
              <Sparkles className="h-4 w-4" />
              <span>{t("landing.badge", "AI-Powered Planning for Modern Bakeries")}</span>
            </div>

            <h1 className="mb-6 max-w-4xl text-4xl font-black leading-[1.05] tracking-normal text-stone-950 sm:text-5xl lg:text-6xl">
              {t("landing.heroTitle", "Plan Smarter. Waste Less. Earn More.")}
            </h1>

            <p className="mb-8 max-w-2xl text-lg leading-8 text-stone-700">
              {t(
                "landing.heroDescription",
                "Predictory is the daily planning dashboard for bakery and cafe teams. Transform sales forecasts into smart prep plans, prevent waste, and give your managers the clarity they need to make confident decisions."
              )}
            </p>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/data-upload"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-amber px-6 py-3 text-base font-bold text-white shadow-lg shadow-brand-amber/25 transition hover:bg-brand-amber-dark active:scale-[0.99]"
              >
                {t("landing.cta", "Go to Dashboard")}
                <ArrowRight className="h-5 w-5" />
              </Link>
            </div>

            <div className="mt-10 grid max-w-xl grid-cols-3 gap-6 border-t border-stone-300 pt-6">
              <div>
                <p className="text-2xl font-black text-stone-950">30%</p>
                <p className="text-sm font-medium text-stone-600">less waste</p>
              </div>
              <div>
                <p className="text-2xl font-black text-stone-950">3</p>
                <p className="text-sm font-medium text-stone-600">languages</p>
              </div>
              <div>
                <p className="text-2xl font-black text-stone-950">1</p>
                <p className="text-sm font-medium text-stone-600">daily plan</p>
              </div>
            </div>
          </div>

          <div className="relative hidden aspect-[4/5] overflow-hidden rounded-lg shadow-2xl shadow-stone-900/15 lg:block">
            <Image
              src="https://images.unsplash.com/photo-1509440159596-0249088772ff?w=900&q=80"
              alt="Fresh bakery counter"
              fill
              className="object-cover"
              {...imageProps}
            />
            <div className="absolute inset-0 bg-gradient-to-t from-stone-950/70 via-transparent to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-6 text-white">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-brand-amber-light">Tomorrow</p>
              <p className="mt-2 text-2xl font-black">Forecast-backed prep decisions</p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-white py-14 sm:py-16 lg:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mb-10 grid gap-4 lg:grid-cols-[0.8fr_1fr] lg:items-end">
            <h2 className="text-3xl font-black text-stone-950 sm:text-4xl">
              {t("landing.whatDoes", "Everything your bakery needs")}
            </h2>
            <p className="max-w-2xl text-base leading-7 text-stone-600 lg:justify-self-end">
              {t(
                "landing.featureIntro",
                "Everything your bakery team needs to plan confidently, reduce waste, and optimize operations in one calm, intuitive interface."
              )}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-6">
            <FeatureImageCard
              className="min-h-[320px] md:col-span-4"
              image="/landing/demand-forecast.svg"
              alt="Fresh baked goods"
              icon={<TrendingUp className="h-8 w-8 text-brand-amber" />}
              title={t("landing.feature.forecast.title", "Smart Demand Forecasting")}
              description={t(
                "landing.feature.forecast.description",
                "AI-powered predictions based on historical sales, weather, and seasonal patterns to guide your daily bake quantities."
              )}
            />

            <div className="group relative flex min-h-[320px] flex-col overflow-hidden rounded-lg border border-stone-200 bg-stone-50 p-6 shadow-sm transition-colors hover:bg-brand-amber-light md:col-span-2">
              <AlertTriangle className="mb-4 h-8 w-8 text-brand-amber-dark" />
              <h3 className="mb-2 text-xl font-bold text-stone-900">
                {t("landing.feature.risk.title", "Reduce Waste & Prevent Stockouts")}
              </h3>
              <p className="mb-6 flex-grow text-sm leading-6 text-stone-600">
                {t(
                  "landing.feature.risk.description",
                  "Real-time alerts for overstocked items and potential stockouts, helping you minimize waste and lost sales."
                )}
              </p>
              <div className="relative h-28 w-full overflow-hidden rounded-lg border border-stone-100 bg-white shadow-sm transition-colors group-hover:border-brand-amber/30">
                <div className="absolute left-2 top-2 z-10 flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-xs font-semibold text-red-600">
                  <AlertTriangle className="h-3 w-3" />
                  Overstocked
                </div>
                <Image
                  src="/landing/waste-risk.svg"
                  alt="Pastries"
                  fill
                  className="object-cover"
                  {...imageProps}
                />
              </div>
            </div>

            <div className="relative flex min-h-[260px] flex-col overflow-hidden rounded-lg bg-stone-900 p-6 text-white shadow-lg md:col-span-2">
              <Bot className="relative z-10 mb-4 h-8 w-8 text-brand-amber" />
              <h3 className="relative z-10 mb-2 text-xl font-bold text-white">
                {t("landing.feature.copilot.title", "AI Copilot Assistant")}
              </h3>
              <p className="relative z-10 text-sm leading-6 text-stone-300">
                {t(
                  "landing.feature.copilot.description",
                  "Multilingual chat assistant that answers questions about forecasts, inventory, and provides planning recommendations."
                )}
              </p>
            </div>

            <FeatureImageCard
              className="min-h-[260px] md:col-span-4"
              image="https://images.unsplash.com/photo-1549931319-a545dcf3bc73?w=900&q=80"
              alt="Artisan bread"
              icon={<Truck className="h-8 w-8 text-brand-amber" />}
              title={t("landing.feature.replenishment.title", "Optimized Replenishment")}
              description={t(
                "landing.feature.replenishment.description",
                "Automated suggestions for ingredient orders and product transfers between locations based on predicted demand."
              )}
            />
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden py-20 sm:py-24">
        <div className="absolute inset-0 bg-stone-900">
          <Image
            src="https://images.unsplash.com/photo-1556217477-d325251ece38?w=1600&q=80"
            alt="Cafe background"
            fill
            className="object-cover opacity-30 mix-blend-overlay"
            {...imageProps}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-stone-900 via-transparent to-stone-900/80" />
        </div>
        <div className="relative z-10 mx-auto max-w-4xl px-4 text-center text-white sm:px-6 lg:px-8">
          <h2 className="mb-6 text-3xl font-black drop-shadow-lg sm:text-4xl">
            {t("landing.ctaHeading", "Ready to transform your bakery operations?")}
          </h2>
          <p className="mx-auto mb-10 max-w-2xl text-lg font-medium leading-8 text-stone-200 drop-shadow sm:text-xl">
            {t(
              "landing.ctaBody",
              "Join bakery teams that are using Predictory to make smarter decisions and reduce waste by up to 30%."
            )}
          </p>
          <Link
            href="/data-upload"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-amber px-8 py-4 text-lg font-bold text-white shadow-2xl shadow-brand-amber/30 transition hover:bg-brand-amber-dark active:scale-[0.99]"
          >
            {t("landing.ctaSecondary", "Start Planning Today")}
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      <footer className="relative z-10 border-t border-stone-900 bg-stone-950 py-10 text-center text-stone-400">
        <div className="mb-4 flex items-center justify-center gap-2 opacity-70">
          <Sparkles className="h-4 w-4 text-brand-amber" />
          <span className="text-xs font-bold uppercase tracking-widest text-stone-300">Predictory</span>
        </div>
        <p className="text-sm">{t("landing.footer", "© 2026 Predictory. Designed for bakery teams. Built with care.")}</p>
      </footer>
    </div>
  );
}

function FeatureImageCard({
  image,
  alt,
  icon,
  title,
  description,
  className,
}: {
  image: string;
  alt: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div className={`group relative overflow-hidden rounded-lg shadow-lg ${className ?? ""}`}>
      <Image
        src={image}
        alt={alt}
        fill
        className="object-cover transition-transform duration-700 group-hover:scale-105"
        {...imageProps}
      />
      <div className="absolute inset-0 flex flex-col justify-end bg-gradient-to-t from-stone-900/90 via-stone-900/40 to-transparent p-6 sm:p-8">
        <div className="mb-3">{icon}</div>
        <h3 className="mb-2 text-2xl font-bold text-white">{title}</h3>
        <p className="max-w-md text-sm leading-6 text-stone-200 sm:text-base">{description}</p>
      </div>
    </div>
  );
}
