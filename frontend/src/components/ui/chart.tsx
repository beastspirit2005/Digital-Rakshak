"use client";

import { useEffect, useState } from "react";

/**
 * Chart color contract: series colors come from the validated --chart-* tokens,
 * structure (grid/axis/tooltip) from the surface tokens. Never hex in a chart.
 */
export const chartSeries = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
  "var(--chart-4)", "var(--chart-5)", "var(--chart-6)",
  "var(--chart-7)", "var(--chart-8)", "var(--chart-9)",
  "var(--chart-10)", "var(--chart-11)", "var(--chart-12)"
];

export const axisTick = { fontSize: 12, fill: "var(--ink-3)" };

export const tooltipStyle: React.CSSProperties = {
  backgroundColor: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: "8px",
  boxShadow: "var(--shadow-card)",
  fontSize: "12px",
};

export const tooltipItemStyle: React.CSSProperties = { color: "var(--ink)" };
export const tooltipLabelStyle: React.CSSProperties = { color: "var(--ink-2)" };

/** Recharts draw-in should run once per page view, then stay put. */
export function useDrawInOnce() {
  const [animate, setAnimate] = useState(true);
  useEffect(() => {
    const id = setTimeout(() => setAnimate(false), 1600);
    return () => clearTimeout(id);
  }, []);
  return animate;
}

/** Colored square + label, used under donuts and beside line charts. */
export function ChartLegend({
  items,
}: {
  items: { label: string; color: string; value?: string }[];
}) {
  return (
    <div className="flex flex-wrap gap-x-5 gap-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-2 text-sm">
          <span
            className="w-2.5 h-2.5 rounded-[3px] shrink-0"
            style={{ backgroundColor: item.color }}
          />
          <span className="text-ink-2">{item.label}</span>
          {item.value && <span className="text-ink font-medium tabular">{item.value}</span>}
        </div>
      ))}
    </div>
  );
}
