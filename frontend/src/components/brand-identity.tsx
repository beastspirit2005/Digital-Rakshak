"use client";

import { BrandLogo } from "@/components/brand-logo";

interface BrandIdentityProps {
  compact?: boolean;
  className?: string;
  fixedDark?: boolean;
}

export function BrandIdentity({
  compact = false,
  className = "",
  fixedDark = false,
}: BrandIdentityProps) {
  return (
    <div
      className={`flex items-center ${
        compact ? "gap-2.5" : "gap-4"
      } ${className}`}
    >
      <div
        className={`
          flex items-center justify-center shrink-0
          border transition-all duration-200
          ${
            fixedDark
              ? "bg-[#18181c] border-white/10 shadow-sm"
              : "bg-surface-2 border-line shadow-sm"
          }
          ${
            compact
              ? "w-10 h-10 rounded-xl"
              : "w-16 h-16 rounded-[18px]"
          }
        `}
      >
        <BrandLogo size={compact ? 26 : 42} glow={!compact} />
      </div>

      {!compact && (
        <div className="min-w-0">
          <div
            className={`
              font-display text-[26px] font-black
              tracking-tight leading-none flex items-center gap-1.5
              ${
                fixedDark
                  ? "text-[#E7EEF3]"
                  : "text-ink"
              }
            `}
          >
            <span>Digital</span>
            <span className="text-[#F59E0B]">Rakshak</span>
          </div>

          <div
            className={`
              mt-1.5 text-[11px] font-semibold
              tracking-[0.2em] uppercase font-mono flex items-center gap-2
              ${
                fixedDark
                  ? "text-[#8293AA]"
                  : "text-ink-3"
              }
            `}
          >
            <span>National Cyber Defense</span>
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#138808]" />
          </div>
        </div>
      )}
    </div>
  );
}
