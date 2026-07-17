"use client";

import React, { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

const ALERT_ITEMS = [
  <span key="1" className="flex items-center gap-1.5">
    🛡 NATIONAL CYBER HELPLINE <span className="text-[#F59E0B] font-bold">1930</span>
  </span>,
  <span key="2">REPORT CYBER FRAUD IMMEDIATELY</span>,
  <span key="3" className="flex items-center gap-1.5 text-cyan-400 font-semibold tracking-wide">
    <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">
      🌐 cybercrime.gov.in
    </a>
  </span>,
  <span key="4">NEVER SHARE OTP</span>,
  <span key="5">VERIFY UPI REQUESTS</span>,
  <span key="6">REPORT WITHIN THE GOLDEN HOUR</span>,

  <span key="7" className="flex items-center gap-1.5">
    📞 CALL <span className="text-[#F59E0B] font-bold">1930</span> FOR IMMEDIATE ASSISTANCE
  </span>,
];

export function NationalAlertTicker() {
  const [mounted, setMounted] = useState(false);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="w-full bg-[#08131A] bg-surface relative overflow-hidden border-t border-b border-[#253540]/50 border-line/50 select-none z-20"
    >
      {/* Subtle vector grid texture */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(37,53,64,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(37,53,64,0.08)_1px,transparent_1px)] bg-[size:32px_32px] pointer-events-none" />

      {/* Injecting marquee animation keyframes dynamically */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes marquee-infinite {
          0% { transform: translate3d(0, 0, 0); }
          100% { transform: translate3d(-50%, 0, 0); }
        }
        .animate-marquee-infinite {
          animation: marquee-infinite 45s linear infinite;
        }
      `}} />

      {/* MOBILE SCREEN LAYOUT */}
      <div className="md:hidden w-full flex items-center justify-center py-3 px-4 relative z-10">
        <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#E7EEF3]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D9A3] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00D9A3]"></span>
          </span>
          <span className="tracking-wide">
            📞 National Cyber Helpline <span className="text-[#F59E0B] font-extrabold">1930</span>
          </span>
        </div>
      </div>

      {/* DESKTOP SCREEN LAYOUT */}
      <div className="hidden md:flex items-center w-full relative z-10">
        
        {/* Fixed LIVE Badge status */}
        <div className="flex items-center gap-2 px-5 py-3 bg-[#0C151B] border-r border-[#253540]/50 border-line/50 shrink-0 z-20 shadow-[4px_0_12px_rgba(0,0,0,0.5)]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00D9A3] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00D9A3]"></span>
          </span>
          <span className="text-[10px] uppercase tracking-widest font-extrabold text-[#E7EEF3] font-mono whitespace-nowrap">
            National Cyber Alert
          </span>
        </div>

        {/* Marquee Infinite Scrolling Track */}
        <div className="flex-1 overflow-hidden relative flex items-center py-3">
          <div 
            className={`flex whitespace-nowrap ${reducedMotion ? "" : "animate-marquee-infinite hover:[animation-play-state:paused]"}`}
            style={{ width: "max-content" }}
          >
            {/* Copy 1 */}
            <div className="flex items-center shrink-0">
              {ALERT_ITEMS.map((item, idx) => (
                <React.Fragment key={`set1-${idx}`}>
                  <span className="text-[11px] font-mono tracking-wider text-[#A7B4BD] font-medium uppercase flex items-center">
                    {item}
                  </span>
                  <span className="text-[#253540] mx-8 font-black select-none">•</span>
                </React.Fragment>
              ))}
            </div>

            {/* Copy 2 (Enables perfect seamless loop alignment) */}
            <div className="flex items-center shrink-0">
              {ALERT_ITEMS.map((item, idx) => (
                <React.Fragment key={`set2-${idx}`}>
                  <span className="text-[11px] font-mono tracking-wider text-[#A7B4BD] font-medium uppercase flex items-center">
                    {item}
                  </span>
                  <span className="text-[#253540] mx-8 font-black select-none">•</span>
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}