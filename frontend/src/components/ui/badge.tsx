import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "lilac" | "peach" | "accent";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-2 text-ink-2",
  success: "bg-success-tint text-success",
  warning: "bg-warning-tint text-warning",
  danger: "bg-danger-tint text-danger",
  lilac: "bg-lilac/15 text-lilac-text",
  peach: "bg-peach/15 text-peach-text",
  accent: "bg-accent text-accent-ink",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: Tone;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-pill px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        tones[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

const statusTone: Record<string, Tone> = {
  resolved: "success",
  closed: "success",
  completed: "success",
  approved: "success",
  under_review: "warning",
  pending: "warning",
  analyzing: "warning",
  assigned: "lilac",
  investigating: "lilac",
  submitted: "neutral",
};

/** Case/status string → tinted badge with sentence-case label. */
export function StatusBadge({ status }: { status: string }) {
  const key = (status || "").toLowerCase();
  const label = key.replace(/_/g, " ");
  return <Badge tone={statusTone[key] ?? "neutral"} className="capitalize">{label}</Badge>;
}

const priorityTone: Record<string, Tone> = {
  critical: "danger",
  high: "peach",
  medium: "warning",
  low: "neutral",
};

export function PriorityBadge({ priority }: { priority: string }) {
  const key = (priority || "").toLowerCase();
  return <Badge tone={priorityTone[key] ?? "neutral"} className="capitalize">{key || "—"}</Badge>;
}
