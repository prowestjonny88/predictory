"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/utils";
import Header from "@/components/Header";
import AlertCard from "@/components/AlertCard";
import type { WasteAlert, StockoutAlert } from "@/types";

type Tab = "waste" | "stockout";

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
  const error = tab === "waste" ? wasteError : stockoutError;

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

      <main className="p-6 space-y-4">
        {/* Tab switcher */}
        <div className="flex gap-2">
          <button
            onClick={() => setTab("waste")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "waste"
                ? "bg-amber-500 text-white"
                : "bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
            }`}
          >
            Waste Alerts{" "}
            {!wasteLoading && (
              <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-xs">
                {wasteAlerts?.length ?? 0}
              </span>
            )}
          </button>
          <button
            onClick={() => setTab("stockout")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === "stockout"
                ? "bg-red-600 text-white"
                : "bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50"
            }`}
          >
            Stockout Alerts{" "}
            {!stockoutLoading && (
              <span className="ml-1.5 rounded-full bg-white/20 px-1.5 text-xs">
                {stockoutAlerts?.length ?? 0}
              </span>
            )}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
            {error instanceof Error ? error.message : "Failed to load alerts"}
          </div>
        )}

        {/* Alert list */}
        <div className="space-y-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-16 bg-neutral-100 animate-pulse rounded-lg" />
            ))
          ) : tab === "waste" ? (
            (wasteAlerts?.length ?? 0) === 0 ? (
              <p className="text-sm text-neutral-400 py-8 text-center">
                No waste alerts for {date}.
              </p>
            ) : (
              wasteAlerts!.map((a, i) => (
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
                      ? `Days below threshold: ${a.days_below_threshold}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || undefined}
                >
                  {a.triggers && a.triggers.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
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
          ) : (stockoutAlerts?.length ?? 0) === 0 ? (
            <p className="text-sm text-neutral-400 py-8 text-center">
              No stockout alerts for {date}.
            </p>
          ) : (
            stockoutAlerts!.map((a, i) => (
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
                ]
                  .filter(Boolean)
                  .join(" · ") || undefined}
              />
            ))
          )}
        </div>
      </main>
    </div>
  );
}
