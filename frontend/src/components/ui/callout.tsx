import React from "react";
import { cn } from "@/lib/utils";
import { AlertTriangle, AlertCircle, Info, CheckCircle2, ShieldAlert, X } from "lucide-react";
import type { HeaderTone } from "./page-header";

interface CalloutProps {
  title?: React.ReactNode;
  children: React.ReactNode;
  tone?: HeaderTone;
  icon?: React.ComponentType<{ className?: string }>;
  className?: string;
  onDismiss?: () => void;
}

const toneStyles: Record<HeaderTone, { container: string; iconBox: string; icon: React.ComponentType<{ className?: string }>; title: string }> = {
  default: {
    container: "bg-surface-2 border-line/40 text-ink",
    iconBox: "bg-surface-3/40 border-line/40 text-ink-2",
    icon: Info,
    title: "text-ink",
  },
  tactical: {
    container: "bg-indigo-500/10 border-indigo-500/25 text-indigo-300",
    iconBox: "bg-indigo-500/20 border-indigo-500/30 text-indigo-400",
    icon: ShieldAlert,
    title: "text-indigo-200",
  },
  warning: {
    container: "bg-amber-500/10 border-amber-500/25 text-amber-300",
    iconBox: "bg-amber-500/20 border-amber-500/30 text-amber-400",
    icon: AlertTriangle,
    title: "text-amber-200",
  },
  danger: {
    container: "bg-rose-500/10 border-rose-500/25 text-rose-300",
    iconBox: "bg-rose-500/20 border-rose-500/30 text-rose-400",
    icon: AlertCircle,
    title: "text-rose-200",
  },
  success: {
    container: "bg-emerald-500/10 border-emerald-500/25 text-emerald-300",
    iconBox: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
    icon: CheckCircle2,
    title: "text-emerald-200",
  },
  accent: {
    container: "bg-primary/10 border-primary/25 text-primary",
    iconBox: "bg-primary/20 border-primary/30 text-primary",
    icon: Info,
    title: "text-primary",
  },
};

export function Callout({
  title,
  children,
  tone = "warning",
  icon,
  className,
  onDismiss,
}: CalloutProps) {
  const t = toneStyles[tone] || toneStyles.warning;
  const IconComponent = icon || t.icon;

  return (
    <div
      role="alert"
      className={cn(
        "flex items-start gap-3.5 p-3.5 rounded-xl border text-sm leading-relaxed backdrop-blur-xs relative",
        t.container,
        className
      )}
    >
      <div className={cn("w-7 h-7 rounded-lg border flex items-center justify-center shrink-0 mt-0.5", t.iconBox)}>
        <IconComponent className="w-4 h-4" />
      </div>

      <div className="flex-1 min-w-0">
        {title && <h4 className={cn("font-semibold text-sm mb-0.5", t.title)}>{title}</h4>}
        <div className="text-xs sm:text-[13px] opacity-90">{children}</div>
      </div>

      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-current opacity-60 hover:opacity-100 transition-opacity p-1 -mr-1 -mt-1 rounded-md"
          aria-label="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
