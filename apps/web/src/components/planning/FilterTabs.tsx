import { cn } from "@/lib/utils";
import { useLanguage } from "@/components/i18n/LanguageProvider";

export type FilterKey = "outlet" | "sku" | "risk";

interface Props {
  value: FilterKey;
  onChange: (value: FilterKey) => void;
}

const tabs: { key: FilterKey; label: string }[] = [
  { key: "outlet", label: "By Outlet" },
  { key: "sku", label: "By SKU" },
  { key: "risk", label: "By Risk" },
];

export default function FilterTabs({ value, onChange }: Props) {
  const { t } = useLanguage();
  return (
    <div className="inline-flex flex-wrap gap-2 rounded-full border border-neutral-200 bg-white p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          className={cn(
            "rounded-full px-3 py-1 text-xs font-semibold transition",
            value === tab.key
              ? "bg-neutral-900 text-white"
              : "text-neutral-600 hover:bg-neutral-100"
          )}
          onClick={() => onChange(tab.key)}
        >
          {t(
            `planning.filter.${tab.key}`,
            tab.label
          )}
        </button>
      ))}
    </div>
  );
}
