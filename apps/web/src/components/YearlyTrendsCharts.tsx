"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
    CartesianGrid,
    Legend,
    Line,
    LineChart,
    ReferenceLine,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { Store, ShoppingBag } from "lucide-react";

import { api } from "@/lib/api";
import type { Outlet, SKU } from "@/types";

type TrendViewMode = "yearly" | "monthly";

const COLORS = [
    "#F59E0B", // amber-500
    "#3B82F6", // blue-500
    "#10B981", // emerald-500
    "#EF4444", // red-500
    "#8B5CF6", // violet-500
    "#EC4899", // pink-500
    "#06B6D4", // cyan-500
    "#F97316", // orange-500
];

const YEAR_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

const MONTHLY_DAYS = Array.from({ length: 30 }, (_, index) => String(index + 1));

// Approximate Malaysia festive uplift profile by month.
// Stronger periods: CNY (Feb), Hari Raya window (Apr/May), Deepavali (Oct/Nov), year-end (Dec).
const HOLIDAY_BOOST_BY_MONTH = [
    0.03, 0.15, 0.04, 0.18, 0.14, 0.03,
    0.02, 0.03, 0.04, 0.10, 0.12, 0.16,
];

function getHolidayBoost(index: number, sensitivity = 1) {
    const prev = HOLIDAY_BOOST_BY_MONTH[Math.max(0, index - 1)];
    const current = HOLIDAY_BOOST_BY_MONTH[index];
    const next = HOLIDAY_BOOST_BY_MONTH[Math.min(HOLIDAY_BOOST_BY_MONTH.length - 1, index + 1)];

    // Smoothed uplift to avoid unnatural one-month spikes.
    return (prev * 0.2 + current * 0.6 + next * 0.2) * sensitivity;
}

function getMonthlyEventBoost(index: number, sensitivity = 1) {
    const festiveDays = new Set([1, 8, 14, 21, 27]);
    const isWeekendLike = index % 7 === 5 || index % 7 === 6;
    const nearFestive = festiveDays.has(index - 1) || festiveDays.has(index + 1);

    let boost = 0;
    if (festiveDays.has(index)) boost += 0.22;
    if (nearFestive) boost += 0.08;
    if (isWeekendLike) boost += 0.06;

    return boost * sensitivity;
}

function getLabelsForMode(mode: TrendViewMode) {
    return mode === "yearly" ? YEAR_MONTHS : MONTHLY_DAYS;
}

function getCurrentIndexForMode(mode: TrendViewMode) {
    if (mode === "yearly") {
        return new Date().getMonth();
    }

    return Math.min(new Date().getDate() - 1, MONTHLY_DAYS.length - 1);
}

// Pseudo-random number generator for stable mock data
function pseudoRandom(seed: number) {
    const x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
}

function YearlyOutletChart({ outlets, mode }: { outlets: Outlet[]; mode: TrendViewMode }) {
    const labels = getLabelsForMode(mode);
    const currentIndex = getCurrentIndexForMode(mode);

    const chartData = useMemo(() => {
        return labels.map((label, index) => {
            const item: any = { label };
            outlets.forEach((o, i) => {
                // Deterministic base value
                const base =
                    mode === "yearly"
                        ? 5000 + (o.id * 1000) + (i * 500)
                        : 900 + (o.id * 140) + (i * 90);
                // Trend
                const trend =
                    mode === "yearly"
                        ? (index - 5) * 200
                        : (index - Math.floor(labels.length / 2)) * 9;
                // Seasonality
                const seasonality =
                    mode === "yearly"
                        ? Math.sin(index * Math.PI / 6) * 300
                        : Math.sin(index * Math.PI / 5) * 45;
                // Festive/event uplift by period
                const uplift =
                    mode === "yearly"
                        ? base * getHolidayBoost(index, 0.95 + (i * 0.08))
                        : base * getMonthlyEventBoost(index, 0.8 + (i * 0.06));
                // Noise
                const noise = (pseudoRandom(o.id * 100 + index) * 400) - 200;

                const val = Math.max(0, Math.round(base + trend + seasonality + uplift + noise));

                if (index <= currentIndex) {
                    item[`${o.name}_past`] = val;
                }
                if (index >= currentIndex) {
                    if (index === currentIndex) {
                        // Guarantee exact match at the split point to connect the lines
                        item[`${o.name}_future`] = item[`${o.name}_past`];
                    } else {
                        item[`${o.name}_future`] = val;
                    }
                }
            });
            return item;
        });
    }, [currentIndex, labels, mode, outlets]);

    return (
        <div className="flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm relative">
            <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
                <Store className="h-4 w-4 text-emerald-500" />
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-neutral-800">
                        {mode === "yearly" ? "1-Year Outlet Sales Trend" : "1-Month Outlet Sales Trend"}
                    </h3>
                    <p className="text-xs text-neutral-400">Previous sales matched with predictive forecasting</p>
                </div>
            </div>
            <div className="p-5 w-full h-[320px] min-h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} width={40} />
                        <Tooltip
                            contentStyle={{ borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)", fontSize: 12 }}
                            formatter={(value, name) => [
                                `${value} units`,
                                String(name).replace("_past", " (Actual)").replace("_future", " (Predicted)")
                            ]}
                        />
                        <ReferenceLine x={labels[currentIndex]} stroke="#9CA3AF" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Today', fill: '#9CA3AF', fontSize: 11 }} />
                        <Legend
                            wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
                            iconType="circle"
                            formatter={(value) => {
                                // Only show legend for past lines to avoid duplicate entries
                                if (value.endsWith('_future')) return null;
                                return value.replace('_past', '');
                            }}
                        />

                        {outlets.map((o, i) => (
                            <Line
                                key={`${o.id}-past`}
                                type="monotone"
                                dataKey={`${o.name}_past`}
                                name={`${o.name}_past`}
                                stroke={COLORS[i % COLORS.length]}
                                strokeWidth={2}
                                dot={{ r: 3 }}
                                activeDot={{ r: 5 }}
                            />
                        ))}
                        {outlets.map((o, i) => (
                            <Line
                                key={`${o.id}-future`}
                                type="monotone"
                                dataKey={`${o.name}_future`}
                                name={`${o.name}_future`}
                                stroke={COLORS[i % COLORS.length]}
                                strokeWidth={2}
                                strokeDasharray="5 5"
                                dot={false}
                                activeDot={{ r: 4 }}
                                legendType="none"
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

function YearlyProductChart({ skus, outlets, mode }: { skus: SKU[], outlets: Outlet[]; mode: TrendViewMode }) {
    const [selectedOutletId, setSelectedOutletId] = useState<string>("all");
    const labels = getLabelsForMode(mode);
    const currentIndex = getCurrentIndexForMode(mode);

    const chartData = useMemo(() => {
        return labels.map((label, index) => {
            const item: any = { label };
            skus.forEach((sku, i) => {
                // Deterministic base based on SKU and outlet selection
                const outletMod = selectedOutletId === "all" ? 10 : Number(selectedOutletId);
                const base =
                    mode === "yearly"
                        ? 800 + (sku.id * 50) + (i * 100) * (selectedOutletId === "all" ? 2 : 1)
                        : 180 + (sku.id * 12) + (i * 28) * (selectedOutletId === "all" ? 2 : 1);
                const trend =
                    mode === "yearly"
                        ? (index - 5) * 30
                        : (index - Math.floor(labels.length / 2)) * 2.2;
                const seasonality =
                    mode === "yearly"
                        ? Math.sin(index * Math.PI / 6) * 100
                        : Math.sin(index * Math.PI / 5) * 24;
                // Product-level festive response (some items react more strongly than others)
                const skuSensitivity = 0.9 + ((i % 4) * 0.18);
                const uplift =
                    mode === "yearly"
                        ? base * getHolidayBoost(index, skuSensitivity)
                        : base * getMonthlyEventBoost(index, skuSensitivity);
                const noise = (pseudoRandom(sku.id * outletMod + index) * 100) - 50;

                const val = Math.max(0, Math.round(base + trend + seasonality + uplift + noise));

                if (index <= currentIndex) {
                    item[`${sku.name}_past`] = val;
                }
                if (index >= currentIndex) {
                    if (index === currentIndex) {
                        item[`${sku.name}_future`] = item[`${sku.name}_past`];
                    } else {
                        item[`${sku.name}_future`] = val;
                    }
                }
            });
            return item;
        });
    }, [currentIndex, labels, mode, selectedOutletId, skus]);

    return (
        <div className="flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm relative">
            <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
                <ShoppingBag className="h-4 w-4 text-amber-500" />
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-neutral-800">
                        {mode === "yearly" ? "1-Year Product Sales Trend" : "1-Month Product Sales Trend"}
                    </h3>
                    <p className="text-xs text-neutral-400">Previous sales matched with predictive forecasting</p>
                </div>
                <select
                    value={selectedOutletId}
                    onChange={(e) => setSelectedOutletId(e.target.value)}
                    className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 focus:outline-none focus:ring-2 focus:ring-amber-400 transition-colors"
                >
                    <option value="all">All Outlets</option>
                    {outlets.map((o) => (
                        <option key={o.id} value={String(o.id)}>
                            {o.name}
                        </option>
                    ))}
                </select>
            </div>
            <div className="p-5 w-full h-[320px] min-h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} width={40} />
                        <Tooltip
                            contentStyle={{ borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)", fontSize: 12 }}
                            formatter={(value, name) => [
                                `${value} units`,
                                String(name).replace("_past", " (Actual)").replace("_future", " (Predicted)")
                            ]}
                        />
                        <ReferenceLine x={labels[currentIndex]} stroke="#9CA3AF" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Today', fill: '#9CA3AF', fontSize: 11 }} />
                        <Legend
                            wrapperStyle={{ fontSize: 11, paddingTop: 10 }}
                            iconType="circle"
                            formatter={(value) => {
                                if (value.endsWith('_future')) return null;
                                return value.replace('_past', '');
                            }}
                        />

                        {skus.map((s, i) => (
                            <Line
                                key={`${s.id}-past`}
                                type="monotone"
                                dataKey={`${s.name}_past`}
                                name={`${s.name}_past`}
                                stroke={COLORS[i % COLORS.length]}
                                strokeWidth={2}
                                dot={{ r: 3 }}
                                activeDot={{ r: 5 }}
                            />
                        ))}
                        {skus.map((s, i) => (
                            <Line
                                key={`${s.id}-future`}
                                type="monotone"
                                dataKey={`${s.name}_future`}
                                name={`${s.name}_future`}
                                stroke={COLORS[i % COLORS.length]}
                                strokeWidth={2}
                                strokeDasharray="5 5"
                                dot={false}
                                activeDot={{ r: 4 }}
                                legendType="none"
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
}

export default function YearlyTrendsCharts() {
    const [mode, setMode] = useState<TrendViewMode>("yearly");

    const outletsQuery = useQuery<Outlet[]>({
        queryKey: ["outlets"],
        queryFn: api.outlets,
        staleTime: Infinity,
    });

    const skusQuery = useQuery<SKU[]>({
        queryKey: ["skus"],
        queryFn: api.skus,
        staleTime: Infinity,
    });

    const outlets = outletsQuery.data ?? [];
    const skus = skusQuery.data ?? [];

    if (outletsQuery.isLoading || skusQuery.isLoading) {
        return (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <div className="h-80 animate-pulse rounded-xl border border-neutral-200 bg-neutral-100" />
                <div className="h-80 animate-pulse rounded-xl border border-neutral-200 bg-neutral-100" />
            </div>
        );
    }

    if (outlets.length === 0 || skus.length === 0) {
        return null;
    }

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-end">
                <div className="inline-flex rounded-lg border border-neutral-200 bg-white p-1 shadow-sm">
                    <button
                        onClick={() => setMode("yearly")}
                        className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                            mode === "yearly"
                                ? "bg-amber-500 text-white"
                                : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                    >
                        Yearly
                    </button>
                    <button
                        onClick={() => setMode("monthly")}
                        className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
                            mode === "monthly"
                                ? "bg-amber-500 text-white"
                                : "text-neutral-600 hover:bg-neutral-100"
                        }`}
                    >
                        Monthly
                    </button>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <YearlyOutletChart outlets={outlets} mode={mode} />
                <YearlyProductChart skus={skus} outlets={outlets} mode={mode} />
            </div>
        </div>
    );
}
