  "use client";

  import { motion, useReducedMotion } from "framer-motion";
  import { cn } from "@/lib/utils";

  export interface TabItem {
    id: string;
    label: React.ReactNode;
  }

  /** Segmented control with premium indicator sliding animations. */
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
        className={cn("inline-flex p-1 rounded-control bg-surface-2 border border-line/10 gap-1", className)}
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
               "relative flex-1 min-h-[64px] px-4 py-2 rounded-control text-xs font-bold uppercase tracking-wider",
                "transition-colors duration-150 cursor-pointer select-none",
                active ? "text-ink" : "text-ink-3 hover:text-ink"
              )}
            >
              {active && (
                <motion.span
                  layoutId={layoutId}
                  transition={reduced ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 40 }}
                  className="absolute inset-0 rounded-control bg-surface shadow-card border border-line/10"
                />
              )}
              <span className="relative z-10 flex flex-col items-center justify-center text-center leading-tight">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    );
  }