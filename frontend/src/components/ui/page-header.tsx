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
    <div className={cn("flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-line/10 mb-8", className)}>
      <div className="space-y-1.5">
        <h1 className="font-display font-extrabold text-2xl sm:text-3xl tracking-tight text-ink">
          {title}
        </h1>
        {sub && <p className="text-sm sm:text-[15px] text-ink-2 font-medium max-w-2xl leading-relaxed">{sub}</p>}
      </div>
      {actions && (
        <div className="flex items-center gap-3 shrink-0 self-start md:self-center">
          {actions}
        </div>
      )}
    </div>
  );
}