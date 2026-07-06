import { cn } from "@/lib/utils";

export function Avatar({
  name,
  size = "md",
  className,
}: {
  name?: string | null;
  size?: "sm" | "md";
  className?: string;
}) {
  const initial = (name || "?").trim().charAt(0).toUpperCase();
  return (
    <div
      className={cn(
        "rounded-pill bg-surface-3 text-ink font-display font-semibold flex items-center justify-center select-none",
        size === "sm" ? "w-8 h-8 text-xs" : "w-9 h-9 text-sm",
        className
      )}
      aria-hidden
    >
      {initial}
    </div>
  );
}
