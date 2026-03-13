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

const MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

const CURRENT_MONTH_INDEX = new Date().getMonth();

// Pseudo-random number generator for stable mock data
function pseudoRandom(seed: number) {
    const x = Math.sin(seed++) * 10000;
    return x - Math.floor(x);
}

function YearlyOutletChart({ outlets }: { outlets: Outlet[] }) {
    const chartData = useMemo(() => {
        return MONTHS.map((month, index) => {
            const item: any = { month };
            outlets.forEach((o, i) => {
                // Deterministic base value
                const base = 5000 + (o.id * 1000) + (i * 500);
                // Trend
                const trend = (index - 5) * 200;
                // Seasonality
                const seasonality = Math.sin(index * Math.PI / 6) * 300;
                // Noise
                const noise = (pseudoRandom(o.id * 100 + index) * 400) - 200;

                const val = Math.max(0, Math.round(base + trend + seasonality + noise));

                if (index <= CURRENT_MONTH_INDEX) {
                    item[`${o.name}_past`] = val;
                }
                if (index >= CURRENT_MONTH_INDEX) {
                    if (index === CURRENT_MONTH_INDEX) {
                        // Guarantee exact match at the split point to connect the lines
                        item[`${o.name}_future`] = item[`${o.name}_past`];
                    } else {
                        item[`${o.name}_future`] = val;
                    }
                }
            });
            return item;
        });
    }, [outlets]);

    return (
        <div className="flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm relative">
            <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
                <Store className="h-4 w-4 text-emerald-500" />
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-neutral-800">1-Year Outlet Sales Trend</h3>
                    <p className="text-xs text-neutral-400">Previous sales matched with predictive forecasting</p>
                </div>
            </div>
            <div className="p-5 w-full h-[320px] min-h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} width={40} />
                        <Tooltip
                            contentStyle={{ borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)", fontSize: 12 }}
                            formatter={(value, name: string) => [
                                `${value} units`,
                                name.replace("_past", " (Actual)").replace("_future", " (Predicted)")
                            ]}
                        />
                        <ReferenceLine x={MONTHS[CURRENT_MONTH_INDEX]} stroke="#9CA3AF" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Today', fill: '#9CA3AF', fontSize: 11 }} />
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

function YearlyProductChart({ skus, outlets }: { skus: SKU[], outlets: Outlet[] }) {
    const [selectedOutletId, setSelectedOutletId] = useState<string>("all");

    const chartData = useMemo(() => {
        return MONTHS.map((month, index) => {
            const item: any = { month };
            skus.forEach((sku, i) => {
                // Deterministic base based on SKU and outlet selection
                const outletMod = selectedOutletId === "all" ? 10 : Number(selectedOutletId);
                const base = 800 + (sku.id * 50) + (i * 100) * (selectedOutletId === "all" ? 2 : 1);
                const trend = (index - 5) * 30;
                const seasonality = Math.sin(index * Math.PI / 6) * 100;
                const noise = (pseudoRandom(sku.id * outletMod + index) * 100) - 50;

                const val = Math.max(0, Math.round(base + trend + seasonality + noise));

                if (index <= CURRENT_MONTH_INDEX) {
                    item[`${sku.name}_past`] = val;
                }
                if (index >= CURRENT_MONTH_INDEX) {
                    if (index === CURRENT_MONTH_INDEX) {
                        item[`${sku.name}_future`] = item[`${sku.name}_past`];
                    } else {
                        item[`${sku.name}_future`] = val;
                    }
                }
            });
            return item;
        });
    }, [skus, selectedOutletId]);

    return (
        <div className="flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm relative">
            <div className="flex items-center gap-3 border-b border-neutral-100 px-5 py-4">
                <ShoppingBag className="h-4 w-4 text-amber-500" />
                <div className="flex-1">
                    <h3 className="text-sm font-semibold text-neutral-800">1-Year Product Sales Trend</h3>
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
                        <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#6B7280" }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fontSize: 11, fill: "#9CA3AF" }} axisLine={false} tickLine={false} width={40} />
                        <Tooltip
                            contentStyle={{ borderRadius: "10px", border: "1px solid #E5E7EB", boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.08)", fontSize: 12 }}
                            formatter={(value, name: string) => [
                                `${value} units`,
                                name.replace("_past", " (Actual)").replace("_future", " (Predicted)")
                            ]}
                        />
                        <ReferenceLine x={MONTHS[CURRENT_MONTH_INDEX]} stroke="#9CA3AF" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: 'Today', fill: '#9CA3AF', fontSize: 11 }} />
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
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <YearlyOutletChart outlets={outlets} />
            <YearlyProductChart skus={skus} outlets={outlets} />
        </div>
    );
}
