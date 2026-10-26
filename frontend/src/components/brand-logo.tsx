"use client";

import React from "react";

export interface BrandLogoProps {
  size?: number;
  variant?: "shield" | "horizontal";
  className?: string;
  glow?: boolean;
}

export function BrandLogo({
  size = 32,
  variant = "shield",
  className = "",
  glow = false,
}: BrandLogoProps) {
  if (variant === "horizontal") {
    // 520x120 aspect ratio (~4.33)
    const height = size;
    const width = Math.round(size * 4.33);

    return (
      <svg
        width={width}
        height={height}
        viewBox="0 0 520 120"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`select-none ${className}`}
        aria-label="Digital Rakshak - National Cyber Defense"
        role="img"
      >
        <defs>
          <linearGradient id="bl-hz-saffron" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#FFA826" />
            <stop offset="50%" stopColor="#FF7A00" />
            <stop offset="100%" stopColor="#D95700" />
          </linearGradient>

          <linearGradient id="bl-hz-green" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00E699" />
            <stop offset="50%" stopColor="#00A859" />
            <stop offset="100%" stopColor="#007038" />
          </linearGradient>

          <linearGradient id="bl-hz-inner" x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" stopColor="#0E1B26" />
            <stop offset="100%" stopColor="#030608" />
          </linearGradient>

          <linearGradient id="bl-hz-text-gold" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FFA726" />
            <stop offset="100%" stopColor="#FF7000" />
          </linearGradient>
        </defs>

        {/* Shield Emblem */}
        <g transform="translate(10, 2) scale(0.48)">
          <path d="M 100 8 L 26 34 L 26 100 C 26 150, 60 195, 100 220 L 100 200 C 70 180, 44 140, 44 100 L 44 46 L 100 26 Z" fill="url(#bl-hz-saffron)" />
          <path d="M 100 8 L 174 34 L 174 100 C 174 150, 140 195, 100 220 L 100 200 C 130 180, 156 140, 156 100 L 156 46 L 100 26 Z" fill="url(#bl-hz-green)" />
          <path d="M 100 26 L 156 46 L 156 100 C 156 140, 130 180, 100 200 C 70 180, 44 140, 44 100 L 44 46 Z" fill="url(#bl-hz-inner)" />
          <path d="M 64 68 L 78 68 L 78 140 L 64 130 Z" fill="#FFFFFF" />
          <path d="M 78 68 L 126 68 C 138 68, 144 76, 144 88 C 144 100, 136 108, 124 108 L 78 108 Z" fill="#FFFFFF" />
          <path d="M 78 80 L 118 80 C 124 80, 128 84, 128 88 C 128 92, 124 96, 118 96 L 78 96 Z" fill="url(#bl-hz-inner)" />
          <path d="M 102 108 L 140 148 L 120 148 L 88 114 Z" fill="#FFFFFF" />
          <path d="M 46 88 C 62 106, 92 110, 154 98 C 132 104, 88 104, 52 92 Z" fill="#FF9933" />
          <path d="M 48 98 C 66 114, 96 118, 156 106 C 132 112, 90 112, 54 102 Z" fill="#FFFFFF" />
          <path d="M 52 108 C 70 122, 100 126, 158 114 C 134 120, 92 120, 58 112 Z" fill="#00D27F" />
        </g>

        {/* Text */}
        <g transform="translate(125, 0)">
          <text x="0" y="62" fontFamily="system-ui, -apple-system, sans-serif" fontWeight="900" fontSize="34" letterSpacing="2">
            <tspan fill="#FFFFFF">DIGITAL </tspan>
            <tspan fill="url(#bl-hz-text-gold)">RAKSHAK</tspan>
          </text>
          <line x1="0" y1="84" x2="45" y2="84" stroke="#FF9933" strokeWidth="2.5" strokeLinecap="round" />
          <text x="56" y="88" fill="#A7B4BD" fontFamily="ui-monospace, monospace" fontSize="12" fontWeight="700" letterSpacing="4">
            NATIONAL CYBER DEFENSE
          </text>
          <line x1="335" y1="84" x2="380" y2="84" stroke="#00D27F" strokeWidth="2.5" strokeLinecap="round" />
        </g>
      </svg>
    );
  }

  // Default Shield Emblem (viewBox 0 0 200 230, aspect ratio ~1:1.15)
  // To keep square bounding box intuitive for standard UI layouts (e.g. width=size, height=size):
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 200 230"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`select-none shrink-0 transition-transform ${glow ? "drop-shadow-[0_0_12px_rgba(245,158,11,0.35)]" : ""} ${className}`}
      aria-label="Digital Rakshak Emblem"
      role="img"
    >
      <defs>
        <linearGradient id="bl-saffron" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FFA826" />
          <stop offset="50%" stopColor="#FF7A00" />
          <stop offset="100%" stopColor="#D95700" />
        </linearGradient>

        <linearGradient id="bl-green" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00E699" />
          <stop offset="50%" stopColor="#00A859" />
          <stop offset="100%" stopColor="#007038" />
        </linearGradient>

        <linearGradient id="bl-apex" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#FFB300" />
          <stop offset="50%" stopColor="#FFF2A0" />
          <stop offset="100%" stopColor="#4EBA6F" />
        </linearGradient>

        <linearGradient id="bl-inner" x1="50%" y1="0%" x2="50%" y2="100%">
          <stop offset="0%" stopColor="#0E1B26" />
          <stop offset="60%" stopColor="#060C12" />
          <stop offset="100%" stopColor="#030608" />
        </linearGradient>

        <linearGradient id="bl-ribbon-saffron" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#FF9933" />
          <stop offset="100%" stopColor="#FF6B00" />
        </linearGradient>

        <linearGradient id="bl-ribbon-green" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#00D27F" />
          <stop offset="100%" stopColor="#008F4C" />
        </linearGradient>

        <filter id="bl-drop-shadow" x="-10%" y="-10%" width="120%" height="120%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000000" floodOpacity="0.5" />
        </filter>
      </defs>

      <g filter="url(#bl-drop-shadow)">
        {/* Left Saffron Facet */}
        <path
          d="M 100 8 L 26 34 L 26 100 C 26 150, 60 195, 100 220 L 100 200 C 70 180, 44 140, 44 100 L 44 46 L 100 26 Z"
          fill="url(#bl-saffron)"
        />

        {/* Right Green Facet */}
        <path
          d="M 100 8 L 174 34 L 174 100 C 174 150, 140 195, 100 220 L 100 200 C 130 180, 156 140, 156 100 L 156 46 L 100 26 Z"
          fill="url(#bl-green)"
        />

        {/* Center Ridge Seam */}
        <path d="M 100 8 L 100 26" stroke="url(#bl-apex)" strokeWidth="2.5" strokeLinecap="round" />
        <path d="M 100 200 L 100 220" stroke="#007038" strokeWidth="2.5" strokeLinecap="round" />

        {/* Inner Plate */}
        <path
          d="M 100 26 L 156 46 L 156 100 C 156 140, 130 180, 100 200 C 70 180, 44 140, 44 100 L 44 46 Z"
          fill="url(#bl-inner)"
        />

        {/* India Geography Watermark (Subtle) */}
        <path
          d="M 94 48 Q 102 44, 108 48 T 114 56 T 122 62 T 128 72 T 120 84 T 114 96 T 100 115 T 90 98 T 82 86 T 76 74 T 84 60 Z"
          fill="#1C2E3D"
          opacity="0.45"
        />

        {/* The 'R' Lettermark */}
        {/* Vertical Stem */}
        <path d="M 64 68 L 78 68 L 78 140 L 64 130 Z" fill="#FFFFFF" />

        {/* Top Loop */}
        <path d="M 78 68 L 126 68 C 138 68, 144 76, 144 88 C 144 100, 136 108, 124 108 L 78 108 Z" fill="#FFFFFF" />
        <path d="M 78 80 L 118 80 C 124 80, 128 84, 128 88 C 128 92, 124 96, 118 96 L 78 96 Z" fill="url(#bl-inner)" />

        {/* Lower Right Leg */}
        <path d="M 102 108 L 140 148 L 120 148 L 88 114 Z" fill="#FFFFFF" />

        {/* Tricolor Dynamic Swoosh Ribbons */}
        {/* Top Saffron Ribbon */}
        <path d="M 46 88 C 62 106, 92 110, 154 98 C 132 104, 88 104, 52 92 Z" fill="url(#bl-ribbon-saffron)" />

        {/* Middle White Ribbon */}
        <path d="M 48 98 C 66 114, 96 118, 156 106 C 132 112, 90 112, 54 102 Z" fill="#FFFFFF" />

        {/* Bottom Green Ribbon */}
        <path d="M 52 108 C 70 122, 100 126, 158 114 C 134 120, 92 120, 58 112 Z" fill="url(#bl-ribbon-green)" />
      </g>
    </svg>
  );
}
