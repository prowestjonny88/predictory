"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO, cn } from "@/lib/utils";
import Header from "@/components/Header";
import AlertCard from "@/components/AlertCard";
import { Flame, ShoppingCart } from "lucide-react";
import type { WasteAlert, StockoutAlert, RiskLevel } from "@/types";

type Tab = "waste" | "stockout";

const RISK_ORDER: Record<RiskLevel, number> = {
  critical: 0, high: 1, medium: 2, low: 3,
};

export default function RiskCenterPage() {
  const [date, setDate] = useState(todayISO);
  const [tab, setTab] = useState<Tab>("waste");

  const {
    data: wasteAlerts,
    isLoading: wasteLoading,
    error: wasteError,
  } = useQuery<WasteAlert[]>({
    queryKey: ["wasteAlerts", date],
    queryFn: () => api.wasteAlerts(date),
  });

  const {
    data: stockoutAlerts,
    isLoading: stockoutLoading,
    error: stockoutError,
  } = useQuery<StockoutAlert[]>({
    queryKey: ["stockoutAlerts", date],
    queryFn: () => api.stockoutAlerts(date),
  });

  const loading = tab === "waste" ? wasteLoading : stockoutLoading;
  const error   = tab === "waste" ? wasteError   : stockoutError;

  const sortedWaste = [...(wasteAlerts ?? [])].sort(
    (a, b) => RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level]
  );
  const sortedStockout = [...(stockoutAlerts ?? [])].sort(
    (a, b) => RISK_ORDER[a.risk_level] - RISK_ORDER[b.risk_level]
  );

  const criticalWaste    = wasteAlerts?.filter((a) => a.risk_level === "critical").length ?? 0;
  const criticalStockout = stockoutAlerts?.filter((a) => a.risk_level === "critical").length ?? 0;

  return (
    <div className="min-h-screen">
      <Header title="Risk Centre" date={date}>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-md border border-neutral-300 px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
        />
      </Header>

      <main className="p-6 space-y-5">
        {/* Summary counts */}
        {(!wasteLoading || !stockoutLoading) && (
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={() => setTab("waste")}
              className={cn(
                "rounded-xl border p-4 text-left transition-all",
                tab === "waste"
                  ? "bg-amber-50 border-amber-300 ring-1 ring-amber-300"
                  : "bg-white border-neutral-200 hover:border-amber-200"
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <Flame className={cn("h-4 w-4", tab === "waste" ? "text-amber-500" : "text-neutral-400")} />
                <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Waste Alerts</span>
              </div>
              <p className="text-3xl font-bold text-neutral-900">{wasteAlerts?.length ?? 0}</p>
              {criticalWaste > 0 && (
                <p className="text-xs text-red-600 font-medium mt-1">{criticalWaste} critical</p>
              )}
            </button>
            <button
              onClick={() => setTab("stockout")}
              className={cn(
                "rounded-xl border p-4 text-left transition-all",
                tab === "stockout"
                  ? "bg-red-50 border-red-300 ring-1 ring-red-300"
                  : "bg-white border-neutral-200 hover:border-red-200"
              )}
            >
              <div className="flex items-center gap-2 mb-2">
                <ShoppingCart className={cn("h-4 w-4", tab === "stockout" ? "text-red-500" : "text-neutral-400")} />
                <span className="text-xs font-semibold uppercase tracking-wide text-neutral-500">Stockout Alerts</span>
              </div>
              <p className="text-3xl font-bold text-neutral-900">{stockoutAlerts?.length ?? 0}</p>
              {criticalStockout > 0 && (
                <p className="text-xs text-red-600 font-medium mt-1">{criticalStockout} critical</p>
              )}
            </button>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load alerts"}
          </div>
        )}

        {/* Alert list */}
        <section>
          <h2 className="text-xs font-semibold text-neutral-500 uppercase tracking-wide mb-3">
            {tab === "waste" ? "Waste" : "Stockout"} Alerts
            {!loading && (
              <span className="ml-2 normal-case font-normal text-neutral-400">
                — sorted by risk level
              </span>
            )}
          </h2>
          <div className="space-y-2">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="h-16 bg-neutral-100 animate-pulse rounded-lg" />
              ))
            ) : tab === "waste" ? (
              sortedWaste.length === 0 ? (
                <div className="rounded-xl bg-white border border-neutral-200 px-5 py-10 text-center text-sm text-neutral-400">
                  No waste alerts for {date}.
                </div>
              ) : (
                sortedWaste.map((a, i) => (
                  <AlertCard
                    key={i}
                    riskLevel={a.risk_level}
                    title={a.sku_name ?? `SKU ${a.sku_id}`}
                    subtitle={a.reason}
                    meta={[
                      a.outlet_name ? `Outlet: ${a.outlet_name}` : null,
                      a.waste_rate_pct != null
                        ? `Waste rate: ${a.waste_rate_pct.toFixed(1)}%`
                        : null,
                      a.days_below_threshold != null
                        ? `${a.days_below_threshold}d below threshold`
                        : null,
                    ].filter(Boolean).join(" · ") || undefined}
                  >
                    {a.triggers && a.triggers.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {a.triggers.map((t, j) => (
                          <span
                            key={j}
                            className="rounded bg-neutral-100 px-2 py-0.5 text-xs text-neutral-600"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </AlertCard>
                ))
              )
            ) : sortedStockout.length === 0 ? (
              <div className="rounded-xl bg-white border border-neutral-200 px-5 py-10 text-center text-sm text-neutral-400">
                No stockout alerts for {date}.
              </div>
            ) : (
              sortedStockout.map((a, i) => (
                <AlertCard
                  key={i}
                  riskLevel={a.risk_level}
                  title={a.sku_name ?? `SKU ${a.sku_id}`}
                  subtitle={a.reason ?? a.message}
                  meta={[
                    a.outlet_name ? `Outlet: ${a.outlet_name}` : null,
                    a.coverage_pct != null
                      ? `Stock coverage: ${a.coverage_pct.toFixed(1)}%`
                      : null,
                  ].filter(Boolean).join(" · ") || undefined}
                />
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
