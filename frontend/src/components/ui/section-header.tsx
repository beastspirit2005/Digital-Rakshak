import React from "react";
import { cn } from "@/lib/utils";
import type { HeaderTone } from "./page-header";

interface SectionHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  count?: number | string;
  tone?: HeaderTone;
  actions?: React.ReactNode;
  className?: string;
}

const toneMap: Record<HeaderTone, { iconBox: string; icon: string }> = {
  default: { iconBox: "bg-surface-2 border-line/40", icon: "text-ink-2" },
  tactical: { iconBox: "bg-indigo-500/10 border-indigo-500/25", icon: "text-indigo-400" },
  warning: { iconBox: "bg-amber-500/10 border-amber-500/25", icon: "text-amber-400" },
  danger: { iconBox: "bg-rose-500/10 border-rose-500/25", icon: "text-rose-400" },
  success: { iconBox: "bg-emerald-500/10 border-emerald-500/25", icon: "text-emerald-400" },
  accent: { iconBox: "bg-primary/10 border-primary/25", icon: "text-primary" },
};

export function SectionHeader({
  title,
  subtitle,
  icon: Icon,
  count,
  tone = "default",
  actions,
  className,
}: SectionHeaderProps) {
  const t = toneMap[tone] || toneMap.default;

  return (
    <div className={cn("flex items-center justify-between gap-4 mb-4", className)}>
      <div className="flex items-center gap-2.5 min-w-0">
        {Icon && (
          <div className={cn("w-7 h-7 rounded-lg border flex items-center justify-center shrink-0 shadow-2xs", t.iconBox)}>
            <Icon className={cn("w-3.5 h-3.5", t.icon)} />
          </div>
        )}
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-display font-bold text-sm tracking-wide uppercase text-ink">
              {title}
            </h3>
            {count !== undefined && (
              <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-surface-3/50 text-ink-2 border border-line/20">
                {count}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-ink-3 mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  );
}
