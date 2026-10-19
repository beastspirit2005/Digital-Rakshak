"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Loader2,
  CheckCircle2,
  CreditCard,
  Activity,
  Eye,
  Terminal,
  Cpu,
  Lock,
  Radio,
  Scan,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface LoadingStep {
  label: string;
  detail?: string;
}

export interface LoadingOverlayProps {
  open: boolean;
  title: string;
  subtitle?: string;
  steps?: (string | LoadingStep)[];
  currentStepIndex?: number;
  autoAdvance?: boolean;
  autoAdvanceIntervalMs?: number;
  variant?: "cyber" | "payment" | "bank" | "vision" | "terminal";
  fullscreen?: boolean;
  className?: string;
  badge?: string;
  onCancel?: () => void;
}

export function LoadingOverlay({
  open,
  title,
  subtitle,
  steps = [],
  currentStepIndex,
  autoAdvance = true,
  autoAdvanceIntervalMs = 1100,
  variant = "cyber",
  fullscreen = true,
  className,
  badge,
  onCancel,
}: LoadingOverlayProps) {
  const [internalStep, setInternalStep] = useState(0);

  // Reset internal step counter when opened
  useEffect(() => {
    if (open) {
      setInternalStep(0);
    }
  }, [open]);

  // Handle auto-advancing steps if currentStepIndex is not explicitly controlled
  useEffect(() => {
    if (!open || !autoAdvance || currentStepIndex !== undefined || steps.length <= 1) {
      return;
    }

    const interval = setInterval(() => {
      setInternalStep((prev) => {
        if (prev < steps.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, autoAdvanceIntervalMs);

    return () => clearInterval(interval);
  }, [open, autoAdvance, currentStepIndex, steps.length, autoAdvanceIntervalMs]);

  const activeIndex = currentStepIndex !== undefined ? currentStepIndex : internalStep;

  // Determine styling theme tokens based on variant
  const getTheme = () => {
    switch (variant) {
      case "payment":
        return {
          icon: ShieldCheck,
          ringColor: "border-amber-500/20 border-t-amber-500",
          glowColor: "bg-amber-500",
          iconColor: "text-amber-500",
          badgeStyle: "bg-amber-500/10 text-amber-500 border-amber-500/30",
          cardBorder: "border-amber-500/30",
          glowShadow: "shadow-[0_0_35px_rgba(245,158,11,0.15)]",
        };
      case "bank":
        return {
          icon: CreditCard,
          ringColor: "border-indigo-500/20 border-t-indigo-500",
          glowColor: "bg-indigo-500",
          iconColor: "text-indigo-500",
          badgeStyle: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
          cardBorder: "border-indigo-500/30",
          glowShadow: "shadow-[0_0_35px_rgba(99,102,241,0.15)]",
        };
      case "vision":
        return {
          icon: Eye,
          ringColor: "border-amber-600/20 border-t-amber-500",
          glowColor: "bg-amber-600",
          iconColor: "text-amber-500",
          badgeStyle: "bg-amber-500/10 text-amber-500 border-amber-500/30",
          cardBorder: "border-amber-500/30",
          glowShadow: "shadow-[0_0_35px_rgba(217,119,6,0.15)]",
        };
      case "terminal":
        return {
          icon: Terminal,
          ringColor: "border-emerald-500/30 border-t-emerald-400",
          glowColor: "bg-emerald-500",
          iconColor: "text-emerald-400",
          badgeStyle: "bg-emerald-950/60 text-emerald-400 border-emerald-500/40",
          cardBorder: "border-emerald-500/30",
          glowShadow: "shadow-[0_0_35px_rgba(16,185,129,0.18)]",
        };
      case "cyber":
      default:
        return {
          icon: ShieldAlert,
          ringColor: "border-emerald-500/20 border-t-emerald-500",
          glowColor: "bg-emerald-500",
          iconColor: "text-emerald-500",
          badgeStyle: "bg-emerald-500/10 text-emerald-500 border-emerald-500/30",
          cardBorder: "border-emerald-500/30",
          glowShadow: "shadow-[0_0_35px_rgba(16,185,129,0.15)]",
        };
    }
  };

  const theme = getTheme();
  const IconComponent = theme.icon;

  const content = (
    <motion.div
      initial={{ scale: 0.94, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.94, opacity: 0 }}
      transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
      className={cn(
        "relative w-full max-w-md bg-card/95 backdrop-blur-xl border rounded-2xl p-6 sm:p-8 flex flex-col items-center text-center",
        theme.cardBorder,
        theme.glowShadow,
        className
      )}
      role="status"
      aria-live="polite"
    >
      {/* Optional Badge */}
      {badge && (
        <span
          className={cn(
            "mb-4 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border",
            theme.badgeStyle
          )}
        >
          {badge}
        </span>
      )}

      {/* Animated Center Spinner Ring */}
      <div className="relative flex items-center justify-center w-20 h-20 mb-5">
        <div
          className={cn(
            "absolute inset-0 rounded-full border-4 animate-spin",
            theme.ringColor
          )}
          style={{ animationDuration: "1.2s" }}
        />
        <div
          className={cn(
            "absolute inset-2 rounded-full opacity-25 animate-pulse blur-md",
            theme.glowColor
          )}
        />
        <div className="relative z-10 flex items-center justify-center">
          <IconComponent className={cn("w-9 h-9 animate-pulse", theme.iconColor)} />
        </div>
      </div>

      {/* Title & Subtitle */}
      <h3 className="text-lg font-bold text-foreground tracking-tight">{title}</h3>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed max-w-sm">
          {subtitle}
        </p>
      )}

      {/* Multi-Stage Steps Progression */}
      {steps.length > 0 && (
        <div className="w-full mt-6 pt-5 border-t border-border/50 text-left space-y-2.5">
          {steps.map((rawStep, idx) => {
            const stepObj: LoadingStep =
              typeof rawStep === "string" ? { label: rawStep } : rawStep;
            const isCompleted = idx < activeIndex;
            const isCurrent = idx === activeIndex;

            return (
              <div
                key={idx}
                className={cn(
                  "flex items-start gap-3 text-xs transition-colors duration-200",
                  isCompleted
                    ? "text-emerald-500 font-medium"
                    : isCurrent
                    ? "text-foreground font-semibold"
                    : "text-muted-foreground/50 font-normal"
                )}
              >
                <div className="mt-0.5 shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 animate-in fade-in" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 animate-spin text-primary" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border border-muted-foreground/30 flex items-center justify-center">
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/30" />
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <p className="truncate leading-tight">{stepObj.label}</p>
                  {stepObj.detail && isCurrent && (
                    <p className="text-[10px] text-muted-foreground mt-0.5 leading-relaxed">
                      {stepObj.detail}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Cancel Action if supported */}
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="mt-5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Cancel operation
        </button>
      )}
    </motion.div>
  );

  return (
    <AnimatePresence>
      {open && (
        fullscreen ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md"
          >
            {content}
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 z-40 flex items-center justify-center p-4 bg-card/90 dark:bg-card/95 backdrop-blur-md rounded-2xl"
          >
            {content}
          </motion.div>
        )
      )}
    </AnimatePresence>
  );
}
