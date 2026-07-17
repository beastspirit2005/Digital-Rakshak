import React from "react";

import { Download, User, ShieldCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

export function CaseActivityTimeline({ events }: { events: any[] }) {
  if (!events || events.length === 0) {
    return (
      <div className="py-4 text-sm text-ink-3">
        No case activity recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-6 mt-4 relative before:absolute before:inset-y-0 before:left-[15px] before:w-[2px] before:bg-line">
      {events.map((event, i) => {
        const isCitizen = event.author === "Citizen";
        return (
          <div key={i} className="relative flex gap-4 pl-4">
            <div className="absolute left-[7px] w-[18px] h-[18px] rounded-full bg-surface-2 border-2 border-surface flex items-center justify-center mt-1 z-10">
              {isCitizen ? (
                <User className="w-2.5 h-2.5 text-accent-text" />
              ) : (
                <ShieldCheck className="w-2.5 h-2.5 text-success" />
              )}
            </div>
            <div className="flex-1 bg-surface-2 p-3 rounded-control text-sm shadow-sm ml-4 border border-line">
              <div className="flex justify-between items-start mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-ink">{event.author}</span>
                  <Badge tone="neutral" className={cn(
                    "text-[10px] uppercase",
                    event.action === "Resolved" ? "text-success border-success/30 bg-success/10" : 
                    event.action === "Reopened" ? "text-accent-text border-accent-text/30 bg-accent/10" : ""
                  )}>
                    {event.action}
                  </Badge>
                </div>
                {event.timestamp && (
                  <span className="text-xs text-ink-3">
                    {new Date(event.timestamp + "Z").toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "numeric", hour12: true })}
                  </span>
                )}
              </div>
              
              {event.remark && (
                <div className="text-ink-2 mt-1 whitespace-pre-wrap">
                  {event.remark}
                </div>
              )}
              
              {event.attachment && (
                <div className="mt-3">
                  <a 
                    href={event.attachment} 
                    target="_blank" 
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-accent-text hover:text-accent-text/80 transition-colors bg-accent/10 px-2.5 py-1.5 rounded-full"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download Attachment
                  </a>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
