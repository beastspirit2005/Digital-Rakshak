import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  render: (row: T) => React.ReactNode;
  align?: "left" | "right";
  mobile?: "title" | "trailing" | "meta" | "hide";
}

/**
 * Desktop: high-contrast table header, refined spacing, subtle borders, font-mono identifiers.
 * Mobile (<sm): stacked list cards.
 */
export function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  maxHeight,
  className,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  maxHeight?: string;
  className?: string;
}) {
  const titleCol = columns.find((c) => c.mobile === "title") ?? columns[0];
  const trailingCol = columns.find((c) => c.mobile === "trailing");
  const metaCols = columns.filter(
    (c) => c !== titleCol && c !== trailingCol && c.mobile !== "hide"
  );

  return (
    <div className={className}>
      {/* desktop */}
      <div
        className="hidden sm:block overflow-y-auto rounded-b-card border border-line/10 shadow-sm"
        style={maxHeight ? { maxHeight } : undefined}
      >
        <table className="w-full text-sm text-left">
          <thead className="sticky top-0 z-10 bg-surface-2 text-ink-2 border-b border-line/10">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-6 py-3 text-xs font-bold uppercase tracking-[0.12em]",
                    col.align === "right" && "text-right"
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line/10 bg-surface">
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  "transition-colors duration-150",
                  onRowClick && "cursor-pointer hover:bg-accent/[0.03] active:bg-accent/[0.05]"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn(
                      "px-6 py-4.5 text-ink-2 font-medium",
                      col.align === "right" && "text-right",
                      col.key.toLowerCase().includes("id") && "font-mono text-xs font-semibold text-ink"
                    )}
                  >
                    {col.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* mobile */}
      <ul className="sm:hidden divide-y divide-line/15">
        {rows.map((row) => (
          <li key={rowKey(row)}>
            <div
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn("px-5 py-5 space-y-3", onRowClick && "active:bg-surface-3/50 cursor-pointer")}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-bold text-ink min-w-0">{titleCol.render(row)}</div>
                {trailingCol && <div className="shrink-0">{trailingCol.render(row)}</div>}
              </div>
              {metaCols.length > 0 && (
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 pt-2 border-t border-line/5">
                  {metaCols.map((col) => (
                    <div key={col.key} className="flex flex-col gap-0.5">
                      <dt className="text-ink-3 text-[10px] uppercase font-bold tracking-wider">{col.header}</dt>
                      <dd className="text-xs text-ink-2 font-semibold min-w-0">{col.render(row)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}