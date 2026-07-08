import { cn } from "@/lib/utils";

/** Standard raised surface. Depth comes from tint + one soft shadow, not borders. */
export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("rounded-card bg-surface shadow-card", className)}
      {...props}
    />
  );
}

/** Recessed module — sits inside cards or directly on the page background. */
export function Inset({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card bg-surface-2", className)} {...props} />;
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
    <div className={cn("flex items-start justify-between gap-4 px-6 pt-5 pb-4", className)}>
      <div>
        <h3 className="font-display font-semibold text-base text-ink">{title}</h3>
        {sub && <p className="text-sm text-ink-2 mt-0.5">{sub}</p>}
      </div>
      {action}
    </div>
  );
}
