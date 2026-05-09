import { useLanguage } from "@/components/i18n/LanguageProvider";

interface Props {
  stock: number;
  need: number;
  shortage: number;
  unit: string;
}

export default function StockNeedBar({ stock, need, shortage, unit }: Props) {
  const { t } = useLanguage();
  const max = Math.max(stock, need, shortage, 1);
  const stockWidth = Math.min(100, (stock / max) * 100);
  const needWidth = Math.min(100, (need / max) * 100);
  const suffix = unit ? ` ${unit}` : "";

  return (
    <div className="min-w-[160px] space-y-1">
      <div className="h-2 rounded-full bg-neutral-100">
        <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${stockWidth}%` }} />
      </div>
      <div className="h-2 rounded-full bg-neutral-100">
        <div className="h-2 rounded-full bg-amber-500" style={{ width: `${needWidth}%` }} />
      </div>
      <div className="flex flex-wrap justify-between gap-2 text-[11px] text-neutral-500">
        <span>{t("stock.stock", "Stock")} {stock.toFixed(1)}{suffix}</span>
        <span>{t("stock.need", "Need")} {need.toFixed(1)}{suffix}</span>
        <span>{t("stock.short", "Short")} {shortage.toFixed(1)}{suffix}</span>
      </div>
    </div>
  );
}
