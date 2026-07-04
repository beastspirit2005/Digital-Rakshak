import { Circle, Clock, CheckCircle2, ShieldAlert } from "lucide-react";

export function CaseTimeline({ events = [] }: { events: any[] }) {
  if (!events || events.length === 0) {
    return (
      <div className="text-center p-8 border border-dashed border-border rounded-xl text-muted-foreground bg-card">
        <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
        No timeline events extracted yet.
      </div>
    );
  }

  return (
    <div className="space-y-8 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
      {events.map((event, index) => (
        <div key={index} className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
          {/* Icon */}
          <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-background bg-card text-primary shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
            {event.type === 'critical' ? (
              <ShieldAlert className="w-4 h-4 text-red-500" />
            ) : event.type === 'action' ? (
              <CheckCircle2 className="w-4 h-4 text-green-500" />
            ) : (
              <Circle className="w-4 h-4" />
            )}
          </div>
          
          {/* Card */}
          <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-4 rounded-xl border border-border bg-card shadow-sm hover:border-primary/50 transition-colors">
            <div className="flex items-center justify-between mb-1">
              <div className="font-bold text-foreground">{event.title}</div>
              <time className="text-xs font-medium text-purple-400">{event.time}</time>
            </div>
            <div className="text-sm text-muted-foreground">{event.description}</div>
          </div>
        </div>
      ))}
    </div>
  );
}
