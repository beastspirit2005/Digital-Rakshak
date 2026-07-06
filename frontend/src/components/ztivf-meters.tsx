import { cn } from "@/lib/utils";

/** Zero-trust validation scores as quiet labeled meters. */
export function ZtivfMeters({
  metrics,
  className,
}: {
  metrics: Record<string, unknown>;
  className?: string;
}) {
  return (
    <div className={cn("grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3", className)}>
      {Object.entries(metrics).map(([key, value]) => {
        const v = Math.max(0, Math.min(1, Number(value) || 0));
        return (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-ink-2 capitalize">{key.replace(/_score$/, "").replace(/_/g, " ")}</span>
              <span className="text-ink font-medium tabular">{Math.round(v * 100)}%</span>
            </div>
            <div className="h-1.5 w-full bg-surface-3 rounded-pill overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-pill",
                  v > 0.8 ? "bg-success" : v > 0.5 ? "bg-warning" : "bg-danger"
                )}
                style={{ width: `${v * 100}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
