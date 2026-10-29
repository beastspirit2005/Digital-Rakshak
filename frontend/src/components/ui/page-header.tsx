import React from "react";
import { cn } from "@/lib/utils";

export type HeaderTone = "default" | "tactical" | "warning" | "danger" | "success" | "accent";

const toneStyles: Record<HeaderTone, { iconBox: string; icon: string; badge: string }> = {
  default: {
    iconBox: "bg-surface-2 border-line/40 text-ink",
    icon: "text-ink-2",
    badge: "bg-surface-3/30 text-ink-2 border-line/20",
  },
  tactical: {
    iconBox: "bg-indigo-500/10 border-indigo-500/25 text-indigo-400",
    icon: "text-indigo-400",
    badge: "bg-indigo-500/10 text-indigo-400 border-indigo-500/25",
  },
  warning: {
    iconBox: "bg-amber-500/10 border-amber-500/25 text-amber-400",
    icon: "text-amber-400",
    badge: "bg-amber-500/10 text-amber-400 border-amber-500/25",
  },
  danger: {
    iconBox: "bg-rose-500/10 border-rose-500/25 text-rose-400",
    icon: "text-rose-400",
    badge: "bg-rose-500/10 text-rose-400 border-rose-500/25",
  },
  success: {
    iconBox: "bg-emerald-500/10 border-emerald-500/25 text-emerald-400",
    icon: "text-emerald-400",
    badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/25",
  },
  accent: {
    iconBox: "bg-primary/10 border-primary/25 text-primary",
    icon: "text-primary",
    badge: "bg-primary/10 text-primary border-primary/25",
  },
};

export interface PageHeaderProps {
  title: React.ReactNode;
  sub?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string | { label: string; tone?: HeaderTone };
  tone?: HeaderTone;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  sub,
  icon: Icon,
  badge,
  tone = "default",
  actions,
  className,
}: PageHeaderProps) {
  const currentTone = toneStyles[tone] || toneStyles.default;
  const badgeLabel = typeof badge === "string" ? badge : badge?.label;
  const badgeTone = typeof badge === "object" && badge?.tone ? toneStyles[badge.tone]?.badge : currentTone.badge;

  return (
    <div
      className={cn(
        "flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-line/10 mb-8 relative",
        className
      )}
    >
      <div className="flex items-start gap-4">
        {Icon && (
          <div
            className={cn(
              "w-11 h-11 rounded-xl border flex items-center justify-center shrink-0 shadow-xs mt-0.5 transition-colors",
              currentTone.iconBox
            )}
          >
            <Icon className={cn("w-5 h-5", currentTone.icon)} />
          </div>
        )}

        <div className="space-y-1.5 min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="font-display font-extrabold text-2xl sm:text-3xl tracking-tight text-ink">
              {title}
            </h1>
            {badgeLabel && (
              <span
                className={cn(
                  "inline-flex items-center px-2 py-0.5 rounded-pill text-[11px] font-bold uppercase tracking-wider border",
                  badgeTone
                )}
              >
                {badgeLabel}
              </span>
            )}
          </div>
          {sub && (
            <p className="text-sm sm:text-[15px] text-ink-2 font-medium max-w-2xl leading-relaxed">
              {sub}
            </p>
          )}
        </div>
      </div>

      {actions && (
        <div className="flex items-center gap-3 shrink-0 self-start md:self-center">
          {actions}
        </div>
      )}
    </div>
  );
}
