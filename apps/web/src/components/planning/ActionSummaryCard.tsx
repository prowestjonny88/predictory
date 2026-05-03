import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/components/i18n/LanguageProvider";

interface SummaryAction {
  label: string;
  value: string;
  tone?: "info" | "low" | "medium" | "high";
}

interface Props {
  title: string;
  items: SummaryAction[];
  subtext?: string;
}

export default function ActionSummaryCard({ title, items, subtext }: Props) {
  const { t } = useLanguage();
  return (
    <Card className="border-amber-200 bg-gradient-to-br from-amber-50 via-white to-white">
      <CardHeader className="flex items-center justify-between">
        <CardTitle className="text-base text-neutral-900">{title}</CardTitle>
        <Badge variant="info">{t("planning.actionSummary.badge", "Action summary")}</Badge>
      </CardHeader>
      <CardContent className="grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <div key={item.label} className="rounded-lg border border-neutral-100 bg-white p-3">
            <p className="text-[11px] uppercase tracking-wide text-neutral-500">{item.label}</p>
            <p className="text-sm font-semibold text-neutral-900">{item.value}</p>
          </div>
        ))}
        {subtext && (
          <p className="text-xs text-neutral-500 md:col-span-2">{subtext}</p>
        )}
      </CardContent>
    </Card>
  );
}
