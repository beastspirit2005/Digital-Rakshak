import { Circle, Clock, CheckCircle2, ShieldAlert } from "lucide-react";

export function CaseTimeline({ events = [] }: { events: any[] }) {
  if (!events || events.length === 0) {
    return (
      <div className="text-center p-8 border border-dashed border-line rounded-card text-sm text-ink-2 bg-surface">
        <Clock className="w-6 h-6 mx-auto mb-2 text-ink-3" />
        No timeline events extracted yet.
      </div>
    );
  }

  return (
    <ol className="relative space-y-6 pl-8 before:absolute before:left-3 before:top-1 before:bottom-1 before:w-px before:bg-line">
      {events.map((event, index) => (
        <li key={index} className="relative">
          <span className="absolute -left-8 top-0.5 flex items-center justify-center w-6 h-6 rounded-pill bg-surface-2">
            {event.type === "critical" ? (
              <ShieldAlert className="w-3.5 h-3.5 text-danger" />
            ) : event.type === "action" ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-success" />
            ) : (
              <Circle className="w-3 h-3 text-ink-3" />
            )}
          </span>
          <div className="flex items-baseline justify-between gap-3">
            <p className="text-sm font-medium text-ink">{event.title}</p>
            <time className="text-xs text-ink-3 tabular shrink-0">{event.time}</time>
          </div>
          <p className="text-sm text-ink-2 mt-0.5">{event.description}</p>
        </li>
      ))}
    </ol>
  );
}
