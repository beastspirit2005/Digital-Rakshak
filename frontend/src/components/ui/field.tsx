"use client";

import { forwardRef, useRef } from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const controlBase = cn(
  "relative z-10",
  "w-full rounded-control border border-line bg-surface px-3.5 text-sm text-ink",
  "placeholder:text-ink-3 transition-colors duration-150",
  "hover:border-ink-3 focus:border-accent-text focus:outline-none focus:ring-1 focus:ring-accent-text/30",
  "disabled:opacity-50 disabled:pointer-events-none"
);

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("block text-sm font-medium text-ink mb-1.5", className)} {...props} />;
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, ...props }, ref) {
    return <input ref={ref} className={cn(controlBase, "h-11", className)} {...props} />;
  }
);

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(controlBase, "py-2.5 resize-none", className)} {...props} />;
});

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, ...props }, ref) {
    return <select ref={ref} className={cn(controlBase, "h-11 appearance-none pr-8", className)} {...props} />;
  }
);

export function FormError({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return (
    <div
      role="alert"
      className="flex items-start gap-2 rounded-control border border-danger/20 bg-danger-tint px-3.5 py-3 text-sm text-danger"
    >
      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
      <p>{children}</p>
    </div>
  );
}

export function FormNotice({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
  className={cn(
    "rounded-control border border-success/20 bg-success-tint px-3.5 py-3 text-sm text-success",
    className
  )}
>
      {children}
    </div>
  );
}

export function OtpInput({
  value,
  onChange,
  length = 6,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  length?: number;
  id?: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const chars = Array.from({ length }, (_, i) => value[i] ?? "");
  const active = Math.min(value.length, length - 1);

  return (
    <div className="relative cursor-text" onClick={() => ref.current?.focus()}>
      <input
        ref={ref}
        id={id}
        inputMode="numeric"
        autoComplete="one-time-code"
        value={value}
        onChange={(e) => onChange(e.target.value.replace(/\D/g, "").slice(0, length))}
        className="absolute inset-0 opacity-0"
        aria-label="One-time password"
      />
      <div className="flex gap-2 justify-between" aria-hidden>
        {chars.map((c, i) => (
          <div
            key={i}
            className={cn(
              "h-13 flex-1 rounded-control border bg-surface flex items-center justify-center",
              "font-display text-lg tabular",
              i === active && value.length < length
                ? "border-accent-text ring-1 ring-accent-text/30"
                : c
                  ? "border-line text-ink"
                  : "border-line text-ink-3"
            )}
          >
            {c}
          </div>
        ))}
      </div>
    </div>
  );
}