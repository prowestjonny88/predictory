"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { useCurrency } from "@/components/CurrencyProvider";
import Header from "@/components/Header";
import { useLanguage } from "@/components/i18n/LanguageProvider";
import { api } from "@/lib/api";
import type { SKU } from "@/types";

export default function CatalogPage() {
  const { t, language } = useLanguage();
  const { formatCurrency } = useCurrency();
  const skusQuery = useQuery<SKU[]>({
    queryKey: ["skus"],
    queryFn: api.skus,
    staleTime: 60_000,
  });

  const rows = useMemo(() => skusQuery.data ?? [], [skusQuery.data]);

  return (
    <div className="min-h-screen">
      <Header title={t("catalog.title", "SKU Catalog")} />

      <main className="max-w-5xl space-y-4 p-6">
        <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
          <h2 className="text-sm font-semibold text-neutral-800">
            {t("catalog.section.itemsPrices", "Items and prices")}
          </h2>
          <p className="text-xs text-neutral-500">
            {t(
              "catalog.section.unitCostHelper",
              "Unit cost is shown only when imported recipe and ingredient cost data is available."
            )}
          </p>
        </div>

        {skusQuery.isLoading && (
          <div className="rounded-xl border border-neutral-200 bg-white p-6 text-sm text-neutral-500">
            {t("catalog.loadingSkus", "Loading SKUs...")}
          </div>
        )}

        {skusQuery.error && (
          <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {skusQuery.error instanceof Error
              ? skusQuery.error.message
              : t("catalog.failedSkus", "Failed to load SKUs")}
          </div>
        )}

        {!skusQuery.isLoading && rows.length === 0 && (
          <div className="rounded-xl border border-neutral-200 bg-white p-6 text-sm text-neutral-500">
            {t("catalog.emptySkus", "No SKU data found.")}
          </div>
        )}

        {rows.length > 0 && (
          <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200 bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  <th className="px-4 py-3">{t("catalog.table.sku", "SKU")}</th>
                  <th className="px-4 py-3">{t("catalog.table.category", "Category")}</th>
                  <th className="px-4 py-3">{t("catalog.table.code", "Code")}</th>
                  <th className="px-4 py-3 text-right">{t("catalog.table.unitPrice", "Unit Price")}</th>
                  <th className="px-4 py-3 text-right">{t("catalog.table.unitCost", "Unit cost")}</th>
                  <th className="px-4 py-3 text-right">{t("catalog.table.freshness", "Freshness (hrs)")}</th>
                  <th className="px-4 py-3 text-center">{t("catalog.table.bestseller", "Bestseller")}</th>
                  <th className="px-4 py-3 text-center">{t("catalog.table.active", "Active")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {rows.map((sku) => (
                  <tr key={sku.id} className="hover:bg-neutral-50">
                    <td className="px-4 py-3 font-medium text-neutral-900">{sku.name}</td>
                    <td className="px-4 py-3 text-neutral-600">{sku.category}</td>
                    <td className="px-4 py-3 text-neutral-500">{sku.code}</td>
                    <td className="px-4 py-3 text-right font-semibold text-neutral-900">
                      {formatCurrency(sku.price, language, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-700">
                      {sku.unit_cost == null
                        ? t("common.unavailable", "Unavailable")
                        : formatCurrency(sku.unit_cost, language, {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                    </td>
                    <td className="px-4 py-3 text-right text-neutral-600">{sku.freshness_hours}</td>
                    <td className="px-4 py-3 text-center text-neutral-600">
                      {sku.is_bestseller ? t("common.yes", "Yes") : t("common.no", "No")}
                    </td>
                    <td className="px-4 py-3 text-center text-neutral-600">
                      {sku.is_active ? t("common.yes", "Yes") : t("common.no", "No")}
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
