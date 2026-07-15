import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "lilac" | "peach" | "accent";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-3/30 text-ink-2 border-line/10",
  success: "bg-success-tint text-success border-success/15",
  warning: "bg-warning-tint text-warning border-warning/15",
  danger: "bg-danger-tint text-danger border-danger/15",
  lilac: "bg-lilac/10 text-lilac-text border-lilac/15",
  peach: "bg-peach/10 text-peach-text border-peach/15",
  accent: "bg-accent/10 text-accent-text border-accent/20",
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
        "inline-flex items-center gap-1.5 rounded-pill px-2.5 py-0.5 text-xs font-semibold whitespace-nowrap border",
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
  submitted: "accent",
};

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
  return <Badge tone={priorityTone[key] ?? "neutral"} className="capitalize font-mono">{key || "—"}</Badge>;
}