"use client";

import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: React.ReactNode;
}

/** Segmented control with a sliding active indicator. */
export function Segmented({
  items,
  value,
  onChange,
  className,
  layoutId = "segmented-indicator",
}: {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
  layoutId?: string;
}) {
  const reduced = useReducedMotion();
  return (
    <div
      role="tablist"
      className={cn("inline-flex p-1 rounded-control bg-surface-2 gap-1", className)}
    >
      {items.map((item) => {
        const active = item.id === value;
        return (
          <button
            key={item.id}
            role="tab"
            aria-selected={active}
            type="button"
            onClick={() => onChange(item.id)}
            className={cn(
              "relative flex-1 h-9 px-4 rounded-[6px] text-sm font-medium whitespace-nowrap",
              "transition-colors duration-150",
              active ? "text-ink" : "text-ink-2 hover:text-ink"
            )}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 40 }}
                className="absolute inset-0 rounded-[6px] bg-surface shadow-card"
              />
            )}
            <span className="relative z-10 flex items-center justify-center gap-1.5">
              {item.label}
            </span>
          </button>
        );
      })}
    </div>
  );
}
