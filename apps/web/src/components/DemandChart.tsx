"use client";

import { useLanguage } from "@/components/i18n/LanguageProvider";
import type { DailyPlanForecastLine } from "@/types";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Props {
  forecasts: DailyPlanForecastLine[] | undefined;
}

export default function DemandChart({ forecasts }: Props) {
  const { t } = useLanguage();

  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-xl border border-neutral-200 bg-white shadow-sm">
        <span className="text-sm text-neutral-400">No forecast data available for chart.</span>
      </div>
    );
  }

  // Aggregate by outlet
  const aggregated = forecasts.reduce((acc, curr) => {
    const key = curr.outlet_name || "Unknown";
    if (!acc[key]) {
      acc[key] = {
        name: key,
        morning: 0,
        midday: 0,
        evening: 0,
      };
    }
    acc[key].morning += curr.morning;
    acc[key].midday += curr.midday;
    acc[key].evening += curr.evening;
    return acc;
  }, {} as Record<string, any>);

  const data = Object.values(aggregated);

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5 shadow-sm">
      <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Predicted Demand by Outlet
      </h3>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis
              dataKey="name"
              axisLine={false}
              tickLine={false}
              tick={{ fontSize: 12, fill: "#6B7280" }}
              dy={10}
            />
            <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: "#6B7280" }} />
            <Tooltip
              cursor={{ fill: "#F3F4F6" }}
              contentStyle={{ borderRadius: "8px", border: "1px solid #E5E7EB", boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)" }}
            />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: "#4B5563", marginTop: "10px" }} />
            <Bar dataKey="morning" name={t("common.daypart.morning", "Morning")} stackId="a" fill="#FCD34D" />
            <Bar dataKey="midday" name={t("common.daypart.midday", "Midday")} stackId="a" fill="#F59E0B" />
            <Bar dataKey="evening" name={t("common.daypart.evening", "Evening")} stackId="a" fill="#D97706" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
