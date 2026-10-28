"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface CaseStepperProps {
  status: string;
  className?: string;
}

export function normalizeStatus(status: string): string {
  return (status || "").toLowerCase().replace(/_/g, " ").trim();
}

export function getCaseStepIndex(status: string): number {
  const s = normalizeStatus(status);
  if (s === "resolved" || s === "closed" || s === "verified") return 4;
  if (s === "investigation completed" || s === "investigation_completed" || s === "completed") return 3;
  if (s === "investigating" || s === "under review" || s === "analyzing" || s === "escalated") return 2;
  if (s === "assigned") return 1;
  return 0; // submitted / pending / new
}

const steps = [
  { key: "submitted", label: "Submitted" },
  { key: "assigned", label: "Assigned" },
  { key: "investigating", label: "Investigating" },
  { key: "completed", label: "Completed" },
  { key: "resolved", label: "Resolved" },
];

export function CaseStepper({ status, className }: CaseStepperProps) {
  const currentIndex = getCaseStepIndex(status);
  const isResolvedCase = currentIndex === 4;

  return (
    <div className={cn("w-full overflow-x-auto py-2", className)}>
      <div className="flex items-center justify-between gap-2 min-w-max sm:min-w-0 w-full">
        {steps.map((step, idx) => {
          const isPast = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const isResolved = isCurrent && idx === 4;
          const isCompletedStep = isCurrent && idx === 3;

          return (
            <React.Fragment key={step.key}>
              {/* Step Pill / Node */}
              <div
                className={cn(
                  "flex items-center gap-1.5 shrink-0 transition-colors",
                  isResolved || isCompletedStep
                    ? "text-emerald-500 font-bold"
                    : isCurrent
                    ? "text-accent font-bold"
                    : isPast
                    ? isResolvedCase
                      ? "text-emerald-500/90 font-medium"
                      : "text-ink font-medium"
                    : "text-ink-3 font-normal"
                )}
              >
                <div
                  className={cn(
                    "w-4 h-4 rounded-full flex items-center justify-center border transition-all shrink-0",
                    isResolved || isCompletedStep
                      ? "border-emerald-500 bg-emerald-500/20 text-emerald-500 ring-2 ring-emerald-500/20"
                      : isCurrent
                      ? "border-accent bg-accent/20 text-accent ring-2 ring-accent/20"
                      : isPast
                      ? isResolvedCase
                        ? "border-emerald-500/60 bg-emerald-500/10 text-emerald-500"
                        : "border-accent/60 bg-accent/10 text-accent"
                      : "border-line bg-surface-2 text-ink-3"
                  )}
                >
                  {isResolved || isCompletedStep ? (
                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)] animate-pulse" />
                  ) : isCurrent ? (
                    <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
                  ) : isPast ? (
                    <div
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        isResolvedCase ? "bg-emerald-500/70" : "bg-accent/70"
                      )}
                    />
                  ) : (
                    <div className="w-1 h-1 rounded-full bg-line" />
                  )}
                </div>

                <span className="text-[11px] whitespace-nowrap capitalize">
                  {step.key === "completed" ? (
                    <>
                      <span className="hidden xl:inline">Investigation </span>Completed
                    </>
                  ) : (
                    step.label
                  )}
                </span>
              </div>

              {/* Connecting Connector Line */}
              {idx < steps.length - 1 && (
                <div
                  className={cn(
                    "h-0.5 flex-1 min-w-[14px] rounded-full transition-all",
                    idx < currentIndex
                      ? isResolvedCase
                        ? "bg-emerald-500"
                        : "bg-accent"
                      : "bg-line/40"
                  )}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}
