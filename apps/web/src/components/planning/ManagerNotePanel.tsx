import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ManagerNoteResponse } from "@/lib/api/planning";

interface Props {
  onParse: (note: string) => Promise<ManagerNoteResponse | null>;
  onApply: (adjustment: ManagerNoteResponse["parsed_adjustment"]) => Promise<void>;
}

export default function ManagerNotePanel({ onParse, onApply }: Props) {
  const [note, setNote] = useState("");
  const [parsing, setParsing] = useState(false);
  const [result, setResult] = useState<ManagerNoteResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  async function handleParse() {
    setParsing(true);
    setError(null);
    try {
      const response = await onParse(note);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to parse note");
      setResult(null);
    } finally {
      setParsing(false);
    }
  }

  async function handleApply() {
    if (!result) {
      return;
    }
    setApplying(true);
    await onApply(result.parsed_adjustment);
    setApplying(false);
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Manager note parser</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <textarea
          className="min-h-[90px] w-full rounded-lg border border-neutral-200 p-3 text-sm"
          placeholder="School group visiting KLCC tomorrow morning, expect more pastries."
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" size="sm" onClick={handleParse} disabled={parsing || note.length < 10}>
            {parsing ? "Parsing..." : "Parse note"}
          </Button>
          {error && <span className="text-xs text-red-600">{error}</span>}
        </div>

        {result && (
          <div className="rounded-lg border border-neutral-100 bg-neutral-50 p-3 text-sm">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Suggested adjustment</p>
            <p className="font-semibold text-neutral-900">
              {result.parsed_adjustment.outlet_id} · {result.parsed_adjustment.daypart} · {result.parsed_adjustment.sku_category}
            </p>
            <p className="text-xs text-neutral-500">
              +{result.parsed_adjustment.suggested_adjustment_pct}% · {result.parsed_adjustment.reason}
            </p>
            <p className="mt-2 text-xs text-neutral-500">{result.explanation}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button variant="primary" size="sm" onClick={handleApply} disabled={applying}>
                {applying ? "Applying..." : "Apply"}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setResult(null)}>
                Ignore
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
