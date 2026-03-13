"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { ForecastLine } from "@/types";

interface ForecastDisplayLine extends ForecastLine {
  run_id: number;
}

interface Props {
  lines: ForecastDisplayLine[];
}

const DAYPART_COLORS = ["#FCD34D", "#F59E0B", "#D97706"];

export default function ForecastChart({ lines }: Props) {
  if (!lines || lines.length === 0) return null;

  // Aggregate total per SKU (top 8 for readability)
  const bySkuMap = lines.reduce((acc, line) => {
    const key = line.sku_name ?? `SKU ${line.sku_id}`;
    acc[key] = (acc[key] ?? 0) + line.total;
    return acc;
  }, {} as Record<string, number>);

  const data = Object.entries(bySkuMap)
    .sort(([, a], [, b]) => (b as number) - (a as number))
    .slice(0, 8)
    .map(([name, total]) => ({ name, total: Math.round(total as number) }));

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Forecasted Units by SKU
      </h3>
      <div className="h-52 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            layout="vertical"
            data={data}
            margin={{ top: 0, right: 40, left: 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#E5E7EB" />
            <XAxis
              type="number"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 11, fill: "#9CA3AF" }}
            />
            <YAxis
              type="category"
              dataKey="name"
              width={130}
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#374151" }}
            />
            <Tooltip
              cursor={{ fill: "#F9FAFB" }}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid #E5E7EB",
                boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
                fontSize: 12,
              }}
            formatter={(value) => [`${value} units`, "Forecast"]}
            />
            <Bar dataKey="total" radius={[0, 4, 4, 0]} maxBarSize={20}>
              {data.map((_, i) => (
                <Cell
                  key={i}
                  fill={DAYPART_COLORS[i % DAYPART_COLORS.length]}
                />
              ))}
              <LabelList
                dataKey="total"
                position="right"
                style={{ fontSize: 11, fill: "#6B7280" }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
