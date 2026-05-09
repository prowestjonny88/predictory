import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  stock: number;
  need: number;
  unit: string;
}

export default function StockNeedBar({ stock, need, unit }: Props) {
  const { t } = useLanguage();
  const max = Math.max(stock, need, 1);
  const stockWidth = Math.min(100, (stock / max) * 100);
  const needWidth = Math.min(100, (need / max) * 100);
  const isShort = stock < need;
  const suffix = unit ? ` ${unit}` : "";


  return (
    <div className="min-w-[180px] space-y-2">
      <div className="space-y-1">
        <div className="h-2 rounded-full bg-neutral-100">
          <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${stockWidth}%` }} />
        </div>
        <div className="flex justify-between gap-2 text-[11px] text-neutral-500">
          <span>{t("stock.stock", "Stock")}</span>
          <span className="tabular-nums">{stock.toFixed(1)}{suffix}</span>
        </div>
      </div>

      <div className="space-y-1">
        <div className="h-2 rounded-full bg-neutral-100">
          <div className="h-2 rounded-full bg-red-500" style={{ width: `${needWidth}%` }} />
        </div>
        <div className={isShort ? "flex justify-between gap-2 text-[11px] font-medium text-red-600" : "flex justify-between gap-2 text-[11px] text-neutral-500"}>
          <span>{t("stock.need", "Need")}</span>
          <span className="tabular-nums">{need.toFixed(1)}{suffix}</span>
        </div>
      </div>

    </div>
  );
}
