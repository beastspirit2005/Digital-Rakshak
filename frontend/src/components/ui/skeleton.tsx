import { cn } from "@/lib/utils";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-control bg-surface-3/30", className)} />;
}

/** Slow, pulsing placeholder rows styled after security records */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="px-6 py-6 space-y-4 bg-surface border border-line/10 rounded-card">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex items-center gap-6">
          <Skeleton className="h-4.5 w-32" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-5.5 w-24 rounded-pill" />
        </div>
      ))}
    </div>
  );
}

export function StatSkeleton() {
  return (
    <div className="rounded-card bg-surface border border-line/10 px-6 py-5.5 shadow-sm">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-9 w-20 mt-3" />
    </div>
  );
}