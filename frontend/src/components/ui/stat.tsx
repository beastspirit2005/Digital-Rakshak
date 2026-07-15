"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Card } from "./card";

/** Number that ticks up once on first mount. Static under reduced motion. */
export function CountUp({
  value,
  duration = 700,
  format = (n: number) => Math.round(n).toLocaleString("en-IN"),
  className,
}: {
  value: number;
  duration?: number;
  format?: (n: number) => string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(reduced ? value : 0);
  const done = useRef(false);

  useEffect(() => {
    if (reduced || done.current) {
      setDisplay(value);
      return;
    }
    done.current = true;
    const start = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(value * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration, reduced]);

  return <span className={cn("tabular font-bold", className)}>{format(display)}</span>;
}

/**
 * Signature visual indicator: cyber-blue intelligence ring track
 * with high-trust percentage visualization.
 */
export function ConfidenceDial({
  value,
  size = 96,
  strokeWidth = 7,
  label,
  className,
}: {
  value: number; // 0..1
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
}) {
  const reduced = useReducedMotion();
  const [drawn, setDrawn] = useState(!!reduced);
  useEffect(() => {
    if (reduced) return;
    const id = requestAnimationFrame(() => setDrawn(true));
    return () => cancelAnimationFrame(id);
  }, [reduced]);

  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, value));
  const offset = drawn ? c * (1 - clamped) : c;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center shrink-0", className)}
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label ?? "Confidence"}: ${Math.round(clamped * 100)}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--surface-3)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          style={{ transition: reduced ? "none" : "stroke-dashoffset 650ms var(--ease-out)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display font-black text-ink tabular"
          style={{ fontSize: size / 4.2 }}
        >
          <CountUp value={clamped * 100} format={(n) => `${Math.round(n)}%`} />
        </span>
        {label && size >= 96 && <span className="text-[10px] uppercase font-mono font-bold text-ink-3 tracking-wider mt-1">{label}</span>}
      </div>
    </div>
  );
}

/** Compact stat card: clear visual separation, font-display, tabular. */
export function StatBlock({
  label,
  value,
  format,
  delta,
  deltaPositive,
  hint,
  className,
}: {
  label: string;
  value: number | string;
  format?: (n: number) => string;
  delta?: string;
  deltaPositive?: boolean;
  hint?: string;
  className?: string;
}) {
  return (
    <Card className={cn("px-6 py-5.5 relative", className)}>
      <div className="absolute top-0 left-0 w-full h-[3px] bg-accent/20" />
      <p className="text-xs uppercase tracking-wider font-bold text-ink-3">{label}</p>
      <p className="font-display font-black text-2xl text-ink mt-2.5 tracking-tight">
        {typeof value === "number" ? <CountUp value={value} format={format} /> : value}
      </p>
      {(delta || hint) && (
        <p className="text-xs mt-2.5 flex items-center gap-1.5">
          {delta && (
            <span className={cn("font-bold px-1.5 py-0.5 rounded text-[11px]", deltaPositive ? "bg-success/10 text-success" : "bg-warning/10 text-peach-text")}>
              {delta}
            </span>
          )}
          {hint && <span className="text-ink-3 font-medium">{hint}</span>}
        </p>
      )}
    </Card>
  );
}