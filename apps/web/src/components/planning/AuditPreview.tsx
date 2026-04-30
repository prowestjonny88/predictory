import { Badge } from "@/components/ui/badge";

export interface AuditEventPreview {
  id: string;
  action: string;
  final_prep: number;
  reason?: string;
  timestamp: string;
}

interface Props {
  events: AuditEventPreview[];
}

export default function AuditPreview({ events }: Props) {
  if (events.length === 0) {
    return <p className="text-xs text-neutral-500">No audit events recorded yet.</p>;
  }

  return (
    <div className="space-y-2">
      {events.map((event) => (
        <div key={event.id} className="flex items-center justify-between rounded-lg border border-neutral-100 bg-neutral-50 p-2">
          <div>
            <p className="text-xs font-semibold text-neutral-900">{event.action}</p>
            {event.reason && <p className="text-xs text-neutral-500">{event.reason}</p>}
          </div>
          <div className="text-right">
            <Badge variant="outline">Final {event.final_prep}</Badge>
            <p className="text-[10px] text-neutral-400">{event.timestamp}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
