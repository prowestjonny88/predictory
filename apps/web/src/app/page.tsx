"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle2,
  ClipboardCheck,
  FileUp,
  Gavel,
  Languages,
  PackageCheck,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Truck,
  Users,
  XCircle,
} from "lucide-react";

import { useLanguage } from "@/components/i18n/LanguageProvider";

type ScenarioKey = "school" | "rain" | "reduce" | "eggs";

const scenarios: Record<
  ScenarioKey,
  {
    label: string;
    context: string;
    response: string;
    decision: string;
  }
> = {
  school: {
    label: "School group tomorrow morning",
    context: "School group visiting KLCC Mall tomorrow morning.",
    response:
      "Agent Council suggests reviewing Butter Croissant morning prep because expected demand is close to the recommendation and stockout exposure is higher than waste exposure.",
    decision: "Keep 50 units unless the manager confirms stronger footfall.",
  },
  rain: {
    label: "Rainy morning traffic",
    context: "Rain is expected during the morning commute near KLCC Mall.",
    response:
      "Predictory highlights a quieter demand scenario and asks the manager to compare waste risk before increasing production.",
    decision: "Review the demand range before approving extra prep.",
  },
  reduce: {
    label: "Reduce croissant prep by 15%",
    context: "Manager note asks to reduce croissant prep after a slower weekday pattern.",
    response:
      "Gemini parses the note, then the Agent Council checks whether the lower candidate still protects against stockouts.",
    decision: "Apply only after human confirmation; the forecast itself is not rerun.",
  },
  eggs: {
    label: "Eggs shortage",
    context: "Egg stock is tight before the morning bake.",
    response:
      "Replenishment evidence flags ingredient pressure, so the council weighs stockout risk against feasible production.",
    decision: "Review reorder impact before approving the prep sheet.",
  },
};

const workflowSteps = [
  {
    icon: <FileUp className="h-5 w-5" />,
    title: "Import sales, stock, recipes",
    body: "Start from the POS or ERP CSV instead of manual spreadsheet chasing.",
  },
  {
    icon: <TrendingUp className="h-5 w-5" />,
    title: "Forecast demand",
    body: "Predict demand by outlet, SKU, and daypart with uncertainty included.",
  },
  {
    icon: <ClipboardCheck className="h-5 w-5" />,
    title: "Recommend prep",
    body: "Turn forecast evidence into tomorrow's bake quantities.",
  },
  {
    icon: <Truck className="h-5 w-5" />,
    title: "Check ingredients",
    body: "Convert prep plans into recipe BOM needs and shortage alerts.",
  },
  {
    icon: <Brain className="h-5 w-5" />,
    title: "Explain tradeoffs",
    body: "Agent Council compares waste, stockout, replenishment, and manager context.",
  },
  {
    icon: <CheckCircle2 className="h-5 w-5" />,
    title: "Manager approves",
    body: "The final plan is approved by a human and recorded for audit.",
  },
];

export default function RootPage() {
  const { t } = useLanguage();
  const [activeScenario, setActiveScenario] = useState<ScenarioKey>("school");
  const [focusedSection, setFocusedSection] = useState<string | null>(null);
  const [navHidden, setNavHidden] = useState(false);
  const focusTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastScrollTopRef = useRef(0);
  const scrollTickingRef = useRef(false);
  const scenario = scenarios[activeScenario];

  useEffect(() => {
    const scrollRoot = document.getElementById("main-content");
    const getScrollTop = () => scrollRoot?.scrollTop ?? window.scrollY;

    lastScrollTopRef.current = getScrollTop();

    const handleScroll = () => {
      if (scrollTickingRef.current) {
        return;
      }

      scrollTickingRef.current = true;
      window.requestAnimationFrame(() => {
        const currentScrollTop = getScrollTop();
        const delta = currentScrollTop - lastScrollTopRef.current;

        if (currentScrollTop < 24) {
          setNavHidden(false);
        } else if (delta > 8) {
          setNavHidden(true);
        } else if (delta < -8) {
          setNavHidden(false);
        }

        lastScrollTopRef.current = currentScrollTop;
        scrollTickingRef.current = false;
      });
    };

    const target: HTMLElement | Window = scrollRoot ?? window;
    target.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      if (focusTimerRef.current) {
        clearTimeout(focusTimerRef.current);
      }
      target.removeEventListener("scroll", handleScroll);
    };
  }, []);

  function handleSectionJump(sectionId: string) {
    setNavHidden(false);
    setFocusedSection(sectionId);
    if (focusTimerRef.current) {
      clearTimeout(focusTimerRef.current);
    }
    focusTimerRef.current = setTimeout(() => setFocusedSection(null), 1200);
  }

  return (
    <div className="min-h-screen overflow-hidden bg-stone-50 text-stone-950 selection:bg-brand-amber selection:text-white">
      <LandingNav t={t} hidden={navHidden} onSectionJump={handleSectionJump} />

      <main>
        <section className="relative pt-12 sm:pt-14 lg:pt-16">
          <div className="absolute left-1/2 top-24 h-72 w-72 -translate-x-1/2 rounded-full bg-brand-amber/20 blur-3xl" />
          <div className="absolute right-0 top-40 h-96 w-96 rounded-full bg-emerald-200/25 blur-3xl" />
          <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 pb-20 sm:px-6 lg:grid-cols-[minmax(0,1fr)_520px] lg:px-8 lg:pb-24">
            <div className="relative z-10">
              <div className="landing-rise mb-6 inline-flex items-center gap-2 rounded-full border border-brand-amber/30 bg-white/80 px-4 py-2 text-sm font-bold text-brand-amber-dark shadow-sm backdrop-blur">
                <Sparkles className="h-4 w-4" />
                {t("landing.badge", "Forecast-backed daily planning for bakery MSMEs")}
              </div>

              <h1 className="landing-rise landing-rise-delay-1 max-w-4xl text-4xl font-black leading-[1.02] tracking-normal text-stone-950 sm:text-5xl lg:text-7xl">
                {t("landing.heroTitle", "Know what to bake tomorrow before waste or stockouts happen.")}
              </h1>

              <p className="landing-rise landing-rise-delay-2 mt-6 max-w-2xl text-lg leading-8 text-stone-700 sm:text-xl">
                {t(
                  "landing.heroDescription",
                  "Predictory turns sales history, inventory, recipes, and demand uncertainty into tomorrow's prep plan, ingredient reorder actions, and AI-grounded explanations."
                )}
              </p>

              <div className="landing-rise landing-rise-delay-3 mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/data-upload"
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-amber px-6 py-3 text-base font-black text-white shadow-lg shadow-brand-amber/25 transition hover:bg-brand-amber-dark active:scale-[0.99]"
                >
                  {t("landing.cta.upload", "Upload POS / ERP CSV")}
                  <ArrowRight className="h-5 w-5" />
                </Link>
                <Link
                  href="/dashboard"
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-stone-300 bg-white px-6 py-3 text-base font-bold text-stone-800 shadow-sm transition hover:border-brand-amber/40 hover:bg-brand-amber-light"
                >
                  {t("landing.cta.brief", "See operations brief")}
                </Link>
              </div>

              <div className="landing-rise landing-rise-delay-3 mt-8 grid max-w-2xl grid-cols-2 gap-3 sm:grid-cols-4">
                <TrustPill icon={<TrendingUp className="h-4 w-4" />} label={t("landing.trust.forecast", "Forecast-backed prep")} />
                <TrustPill icon={<ShieldCheck className="h-4 w-4" />} label={t("landing.trust.evidence", "Evidence-grounded AI")} />
                <TrustPill icon={<Users className="h-4 w-4" />} label={t("landing.trust.human", "Human-approved decisions")} />
                <TrustPill icon={<ClipboardCheck className="h-4 w-4" />} label={t("landing.trust.audit", "Audit trail")} />
              </div>
            </div>

            <HeroDecisionMockup t={t} />
          </div>
        </section>

        <section
          id="workflow"
          className={`relative overflow-hidden border-y border-stone-200 bg-white py-16 sm:py-20 ${
            focusedSection === "workflow" ? "landing-section-focus" : ""
          }`}
        >
          <div className="absolute inset-0" aria-hidden="true">
            <Image
              src="/landing/bakery-operations-v2.png"
              alt=""
              fill
              sizes="100vw"
              className="landing-bg-pan-slow object-cover opacity-[0.18]"
            />
          </div>
          <div className="absolute inset-0 bg-gradient-to-br from-white/95 via-white/88 to-brand-amber-light/78" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(255,255,255,0.92),rgba(255,255,255,0.48)_48%,rgba(251,191,36,0.16)_100%)]" />
          <div className="relative z-10">
            <SectionHeader
              eyebrow={t("landing.workflow.eyebrow", "Daily workflow")}
              title={t("landing.workflow.title", "From yesterday's sales to tomorrow's bake plan.")}
              body={t(
                "landing.workflow.body",
                "Predictory connects the operating data a bakery already has to the prep decisions managers approve every morning."
              )}
            />
            <div className="mx-auto mt-10 grid max-w-7xl gap-4 px-4 sm:px-6 md:grid-cols-2 lg:grid-cols-6 lg:px-8">
              {workflowSteps.map((step, index) => (
                <WorkflowStep key={step.title} index={index + 1} icon={step.icon} title={step.title} body={step.body} />
              ))}
            </div>
          </div>
        </section>

        <section id="demo" className={`bg-stone-50 py-16 sm:py-20 ${focusedSection === "demo" ? "landing-section-focus" : ""}`}>
          <div className="mx-auto grid max-w-7xl gap-8 px-4 sm:px-6 lg:grid-cols-[0.85fr_1.15fr] lg:px-8">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.22em] text-brand-amber-dark">
                {t("landing.scenario.eyebrow", "Try a decision")}
              </p>
              <h2 className="mt-3 text-3xl font-black leading-tight text-stone-950 sm:text-5xl">
                {t("landing.scenario.title", "See how one bakery decision changes the plan.")}
              </h2>
              <p className="mt-4 text-base leading-7 text-stone-600">
                {t(
                  "landing.scenario.body",
                  "These examples are static landing-page previews. In the app, explanations are grounded in backend evidence and manager approval is required before changing the plan."
                )}
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                {(Object.keys(scenarios) as ScenarioKey[]).map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setActiveScenario(key)}
                    className={`rounded-full border px-4 py-2 text-left text-sm font-bold transition ${
                      activeScenario === key
                        ? "border-brand-amber bg-brand-amber text-white shadow-lg shadow-brand-amber/20"
                        : "border-stone-200 bg-white text-stone-700 hover:border-brand-amber/50 hover:bg-brand-amber-light"
                    }`}
                  >
                    {scenarios[key].label}
                  </button>
                ))}
              </div>
            </div>

            <div key={activeScenario} className="animate-fade-in rounded-2xl border border-stone-200 bg-white p-5 shadow-xl shadow-stone-900/5 sm:p-6">
              <div className="grid gap-4 md:grid-cols-2">
                <DecisionPanel title={t("landing.scenario.context", "Manager context")} icon={<Users className="h-5 w-5" />}>
                  {scenario.context}
                </DecisionPanel>
                <DecisionPanel title={t("landing.scenario.response", "Predictory response")} icon={<Brain className="h-5 w-5" />}>
                  {scenario.response}
                </DecisionPanel>
              </div>
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-xs font-black uppercase tracking-[0.18em] text-emerald-700">
                  {t("landing.scenario.decision", "Decision")}
                </p>
                <p className="mt-2 text-base font-bold leading-7 text-stone-950">{scenario.decision}</p>
              </div>
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden bg-white py-16 sm:py-20">
          <div className="absolute inset-0" aria-hidden="true">
            <Image
              src="/landing/ingredient-replenishment-v2.png"
              alt=""
              fill
              sizes="100vw"
              className="landing-bg-pan-reverse object-cover opacity-[0.11]"
            />
          </div>
          <div className="absolute inset-0 bg-gradient-to-b from-white via-white/92 to-white/88" />
          <div className="relative z-10">
            <SectionHeader
              eyebrow={t("landing.features.eyebrow", "Product surfaces")}
              title={t("landing.features.title", "Built around the decisions bakery teams already make.")}
              body={t(
                "landing.features.body",
                "The app is not a generic analytics page. It moves managers through prep, replenishment, risk, explanation, and approval."
              )}
            />
            <div className="mx-auto mt-10 grid max-w-7xl gap-5 px-4 sm:px-6 lg:grid-cols-4 lg:px-8">
              <FeatureCard
                icon={<ClipboardCheck className="h-6 w-6" />}
                title={t("landing.feature.daily.title", "Daily Planning Workspace")}
                body={t(
                  "landing.feature.daily.body",
                  "Review forecast-backed prep recommendations by outlet, SKU, and daypart before production starts."
                )}
                href="/daily-planning"
                cta={t("landing.feature.daily.cta", "Open Daily Planning")}
              >
                <MiniDemandCard />
              </FeatureCard>
              <FeatureCard
                icon={<Gavel className="h-6 w-6" />}
                title={t("landing.feature.council.title", "Agent Council")}
                body={t(
                  "landing.feature.council.body",
                  "Specialist agents compare waste, stockout, replenishment, and manager context before the Judge selects a valid backend candidate."
                )}
              >
                <MiniCouncil />
              </FeatureCard>
              <FeatureCard
                icon={<PackageCheck className="h-6 w-6" />}
                title={t("landing.feature.replenishment.title", "Ingredient Replenishment")}
                body={t(
                  "landing.feature.replenishment.body",
                  "Translate prep plans into ingredient needs using recipe BOMs, stock-on-hand, shortage quantity, urgency, and driving SKUs."
                )}
                href="/replenishment"
                cta={t("landing.feature.replenishment.cta", "View Replenishment")}
              >
                <MiniReplenishment />
              </FeatureCard>
              <FeatureCard
                icon={<AlertTriangle className="h-6 w-6" />}
                title={t("landing.feature.risk.title", "Waste & Stockout Risk Centre")}
                body={t(
                  "landing.feature.risk.body",
                  "Spot the highest-risk prep lines before they become leftovers or missed sales."
                )}
                href="/risk-center"
                cta={t("landing.feature.risk.cta", "Open Risk Centre")}
              >
                <MiniRisk />
              </FeatureCard>
            </div>
          </div>
        </section>

        <section
          id="agent-council"
          className={`relative overflow-hidden bg-stone-950 py-16 text-white sm:py-20 ${focusedSection === "agent-council" ? "landing-section-focus" : ""}`}
        >
          <div className="absolute -left-24 top-0 h-72 w-72 rounded-full bg-brand-amber/20 blur-3xl" />
          <div className="absolute -right-24 bottom-0 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />
          <div className="relative mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[0.85fr_1.15fr] lg:px-8">
            <div>
              <p className="text-sm font-black uppercase tracking-[0.22em] text-brand-amber-light">
                {t("landing.guardrail.eyebrow", "AI guardrails")}
              </p>
              <h2 className="mt-3 text-3xl font-black leading-tight sm:text-5xl">
                {t("landing.guardrail.title", "AI explains the decision. It does not invent the numbers.")}
              </h2>
              <p className="mt-5 text-base leading-8 text-stone-300">
                {t(
                  "landing.guardrail.body",
                  "Forecasts, prep quantities, reorder quantities, and exposure values are generated by backend models and deterministic planning logic. Gemini explains the evidence and the Agent Council compares valid candidate decisions."
                )}
              </p>
              <div className="mt-6 grid grid-cols-2 gap-3">
                {["No invented quantities", "Backend evidence only", "Human-in-the-loop", "Audit-ready decisions"].map((label) => (
                  <div key={label} className="rounded-xl border border-white/10 bg-white/5 p-3 text-sm font-bold text-stone-100">
                    {label}
                  </div>
                ))}
              </div>
            </div>
            <AgentProtocol />
          </div>
        </section>

        <section id="why" className={`bg-stone-50 py-16 sm:py-20 ${focusedSection === "why" ? "landing-section-focus" : ""}`}>
          <SectionHeader
            eyebrow={t("landing.compare.eyebrow", "Why Predictory")}
            title={t("landing.compare.title", "Not another dashboard. A daily decision workflow.")}
            body={t(
              "landing.compare.body",
              "Predictory is designed for managers who need to approve tomorrow's bake plan, not just read yesterday's charts."
            )}
          />
          <div className="mx-auto mt-10 grid max-w-6xl gap-5 px-4 sm:px-6 lg:grid-cols-2 lg:px-8">
            <ComparisonCard
              tone="muted"
              title={t("landing.compare.typical", "Typical dashboard")}
              items={[
                "Shows yesterday's metrics",
                "Leaves managers to calculate prep manually",
                "Flags problems without next steps",
                "Uses generic AI chat with unclear evidence",
              ]}
            />
            <ComparisonCard
              tone="positive"
              title={t("landing.compare.predictory", "Predictory")}
              items={[
                "Recommends tomorrow's prep",
                "Balances waste and stockout exposure",
                "Turns recipes into ingredient needs",
                "Requires manager approval before changes",
              ]}
            />
          </div>
        </section>

        <section className="bg-white py-16 sm:py-20">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="rounded-3xl border border-stone-200 bg-gradient-to-br from-white via-brand-amber-light/30 to-emerald-50 p-6 shadow-xl shadow-stone-900/5 sm:p-10">
              <div className="grid gap-8 lg:grid-cols-[1fr_0.85fr] lg:items-center">
                <div>
                  <p className="text-sm font-black uppercase tracking-[0.22em] text-brand-amber-dark">
                    {t("landing.msme.eyebrow", "MSME impact")}
                  </p>
                  <h2 className="mt-3 text-3xl font-black leading-tight text-stone-950 sm:text-5xl">
                    {t("landing.msme.title", "Built for bakery MSMEs that cannot afford enterprise planning teams.")}
                  </h2>
                  <p className="mt-5 max-w-3xl text-base leading-8 text-stone-700">
                    {t(
                      "landing.msme.body",
                      "Small bakery chains often rely on spreadsheets, memory, and last-minute judgment to decide what to bake. Predictory gives them a lightweight decision layer without needing a data science team."
                    )}
                  </p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <ImpactChip icon={<Languages className="h-5 w-5" />} label={t("landing.msme.languages", "3 languages")} />
                  <ImpactChip icon={<BarChart3 className="h-5 w-5" />} label={t("landing.msme.daypart", "Outlet x SKU x daypart planning")} />
                  <ImpactChip icon={<ClipboardCheck className="h-5 w-5" />} label={t("landing.msme.sheet", "Human-approved prep sheet")} />
                  <ImpactChip icon={<ShieldCheck className="h-5 w-5" />} label={t("landing.msme.evidence", "Evidence-grounded AI explanations")} />
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-stone-950 py-16 text-white sm:py-20">
          <div className="mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
            <h2 className="text-3xl font-black leading-tight sm:text-5xl">
              {t("landing.final.title", "Turn tomorrow's uncertainty into an approved bake plan.")}
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-8 text-stone-300">
              {t(
                "landing.final.body",
                "Start by uploading the POS or ERP CSV, then review prep, replenishment, and risk before production begins."
              )}
            </p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link
                href="/data-upload"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-brand-amber px-7 py-3 text-base font-black text-white shadow-lg shadow-brand-amber/20 transition hover:bg-brand-amber-dark"
              >
                {t("landing.final.primary", "Upload POS / ERP CSV")}
                <ArrowRight className="h-5 w-5" />
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-white/15 bg-white/10 px-7 py-3 text-base font-bold text-white transition hover:bg-white/15"
              >
                {t("landing.final.secondary", "View Operations Brief")}
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-stone-200 bg-white py-8 text-center text-stone-500">
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="h-4 w-4 text-brand-amber" />
          <span className="text-sm font-black uppercase tracking-widest text-stone-800">Predictory</span>
        </div>
        <p className="mt-3 text-sm">
          {t("landing.footer", "Decision layer between yesterday's sales and tomorrow's bake. Built for BorNEO HackWknd 2026.")}
        </p>
      </footer>
    </div>
  );
}

function LandingNav({
  t,
  hidden,
  onSectionJump,
}: {
  t: (key: string, fallback: string) => string;
  hidden: boolean;
  onSectionJump: (sectionId: string) => void;
}) {
  return (
    <nav
      className={`sticky top-0 z-50 w-full border-b border-stone-200 bg-white/85 shadow-sm shadow-stone-900/5 backdrop-blur-md transition-transform duration-300 ease-out ${
        hidden ? "-translate-y-full" : "translate-y-0"
      }`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-amber text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </div>
          <span className="text-xl font-black tracking-tight text-stone-900">Predictory</span>
        </Link>
        <div className="hidden items-center gap-7 text-sm font-bold text-stone-600 md:flex">
          <a href="#workflow" onClick={() => onSectionJump("workflow")} className="transition hover:text-stone-950">
            {t("landing.nav.workflow", "Workflow")}
          </a>
          <a href="#agent-council" onClick={() => onSectionJump("agent-council")} className="transition hover:text-stone-950">
            {t("landing.nav.agentCouncil", "Agent Council")}
          </a>
          <a href="#why" onClick={() => onSectionJump("why")} className="transition hover:text-stone-950">
            {t("landing.nav.why", "Why Predictory")}
          </a>
          <a href="#demo" onClick={() => onSectionJump("demo")} className="transition hover:text-stone-950">
            {t("landing.nav.demo", "Demo")}
          </a>
        </div>
        <Link
          href="/data-upload"
          className="hidden rounded-md bg-stone-950 px-4 py-2 text-sm font-black text-white transition hover:bg-brand-amber md:inline-flex"
        >
          {t("landing.nav.cta", "Upload CSV")}
        </Link>
      </div>
    </nav>
  );
}

function HeroDecisionMockup({ t }: { t: (key: string, fallback: string) => string }) {
  return (
    <div className="landing-rise landing-rise-delay-2 relative z-10">
      <div className="absolute -inset-5 rounded-[2rem] bg-brand-amber/20 blur-2xl" />
      <div className="landing-float relative rounded-[1.75rem] border border-stone-200 bg-white p-4 shadow-2xl shadow-stone-900/15">
        <div className="mb-4 flex items-center gap-2 border-b border-stone-100 pb-3">
          <span className="h-3 w-3 rounded-full bg-red-400" />
          <span className="h-3 w-3 rounded-full bg-amber-400" />
          <span className="h-3 w-3 rounded-full bg-emerald-400" />
          <span className="ml-auto rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">
            {t("landing.mockup.badge", "Human approval required")}
          </span>
        </div>
        <div className="rounded-2xl border border-stone-200 bg-stone-50 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-brand-amber-dark">
                {t("landing.mockup.title", "Tomorrow's top decision")}
              </p>
              <h3 className="mt-2 text-2xl font-black text-stone-950">
                {t("landing.mockup.prepare", "Prepare 50 units")}
              </h3>
              <p className="mt-1 text-sm font-semibold text-stone-500">KLCC Mall / Butter Croissant / Morning</p>
            </div>
            <div className="rounded-xl bg-white px-3 py-2 text-right shadow-sm">
              <p className="text-xs font-bold text-stone-500">{t("landing.mockup.source", "Source")}</p>
              <p className="text-sm font-black text-stone-950">{t("landing.mockup.sourceValue", "Backend evidence")}</p>
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-2 flex justify-between text-xs font-bold text-stone-500">
              <span>{t("landing.mockup.low", "Low 8")}</span>
              <span>{t("landing.mockup.expected", "Expected 47")}</span>
              <span>{t("landing.mockup.high", "High 80")}</span>
            </div>
            <div className="relative h-4 rounded-full bg-stone-200">
              <div className="landing-range-fill absolute left-[10%] right-[12%] top-1 h-2 rounded-full bg-gradient-to-r from-emerald-400 via-brand-amber to-red-400" />
              <div className="absolute left-[58%] top-[-5px] h-7 w-1 rounded-full bg-stone-950" />
              <div className="landing-marker-pop absolute left-[62%] top-[-3px] h-6 w-6 rounded-full border-4 border-white bg-brand-amber shadow-lg" />
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2">
            <MetricCard label={t("landing.mockup.waste", "Waste exposure")} value="RM 2.98" tone="orange" />
            <MetricCard label={t("landing.mockup.stockout", "Stockout exposure")} value="RM 11.27" tone="red" />
          </div>

          <div className="mt-5 rounded-xl border border-brand-amber/30 bg-brand-amber-light p-4">
            <p className="text-sm font-black text-brand-amber-dark">{t("landing.mockup.next", "Next action")}</p>
            <p className="mt-1 text-base font-bold text-stone-950">{t("landing.mockup.review", "Review with Agent Council")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function TrustPill({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="flex min-h-14 items-center gap-2 rounded-xl border border-stone-200 bg-white/85 px-3 py-2 text-sm font-bold text-stone-700 shadow-sm">
      <span className="text-brand-amber-dark">{icon}</span>
      <span>{label}</span>
    </div>
  );
}

function SectionHeader({ eyebrow, title, body }: { eyebrow: string; title: string; body: string }) {
  return (
    <div className="mx-auto max-w-3xl px-4 text-center sm:px-6 lg:px-8">
      <p className="text-sm font-black uppercase tracking-[0.22em] text-brand-amber-dark">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-black leading-tight text-stone-950 sm:text-5xl">{title}</h2>
      <p className="mt-4 text-base leading-7 text-stone-600">{body}</p>
    </div>
  );
}

function WorkflowStep({ index, icon, title, body }: { index: number; icon: ReactNode; title: string; body: string }) {
  return (
    <div className="relative rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-lg">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-amber-light text-brand-amber-dark">{icon}</div>
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-stone-950 text-xs font-black text-white">{index}</span>
      </div>
      <h3 className="text-base font-black text-stone-950">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-stone-600">{body}</p>
    </div>
  );
}

function DecisionPanel({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
      <div className="flex items-center gap-2 text-sm font-black text-stone-950">
        <span className="text-brand-amber-dark">{icon}</span>
        {title}
      </div>
      <p className="mt-3 text-sm leading-6 text-stone-700">{children}</p>
    </div>
  );
}

function FeatureCard({
  icon,
  title,
  body,
  href,
  cta,
  children,
}: {
  icon: ReactNode;
  title: string;
  body: string;
  href?: string;
  cta?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-[430px] flex-col rounded-2xl border border-stone-200 bg-white p-5 shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-stone-950 text-brand-amber">{icon}</div>
      <h3 className="text-xl font-black text-stone-950">{title}</h3>
      <p className="mt-3 flex-1 text-sm leading-6 text-stone-600">{body}</p>
      <div className="my-5">{children}</div>
      {href && cta ? (
        <Link href={href} className="inline-flex items-center gap-2 text-sm font-black text-brand-amber-dark hover:text-stone-950">
          {cta}
          <ArrowRight className="h-4 w-4" />
        </Link>
      ) : (
        <span className="text-sm font-black text-stone-400">Evidence review</span>
      )}
    </div>
  );
}

function MiniDemandCard() {
  return (
    <div className="rounded-xl border border-stone-200 bg-stone-50 p-4">
      <div className="flex items-center justify-between text-xs font-bold text-stone-500">
        <span>Demand range</span>
        <span>Morning</span>
      </div>
      <div className="mt-3 h-3 rounded-full bg-stone-200">
        <div className="h-3 w-3/4 rounded-full bg-gradient-to-r from-emerald-400 via-brand-amber to-red-400" />
      </div>
      <div className="mt-3 flex items-end justify-between">
        <span className="text-sm font-bold text-stone-600">Butter Croissant</span>
        <span className="text-2xl font-black text-stone-950">50</span>
      </div>
    </div>
  );
}

function MiniCouncil() {
  return (
    <div className="grid grid-cols-2 gap-2">
      {["Forecast", "Waste", "Stockout", "Replenishment"].map((agent) => (
        <div key={agent} className="rounded-lg border border-stone-200 bg-stone-50 p-2 text-center text-xs font-black text-stone-700">
          {agent}
        </div>
      ))}
      <div className="col-span-2 rounded-lg bg-stone-950 p-2 text-center text-xs font-black text-white">Judge Agent</div>
    </div>
  );
}

function MiniReplenishment() {
  return (
    <div className="overflow-hidden rounded-xl border border-stone-200 bg-white text-sm">
      <div className="grid grid-cols-3 bg-stone-50 px-3 py-2 text-xs font-black text-stone-500">
        <span>Ingredient</span>
        <span>Need</span>
        <span>Reorder</span>
      </div>
      <div className="grid grid-cols-3 px-3 py-3 font-bold text-stone-800">
        <span>Eggs</span>
        <span>652.5</span>
        <span className="text-brand-amber-dark">52.5</span>
      </div>
    </div>
  );
}

function MiniRisk() {
  return (
    <div className="grid gap-2">
      <div className="rounded-lg border border-red-100 bg-red-50 p-3 text-sm font-bold text-red-700">Stockout alert</div>
      <div className="rounded-lg border border-orange-100 bg-orange-50 p-3 text-sm font-bold text-orange-700">Waste hotspot</div>
    </div>
  );
}

function AgentProtocol() {
  const steps = ["LightGBM Forecast", "Prep Optimizer", "Candidate Prep Quantities", "Agent Council Debate", "Judge Recommendation", "Manager Approval", "Audit Trail"];
  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-2xl shadow-black/20">
      <div className="grid gap-3 sm:grid-cols-2">
        <ProtocolLine label="Tools calculate." />
        <ProtocolLine label="Agents argue." />
        <ProtocolLine label="Judge synthesizes." />
        <ProtocolLine label="Human approves." />
        <ProtocolLine label="Audit records." className="sm:col-span-2" />
      </div>
      <div className="mt-6 space-y-2">
        {steps.map((step, index) => (
          <div key={step} className="flex items-center gap-3 rounded-xl border border-white/10 bg-stone-900/80 p-3">
            <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-amber text-xs font-black text-white">{index + 1}</span>
            <span className="text-sm font-bold text-stone-100">{step}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ProtocolLine({ label, className }: { label: string; className?: string }) {
  return <div className={`rounded-xl bg-white/10 p-3 text-center text-sm font-black text-white ${className ?? ""}`}>{label}</div>;
}

function ComparisonCard({ title, items, tone }: { title: string; items: string[]; tone: "muted" | "positive" }) {
  const positive = tone === "positive";
  return (
    <div className={`rounded-2xl border p-6 shadow-sm ${positive ? "border-emerald-200 bg-emerald-50" : "border-stone-200 bg-white"}`}>
      <h3 className="text-2xl font-black text-stone-950">{title}</h3>
      <div className="mt-5 space-y-3">
        {items.map((item) => (
          <div key={item} className="flex gap-3 rounded-xl bg-white/80 p-3">
            {positive ? <CheckCircle2 className="mt-0.5 h-5 w-5 text-emerald-600" /> : <XCircle className="mt-0.5 h-5 w-5 text-stone-400" />}
            <span className="text-sm font-bold leading-6 text-stone-700">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ImpactChip({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/80 p-4 shadow-sm">
      <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-stone-950 text-brand-amber">{icon}</div>
      <p className="text-sm font-black leading-6 text-stone-900">{label}</p>
    </div>
  );
}

function MetricCard({ label, value, tone }: { label: string; value: string; tone: "orange" | "red" }) {
  const toneClass = tone === "red" ? "bg-red-50 text-red-700 border-red-100" : "bg-orange-50 text-orange-700 border-orange-100";
  return (
    <div className={`rounded-xl border p-3 ${toneClass}`}>
      <p className="text-xs font-bold opacity-75">{label}</p>
      <p className="mt-1 text-xl font-black">{value}</p>
    </div>
  );
}
