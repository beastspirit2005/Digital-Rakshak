import { cn } from "@/lib/utils";

/** Standard raised surface. Premium depth comes from fine borders, subtle shadows, and layered values. */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-card bg-surface border border-line/10 shadow-card transition-all duration-200 relative overflow-hidden",
        className
      )}
      {...props}
    />
  );
}

/** Recessed intelligence module — sitting clean within cards or on parent surfaces. */
export function Inset({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div 
      className={cn("rounded-control bg-surface-2 border border-line/5 p-4", className)} 
      {...props} 
    />
  );
}

export function CardHeader({
  title,
  sub,
  action,
  className,
}: {
  title: React.ReactNode;
  sub?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4 px-6 pt-5 pb-4 border-b border-line/5", className)}>
      <div>
        <h3 className="font-display font-bold text-base text-ink tracking-tight">{title}</h3>
        {sub && <p className="text-xs text-ink-2 mt-1">{sub}</p>}
      </div>
      {action}
    </div>
  );
}