import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Props {
  engineName: string;
  validationWindow: string;
  wape: number;
  coverage: number;
  onOpenEvidence: () => void;
}

export default function ModelBadge({
  engineName,
  validationWindow,
  wape,
  coverage,
  onOpenEvidence,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-col">
        <span className="text-xs uppercase tracking-wide text-neutral-500">Model badge</span>
        <span className="text-sm font-semibold text-neutral-900">{engineName}</span>
        <span className="text-xs text-neutral-500">Validation: {validationWindow}</span>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="info">WAPE {(wape * 100).toFixed(1)}%</Badge>
        <Badge variant="low">Coverage {(coverage * 100).toFixed(0)}%</Badge>
      </div>
      <Button variant="outline" size="sm" onClick={onOpenEvidence}>
        View evidence
      </Button>
    </div>
  );
}
