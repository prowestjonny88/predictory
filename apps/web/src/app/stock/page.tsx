"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import type { Inventory, Outlet, Ingredient } from "@/types";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card } from "@/components/ui/card";

type StockView = "grouped" | "all" | `outlet:${string}`;

export default function StockPage() {
    const [stockView, setStockView] = useState<StockView>("grouped");
    const { t } = useLanguage();
    const separator = t("common.listSeparator", " • ");

    const outletsQuery = useQuery<Outlet[]>({
        queryKey: ["outlets"],
        queryFn: api.outlets,
        staleTime: Infinity,
    });

    const selectedOutletId = stockView.startsWith("outlet:") ? stockView.replace("outlet:", "") : "all";

    const inventoryQuery = useQuery<Inventory[]>({
        queryKey: ["inventory", selectedOutletId],
        queryFn: () => api.inventory(selectedOutletId),
        staleTime: 120_000,
        placeholderData: (previous) => previous,
        refetchInterval: 30000,
    });

    const ingredientsQuery = useQuery<Ingredient[]>({
        queryKey: ["ingredients"],
        queryFn: api.ingredients,
        staleTime: Infinity,
    });

    const outlets = outletsQuery.data ?? [];
    const inventory = inventoryQuery.data ?? [];
    const ingredients = ingredientsQuery.data ?? [];

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

    const inventoryByOutlet = useMemo(() => {
        const byOutlet = new Map<number, Inventory[]>();
        for (const item of latestInventory) {
            const rows = byOutlet.get(item.outlet_id) ?? [];
            rows.push(item);
            byOutlet.set(item.outlet_id, rows);
        }
        return outlets
            .map((outlet) => ({
                outlet,
                rows: (byOutlet.get(outlet.id) ?? []).sort((a, b) => a.sku_name.localeCompare(b.sku_name)),
            }))
            .filter((group) => group.rows.length > 0);
    }, [latestInventory, outlets]);

    function renderInventoryTable(rows: Inventory[], showOutlet: boolean) {
        return (
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead>{t("stock.productName", "Product Name")}</TableHead>
                        {showOutlet && <TableHead>{t("stock.outlet", "Outlet")}</TableHead>}
                        <TableHead>{t("stock.snapshotTime", "Snapshot Time")}</TableHead>
                        <TableHead className="text-right">{t("stock.unitsOnHand", "Units On Hand")}</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {inventoryQuery.isLoading ? (
                        Array.from({ length: 5 }).map((_, i) => (
                            <TableRow key={i}>
                                <TableCell colSpan={showOutlet ? 4 : 3}>
                                    <div className="h-4 animate-pulse rounded bg-neutral-100 w-full" />
                                </TableCell>
                            </TableRow>
                        ))
                    ) : rows.length === 0 ? (
                        <TableRow>
                            <TableCell colSpan={showOutlet ? 4 : 3} className="px-5 py-12 text-center text-sm text-neutral-400">
                                {t("stock.noStockData", "No stock data available.")}
                            </TableCell>
                        </TableRow>
                    ) : (
                        rows.map((item) => (
                            <TableRow key={item.id} className="transition-colors hover:bg-neutral-50/60 group">
                                <TableCell className="font-medium text-neutral-900">{item.sku_name}</TableCell>
                                {showOutlet && (
                                    <TableCell className="text-neutral-600">
                                        {outlets.find((o) => o.id === item.outlet_id)?.name ?? `${t("common.outlet", "Outlet")} ${item.outlet_id}`}
                                    </TableCell>
                                )}
                                <TableCell className="text-neutral-500 text-xs">
                                    {item.snapshot_date}{separator}<span className="uppercase text-amber-600">{item.snapshot_time}</span>
                                </TableCell>
                                <TableCell className="text-right font-semibold tabular-nums text-neutral-800">
                                    {item.units_on_hand}
                                    {item.units_on_hand === 0 && (
                                        <span className="ml-2 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
                                            {t("stock.outOfStock", "Out of stock")}
                                        </span>
                                    )}
                                    {item.units_on_hand > 0 && item.units_on_hand <= 5 && (
                                        <span className="ml-2 inline-flex items-center rounded-full bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-700 ring-1 ring-inset ring-orange-600/10">
                                            {t("stock.lowStock", "Low")}
                                        </span>
                                    )}
                                </TableCell>
                            </TableRow>
                        ))
                    )}
                </TableBody>
            </Table>
        );
    }

    return (
        <div className="min-h-screen">
            <Header title={t("nav.stock", "Current Stock")} date={new Date().toISOString().split("T")[0]}>
                <select
                    value={stockView}
                    onChange={(e) => setStockView(e.target.value as StockView)}
                    className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                    <option value="grouped">{t("stock.groupedByOutlet", "Grouped by Outlet")}</option>
                    <option value="all">{t("common.allOutlets", "All Outlets")}</option>
                    {outlets.map((outlet) => (
                        <option key={outlet.id} value={`outlet:${outlet.id}`}>
                            {outlet.name}
                        </option>
                    ))}
                </select>
            </Header>

            <main className="max-w-6xl space-y-6 p-6 page-enter mx-auto">
                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600 pl-1">
                            {t("stock.outletInventory", "Outlet Inventory")}
                        </h2>
                    </div>

                    <Card>
                        {stockView === "grouped" ? (
                            <div className="divide-y divide-neutral-100">
                                {inventoryQuery.isLoading ? (
                                    renderInventoryTable([], false)
                                ) : inventoryByOutlet.length === 0 ? (
                                    <div className="px-5 py-12 text-center text-sm text-neutral-400">
                                        {t("stock.noStockData", "No stock data available.")}
                                    </div>
                                ) : (
                                    inventoryByOutlet.map(({ outlet, rows }) => (
                                        <section key={outlet.id} className="p-4">
                                            <div className="mb-3 flex items-center justify-between">
                                                <h3 className="text-sm font-semibold text-neutral-900">{outlet.name}</h3>
                                                <span className="text-xs text-neutral-400">
                                                    {rows.length} {rows.length === 1 ? t("common.item", "item") : t("common.items", "items")}
                                                </span>
                                            </div>
                                            <div className="overflow-hidden rounded-lg border border-neutral-100">
                                                {renderInventoryTable(rows, false)}
                                            </div>
                                        </section>
                                    ))
                                )}
                            </div>
                        ) : (
                            renderInventoryTable(latestInventory, stockView === "all")
                        )}
                    </Card>
                </section>

                <section>
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-sm font-bold uppercase tracking-wide text-neutral-600 pl-1">
                            {t("stock.baseIngredients", "Base Ingredients")}
                        </h2>
                    </div>

                    <Card>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>{t("stock.ingredientName", "Ingredient Name")}</TableHead>
                                    <TableHead>{t("stock.outlet", "Outlet")}</TableHead>
                                    <TableHead>{t("stock.snapshotTime", "Snapshot Time")}</TableHead>
                                    <TableHead className="text-right">{t("stock.stockOnHand", "Stock On Hand")}</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {ingredientsQuery.isLoading ? (
                                    Array.from({ length: 5 }).map((_, i) => (
                                        <TableRow key={i}>
                                            <TableCell colSpan={4}>
                                                <div className="h-4 animate-pulse rounded bg-neutral-100 w-full" />
                                            </TableCell>
                                        </TableRow>
                                    ))
                                ) : ingredients.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={4} className="px-5 py-12 text-center text-sm text-neutral-400">
                                            {t("stock.noIngredientData", "No ingredient data available.")}
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    ingredients.map((item) => (
                                        <TableRow key={item.id} className="transition-colors hover:bg-neutral-50/60 group">
                                            <TableCell className="font-medium text-neutral-900">{item.name}</TableCell>
                                            <TableCell className="text-neutral-600">{t("stock.centralWarehouse", "Central Warehouse")}</TableCell>
                                            <TableCell className="text-neutral-500 text-xs">
                                                {new Date().toISOString().split("T")[0]}{separator}<span className="uppercase text-amber-600">{t("stock.live", "LIVE")}</span>
                                            </TableCell>
                                            <TableCell className="text-right font-semibold tabular-nums text-neutral-800">
                                                {item.stock_on_hand?.toFixed(2) ?? "-"} <span className="text-neutral-500 text-xs font-normal ml-1">{item.unit}</span>
                                                {(item.stock_on_hand ?? 0) < (item.reorder_point ?? 0) && (
                                                    <span className="ml-2 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-medium text-red-700 ring-1 ring-inset ring-red-600/10">
                                                        {t("stock.needsReorder", "Needs Reorder")}
                                                    </span>
                                                )}
                                            </TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </Card>
                </section>
            </main>
        </div>
    );
}
