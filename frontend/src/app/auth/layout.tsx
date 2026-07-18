import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";
import { BrandIdentity } from "@/components/brand-identity";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
   <div className="min-h-screen bg-background dark:bg-[#08131A] relative flex flex-col overflow-x-hidden selection:bg-[#F59E0B] selection:text-[#020617] text-foreground">
      {/* LAYER 1: Dark mode aligned with landing page nav header color (#08131A) */}

      {/* LAYER 2: Subtle cyber grid */}
      <div className="absolute inset-0 bg-cyber-grid opacity-4 pointer-events-none z-0" />

      {/* LAYER 3: Amber radial glow from left side */}
      <div className="absolute top-[15%] left-[-15%] w-[60%] h-[60%] rounded-full bg-[#F59E0B]/08 blur-[130px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: "8s" }} />

      {/* LAYER 4: Orange radial glow from right side */}
      <div className="absolute bottom-[15%] right-[-15%] w-[60%] h-[60%] rounded-full bg-[#F59E0B]/08 blur-[130px] pointer-events-none z-0 animate-pulse" style={{ animationDuration: "10s" }} />

      {/* LAYER 5: Cybersecurity illustration behind the card */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-0 select-none overflow-hidden">
        <svg className="w-[90%] max-w-[950px] h-auto aspect-square text-ink-3/40 opacity-[0.12]" viewBox="0 0 800 800" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Radar grids */}
          <g stroke="currentColor" strokeWidth="1" strokeDasharray="3 3">
            <circle cx="400" cy="400" r="320" opacity="0.3" />
            <circle cx="400" cy="400" r="240" opacity="0.2" />
            <circle cx="400" cy="400" r="160" opacity="0.1" />
          </g>

          {/* National Shield Outline */}
          <path d="M 400 150 L 530 190 C 530 315, 470 415, 400 465 C 330 415, 270 315, 270 190 L 400 150 Z" stroke="currentColor" strokeWidth="1.5" className="animate-pulse" style={{ animationDuration: "6s" }} fill="none" opacity="0.25" />

          {/* Abstract India geographical outline indicator */}
          <path d="M 380 220 Q 395 200, 425 210 T 450 250 T 475 270 T 495 310 T 485 350 T 455 390 T 415 440 T 400 480 T 385 440 T 345 390 T 315 350 T 305 310 T 325 270 T 350 250 T 380 220 Z" stroke="#F59E0B" strokeWidth="1" strokeDasharray="6 3" fill="none" opacity="0.15" />

          {/* Security Circuit Connections */}
          <path d="M 400 80 L 400 150 M 400 465 L 400 550 M 150 400 L 270 400 M 530 400 L 650 400" stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
          <path d="M 220 220 L 290 290 M 580 220 L 510 290 M 220 580 L 290 510 M 580 580 L 510 510" stroke="currentColor" strokeWidth="1" opacity="0.3" />

          {/* Lock icon in the vector workspace */}
          <g transform="translate(375, 280)" stroke="#F59E0B" strokeWidth="2" fill="none" opacity="0.6">
            <rect x="5" y="20" width="40" height="32" rx="4" />
            <path d="M 12 20 L 12 12 A 12 12 0 0 1 38 20" />
            <circle cx="25" cy="33" r="3" fill="#F59E0B" />
          </g>

          {/* Network nodes */}
          <g fill="currentColor">
            <circle cx="290" cy="290" r="4" />
            <circle cx="510" cy="290" r="4" />
            <circle cx="270" cy="400" r="5" />
            <circle cx="530" cy="400" r="5" />
            <circle cx="400" cy="150" r="6" />
            <circle cx="400" cy="465" r="6" />
          </g>
        </svg>
      </div>

      {/* Top brand header */}
      <header className="relative w-full flex items-center justify-between px-6 md:px-12 py-5 z-20">
        <Link href="/" className="transition-transform duration-200 active:scale-[0.98]">
          <BrandIdentity/>
        </Link>
        <ThemeToggle />
      </header>

      {/* Centered Auth Card Container */}
      <main className="flex-1 relative z-10 flex items-center justify-center px-4 sm:px-6 py-10 md:py-14">
        <div className="w-full max-w-[540px] animate-slide-up">
          <div className="w-full rounded-[28px] p-6 sm:p-12 relative overflow-hidden glass-premium-card">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}