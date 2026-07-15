import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function EmptyState({
  icon: Icon,
  title,
  body,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  body?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center text-center py-20 px-6 bg-surface-2/20 border border-dashed border-line/20 rounded-card", className)}>
      <div className="w-14 h-14 rounded-control bg-accent/5 border border-accent/15 flex items-center justify-center mb-5 shadow-inner">
        <Icon className="w-6 h-6 text-accent-text" />
      </div>
      <h3 className="font-display font-bold text-lg text-ink tracking-tight">{title}</h3>
      {body && <p className="text-sm text-ink-2 mt-2 max-w-sm leading-relaxed">{body}</p>}
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}