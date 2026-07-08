import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  render: (row: T) => React.ReactNode;
  align?: "left" | "right";
  /** where this field lands in the mobile card: title row, meta rows, or dropped */
  mobile?: "title" | "trailing" | "meta" | "hide";
}

/**
 * Desktop: a real table with a sticky header and comfortable rows.
 * Mobile (<sm): stacked list cards — primary data never scrolls sideways.
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
        className="hidden sm:block overflow-y-auto rounded-b-card"
        style={maxHeight ? { maxHeight } : undefined}
      >
        <table className="w-full text-sm text-left">
          <thead className="sticky top-0 z-10 bg-surface-2 text-ink-2">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "px-6 py-3 text-xs font-medium whitespace-nowrap",
                    col.align === "right" && "text-right"
                  )}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                className={cn(
                  "transition-colors duration-150",
                  onRowClick && "cursor-pointer hover:bg-surface-2/60"
                )}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={cn("px-6 py-4", col.align === "right" && "text-right")}
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
      <ul className="sm:hidden divide-y divide-line">
        {rows.map((row) => (
          <li key={rowKey(row)}>
            <div
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={cn("px-4 py-4 space-y-2.5", onRowClick && "active:bg-surface-2/60")}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-medium text-ink min-w-0">{titleCol.render(row)}</div>
                {trailingCol && <div className="shrink-0">{trailingCol.render(row)}</div>}
              </div>
              {metaCols.length > 0 && (
                <dl className="space-y-1.5">
                  {metaCols.map((col) => (
                    <div key={col.key} className="flex items-center justify-between gap-3 text-sm">
                      <dt className="text-ink-3 text-xs">{col.header}</dt>
                      <dd className="text-ink-2 text-right min-w-0">{col.render(row)}</dd>
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
