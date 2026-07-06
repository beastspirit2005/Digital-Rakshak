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
    <div className={cn("flex flex-col items-center justify-center text-center py-16 px-6", className)}>
      <div className="w-12 h-12 rounded-pill bg-surface-2 flex items-center justify-center mb-4">
        <Icon className="w-5 h-5 text-ink-3" />
      </div>
      <h3 className="font-display font-semibold text-base text-ink">{title}</h3>
      {body && <p className="text-sm text-ink-2 mt-1.5 max-w-sm">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
