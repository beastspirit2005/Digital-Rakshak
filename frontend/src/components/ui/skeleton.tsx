import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-control bg-surface-2", className)} />;
}

/** Placeholder rows shaped like the table they replace. */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="px-6 py-4 space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-5 w-20 rounded-pill" />
        </div>
      ))}
    </div>
  );
}

export function StatSkeleton() {
  return (
    <div className="rounded-card bg-surface shadow-card px-6 py-5">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-8 w-20 mt-3" />
    </div>
  );
}
