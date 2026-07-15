import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-accent-ink hover:bg-accent-hover active:bg-accent-hover font-semibold shadow-md shadow-accent/15 border border-accent/25 hover:border-accent/40",
  secondary:
    "bg-surface-2 text-ink hover:bg-surface-3 active:bg-surface-3 border border-line/10 hover:border-line/25",
  ghost: "text-ink-2 hover:bg-surface-3/40 hover:text-ink active:bg-surface-3",
  danger: "bg-danger-tint text-danger hover:brightness-105 border border-danger/20 hover:border-danger/40",
};

const sizes: Record<Size, string> = {
  sm: "h-8.5 px-3.5 text-xs gap-1.5 rounded-control",
  md: "h-10 px-4.5 text-sm gap-2 rounded-control",
  lg: "h-11.5 px-6 text-base gap-2 rounded-control",
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "secondary", size = "md", loading, className, children, disabled, ...props },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center font-semibold",
        "transition-all duration-150 ease-out cursor-pointer select-none",
        "active:scale-[0.98] disabled:opacity-40 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
});