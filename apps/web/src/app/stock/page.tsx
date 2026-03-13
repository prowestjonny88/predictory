"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CopyIcon } from "lucide-react";

import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import type { Inventory, Outlet } from "@/types";

export default function StockPage() {
    const [outletId, setOutletId] = useState<string>("all");
    const { t } = useLanguage();

    const outletsQuery = useQuery<Outlet[]>({
        queryKey: ["outlets"],
        queryFn: api.outlets,
        staleTime: Infinity,
    });

    const inventoryQuery = useQuery<Inventory[]>({
        queryKey: ["inventory", outletId],
        queryFn: () => api.inventory(outletId),
        refetchInterval: 30000,
    });

    const outlets = outletsQuery.data ?? [];
    const inventory = inventoryQuery.data ?? [];

    const latestInventory = useMemo(() => {
        const seen = new Set<string>();
        const filtered: Inventory[] = [];
        for (const item of inventory) {
            const key = `${item.outlet_id}-${item.sku_id}`;
            if (!seen.has(key)) {
                seen.add(key);
                filtered.push(item);
            }
        }
        return filtered.sort((a, b) => a.sku_name.localeCompare(b.sku_name));
    }, [inventory]);

    return (
        <div className="min-h-screen">
            <Header title={t("nav.stock", "Current Stock")} date={new Date().toISOString().split("T")[0]}>
                <select
                    value={outletId}
                    onChange={(e) => setOutletId(e.target.value)}
                    className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                    <option value="all">{t("forecast.allOutlets", "All Outlets")}</option>
                    {outlets.map((outlet) => (
                        <option key={outlet.id} value={String(outlet.id)}>
                            {outlet.name}
                        </option>
                    ))}
                </select>
            </Header>

            <main className="max-w-6xl space-y-6 p-6 page-enter mx-auto">
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600 pl-1">
                            Outlet Inventory
                        </h2>
                    </div>

                    <div className="overflow-x-auto overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm ring-1 ring-neutral-900/5">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-neutral-200 bg-neutral-50/80 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">
                                    <th className="px-5 py-4">Product Name</th>
                                    <th className="px-5 py-4">Outlet</th>
                                    <th className="px-5 py-4">Snapshot Time</th>
                                    <th className="px-5 py-4 text-right">Units On Hand</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-neutral-100">
                                {inventoryQuery.isLoading ? (
                                    Array.from({ length: 5 }).map((_, i) => (
                                        <tr key={i}>
                                            <td colSpan={4} className="px-5 py-4">
                                                <div className="h-4 animate-pulse rounded bg-neutral-100 w-full" />
                                            </td>
                                        </tr>
                                    ))
                                ) : latestInventory.length === 0 ? (
                                    <tr>
                                        <td colSpan={4} className="px-5 py-12 text-center text-sm text-neutral-400">
                                            No stock data available.
                                        </td>
                                    </tr>
                                ) : (
                                    latestInventory.map((item) => (
                                        <tr key={item.id} className="transition-colors hover:bg-neutral-50/60 group">
                                            <td className="px-5 py-4 font-medium text-neutral-900">{item.sku_name}</td>
                                            <td className="px-5 py-4 text-neutral-600">
                                                {outlets.find((o) => o.id === item.outlet_id)?.name ?? `Outlet ${item.outlet_id}`}
                                            </td>
                                            <td className="px-5 py-4 text-neutral-500 text-xs">
                                                {item.snapshot_date} • <span className="uppercase text-amber-600">{item.snapshot_time}</span>
                                            </td>
                                            <td className="px-5 py-4 text-right font-semibold tabular-nums text-neutral-800">
                                                {item.units_on_hand}
                                                {item.units_on_hand === 0 && (
                                                    <span className="ml-2 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
                                                        Out of stock
                                                    </span>
                                                )}
                                                {item.units_on_hand > 0 && item.units_on_hand <= 5 && (
                                                    <span className="ml-2 inline-flex items-center rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700 ring-1 ring-inset ring-orange-600/10">
                                                        Low
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </section>
            </main>
        </div>
    );
}
