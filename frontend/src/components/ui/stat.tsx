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

  return <span className={cn("tabular", className)}>{format(display)}</span>;
}

/**
 * The signature moment: a ring that draws in while its number ticks up.
 * Used large on dashboard heroes, small on case rows (RAIC confidence).
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
          style={{ transition: reduced ? "none" : "stroke-dashoffset 600ms var(--ease-out)" }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display font-semibold text-ink tabular"
          style={{ fontSize: size / 4.2 }}
        >
          <CountUp value={clamped * 100} format={(n) => `${Math.round(n)}%`} />
        </span>
        {label && size >= 96 && <span className="text-xs text-ink-2 mt-0.5">{label}</span>}
      </div>
    </div>
  );
}

/** Compact stat card: quiet label, big tabular figure, optional delta. */
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
    <Card className={cn("px-6 py-5", className)}>
      <p className="text-sm text-ink-2">{label}</p>
      <p className="font-display font-semibold text-xl text-ink mt-2 tracking-tight">
        {typeof value === "number" ? <CountUp value={value} format={format} /> : value}
      </p>
      {(delta || hint) && (
        <p className="text-xs mt-1.5">
          {delta && (
            <span className={deltaPositive ? "text-success" : "text-peach-text"}>{delta}</span>
          )}
          {hint && <span className="text-ink-3">{delta ? " · " : ""}{hint}</span>}
        </p>
      )}
    </Card>
  );
}
