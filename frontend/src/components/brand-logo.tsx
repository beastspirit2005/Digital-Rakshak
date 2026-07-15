"use client";

import { Shield } from "lucide-react";

interface BrandLogoProps {
  size?: number;
  className?: string;
}

export function BrandLogo({
  size = 32,
  className = "",
}: BrandLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id="digital-rakshak-tricolor"
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0%" stopColor="#FF9933" />
          <stop offset="45%" stopColor="#F5F5F5" />
          <stop offset="55%" stopColor="#F5F5F5" />
          <stop offset="100%" stopColor="#138808" />
        </linearGradient>
      </defs>

      <Shield
        x={3}
        y={3}
        width={26}
        height={26}
        stroke="url(#digital-rakshak-tricolor)"
        strokeWidth={2.6}
      />
    </svg>
  );
}