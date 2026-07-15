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
    bg-[#16232B] border-[#263640]
    border
    ${
      compact
        ? "w-10 h-10 rounded-xl"
        : "w-16 h-16 rounded-[18px]"
    }
  `}
>
  <BrandLogo size={compact ? 25 : 38} />
</div>

      {!compact && (
        <div className="min-w-0">
          <div
            className={`
              font-display text-[28px] font-bold
              tracking-tight leading-none
              ${
                fixedDark
                  ? "text-[#E7EEF3]"
                  : "text-ink"
              }
            `}
          >
            Digital Rakshak
          </div>

          <div
            className={`
              mt-2 text-[12px] font-medium
              tracking-[0.22em] uppercase
              ${
                fixedDark
                  ? "text-[#8293AA]"
                  : "text-ink-3"
              }
            `}
          >
            Cyber Threat Intelligence for India
          </div>
        </div>
      )}
    </div>
  );
}