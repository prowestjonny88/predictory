"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import Header from "@/components/Header";
import { api } from "@/lib/api";
import type { SKU } from "@/types";

function formatPrice(value: number) {
  return `RM ${value.toFixed(2)}`;
}

const UNIT_COST_RATIO = 0.4;

function formatUnitCost(price: number) {
  return formatPrice(price * UNIT_COST_RATIO);
}

export default function CatalogPage() {
  const skusQuery = useQuery<SKU[]>({
    queryKey: ["skus"],
    queryFn: api.skus,
    staleTime: 60_000,
  });

  const rows = useMemo(() => skusQuery.data ?? [], [skusQuery.data]);

  return (
    <div className="min-h-screen">
      <Header title="SKU Catalog" />

      <main className="max-w-5xl space-y-4 p-6">
        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-neutral-800">Items and prices</h2>
          <p className="text-xs text-neutral-500">
            Unit cost is derived as unit price x {UNIT_COST_RATIO.toFixed(2)} for demo purposes.
          </p>
        </div>

        {skusQuery.isLoading && (
          <div className="rounded-xl border border-neutral-200 bg-white p-6 text-sm text-neutral-500">
            Loading SKUs...
          </div>
        )}

        {skusQuery.error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {skusQuery.error instanceof Error ? skusQuery.error.message : "Failed to load SKUs"}
          </div>
        )}

        {!skusQuery.isLoading && rows.length === 0 && (
          <div className="rounded-xl border border-neutral-200 bg-white p-6 text-sm text-neutral-500">
            No SKU data found.
          </div>
        )}

        {rows.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3">Category</th>
                  <th className="px-4 py-3">Code</th>
                  <th className="px-4 py-3 text-right">Unit Price</th>
                  <th className="px-4 py-3 text-right">Unit cost</th>
                  <th className="px-4 py-3 text-right">Freshness (hrs)</th>
                  <th className="px-4 py-3 text-center">Bestseller</th>
                  <th className="px-4 py-3 text-center">Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rows.map((sku) => (
                  <tr key={sku.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3 font-medium text-neutral-900">{sku.name}</td>
                    <td className="px-4 py-3 text-neutral-600">{sku.category}</td>
                    <td className="px-4 py-3 text-neutral-500">{sku.code}</td>
                    <td className="px-4 py-3 text-right font-semibold text-neutral-900">
                      {formatPrice(sku.price)}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-700">
                      {formatUnitCost(sku.price)}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-600">{sku.freshness_hours}</td>
                    <td className="px-4 py-3 text-center text-neutral-600">
                      {sku.is_bestseller ? "Yes" : "No"}
                    </td>
                    <td className="px-4 py-3 text-center text-neutral-600">
                      {sku.is_active ? "Yes" : "No"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
