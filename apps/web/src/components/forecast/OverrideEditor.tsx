"use client";

import { useEffect, useState } from "react";

import type { ForecastOverride, ForecastOverridePayload, SKU } from "@/types";

interface Props {
  targetDate: string;
  outletId: number;
  skus: SKU[];
  editingOverride: ForecastOverride | null;
  onCancelEdit: () => void;
  onSubmit: (
    payload:
      | ForecastOverridePayload
      | Partial<Pick<ForecastOverridePayload, "title" | "notes" | "adjustment_pct" | "enabled">>,
    overrideId?: number
  ) => void;
  isBusy: boolean;
}

const DEFAULT_FORM = {
  scope: "outlet" as "outlet" | "sku",
  skuId: "",
  overrideType: "promo" as "promo" | "event",
  title: "",
  notes: "",
  adjustmentPct: "0",
  enabled: true,
};

export default function OverrideEditor({
  targetDate,
  outletId,
  skus,
  editingOverride,
  onCancelEdit,
  onSubmit,
  isBusy,
}: Props) {
  const [scope, setScope] = useState<"outlet" | "sku">(DEFAULT_FORM.scope);
  const [skuId, setSkuId] = useState(DEFAULT_FORM.skuId);
  const [overrideType, setOverrideType] = useState<"promo" | "event">(DEFAULT_FORM.overrideType);
  const [title, setTitle] = useState(DEFAULT_FORM.title);
  const [notes, setNotes] = useState(DEFAULT_FORM.notes);
  const [adjustmentPct, setAdjustmentPct] = useState(DEFAULT_FORM.adjustmentPct);
  const [enabled, setEnabled] = useState(DEFAULT_FORM.enabled);

  useEffect(() => {
    if (!editingOverride) {
      setScope(DEFAULT_FORM.scope);
      setSkuId(DEFAULT_FORM.skuId);
      setOverrideType(DEFAULT_FORM.overrideType);
      setTitle(DEFAULT_FORM.title);
      setNotes(DEFAULT_FORM.notes);
      setAdjustmentPct(DEFAULT_FORM.adjustmentPct);
      setEnabled(DEFAULT_FORM.enabled);
      return;
    }

    setScope(editingOverride.sku_id ? "sku" : "outlet");
    setSkuId(editingOverride.sku_id ? String(editingOverride.sku_id) : "");
    setOverrideType(editingOverride.override_type);
    setTitle(editingOverride.title);
    setNotes(editingOverride.notes ?? "");
    setAdjustmentPct(String(editingOverride.adjustment_pct));
    setEnabled(editingOverride.enabled);
  }, [editingOverride]);

  function handleSubmit() {
    const parsedAdjustment = Number(adjustmentPct);
    if (!title.trim() || Number.isNaN(parsedAdjustment)) {
      return;
    }

    if (editingOverride) {
      onSubmit(
        {
          title: title.trim(),
          notes: notes.trim() || null,
          adjustment_pct: parsedAdjustment,
          enabled,
        },
        editingOverride.id
      );
      return;
    }

    onSubmit({
      target_date: targetDate,
      outlet_id: outletId,
      sku_id: scope === "sku" && skuId ? Number(skuId) : null,
      override_type: overrideType,
      title: title.trim(),
      notes: notes.trim() || null,
      adjustment_pct: parsedAdjustment,
      enabled,
      created_by: "planner",
    });
  }

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-neutral-800">
            {editingOverride ? "Edit Override" : "Add Event / Promo Override"}
          </h3>
          <p className="mt-1 text-xs text-neutral-500">
            Overrides adjust the forecast before prep and replenishment planning.
          </p>
        </div>
        {editingOverride && (
          <button
            onClick={onCancelEdit}
            className="text-xs font-medium text-neutral-500 hover:text-neutral-700"
          >
            Cancel edit
          </button>
        )}
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
          Scope
          <select
            value={scope}
            onChange={(event) => setScope(event.target.value as "outlet" | "sku")}
            disabled={isBusy || Boolean(editingOverride?.sku_id)}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            <option value="outlet">Outlet-wide</option>
            <option value="sku">Specific SKU</option>
          </select>
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
          Type
          <select
            value={overrideType}
            onChange={(event) => setOverrideType(event.target.value as "promo" | "event")}
            disabled={isBusy || Boolean(editingOverride)}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
          >
            <option value="promo">Promo</option>
            <option value="event">Event</option>
          </select>
        </label>

        {scope === "sku" && (
          <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
            SKU
            <select
              value={skuId}
              onChange={(event) => setSkuId(event.target.value)}
              disabled={isBusy || Boolean(editingOverride?.sku_id)}
              className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
            >
              <option value="">Choose SKU</option>
              {skus.map((sku) => (
                <option key={sku.id} value={String(sku.id)}>
                  {sku.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600">
          Adjustment %
          <input
            type="number"
            min={-50}
            max={100}
            step={1}
            value={adjustmentPct}
            onChange={(event) => setAdjustmentPct(event.target.value)}
            disabled={isBusy}
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600 md:col-span-2">
          Title
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={isBusy}
            placeholder="e.g. Morning pastry push"
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400"
          />
        </label>

        <label className="flex flex-col gap-1 text-xs font-medium text-neutral-600 md:col-span-2">
          Notes
          <textarea
            rows={2}
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            disabled={isBusy}
            placeholder="Optional operational note"
            className="rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-none"
          />
        </label>
      </div>

      <label className="mt-3 flex items-center gap-2 text-sm text-neutral-600">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(event) => setEnabled(event.target.checked)}
          disabled={isBusy}
        />
        Override enabled
      </label>

      <div className="mt-4 flex items-center justify-end gap-3">
        {editingOverride && (
          <button
            onClick={onCancelEdit}
            className="rounded-md border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          >
            Cancel
          </button>
        )}
        <button
          onClick={handleSubmit}
          disabled={isBusy || !title.trim() || (scope === "sku" && !skuId)}
          className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-600 disabled:opacity-50"
        >
          {isBusy ? "Saving..." : editingOverride ? "Update override" : "Save override"}
        </button>
      </div>
    </div>
  );
}
