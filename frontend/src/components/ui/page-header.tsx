import { cn } from "@/lib/utils";

export function PageHeader({
  title,
  sub,
  actions,
  className,
}: {
  title: React.ReactNode;
  sub?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col sm:flex-row sm:items-end justify-between gap-4", className)}>
      <div>
        <h1 className="font-display font-semibold text-xl sm:text-2xl tracking-tight text-ink">
          {title}
        </h1>
        {sub && <p className="text-sm text-ink-2 mt-1.5 max-w-2xl">{sub}</p>}
      </div>
      {actions && <div className="flex items-center gap-3 shrink-0">{actions}</div>}
    </div>
  );
}
