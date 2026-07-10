"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Loader2 } from "lucide-react";

interface TerminalOverlayProps {
  open: boolean;
  logs: string[];
}

/**
 * Retro green-on-black terminal overlay.
 * Shows AI processing logs during scam report analysis.
 */
export function TerminalOverlay({ open, logs }: TerminalOverlayProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <motion.div
            initial={{ scale: 0.92, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.92, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="terminal-window max-w-xl w-full rounded-xl overflow-hidden shadow-2xl border border-[#1a3a1a]"
          >
            {/* Title bar */}
            <div className="terminal-titlebar flex items-center gap-2.5 px-4 py-2.5"
                 style={{ background: "linear-gradient(135deg, #0a1a0a 0%, #0d250d 100%)" }}>
              {/* Traffic light dots */}
              <div className="flex gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              </div>
              <Terminal className="w-3.5 h-3.5 text-[#00ff41] ml-2" />
              <span className="text-xs font-mono font-semibold text-[#00ff41] tracking-wider uppercase">
                Rakshak AI Core
              </span>
              <Loader2 className="w-3 h-3 animate-spin text-[#00ff41]/60 ml-auto" />
            </div>

            {/* Terminal body */}
            <div
              className="p-5 h-72 overflow-y-auto font-mono text-xs leading-relaxed space-y-1.5"
              style={{
                background: "linear-gradient(180deg, #050d05 0%, #0a0f0a 100%)",
                textShadow: "0 0 8px rgba(0, 255, 65, 0.3)",
              }}
            >
              {logs.map((log, index) => (
                <motion.p
                  key={index}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.15, delay: index * 0.03 }}
                  className={
                    log.includes("[SUCCESS]")
                      ? "text-[#00ff41] font-bold"
                      : log.includes("[ERROR]") || log.includes("[FAIL]")
                        ? "text-[#ff4444]"
                        : "text-[#00cc33]"
                  }
                >
                  <span className="text-[#00ff41]/40 mr-2 select-none">{">"}</span>
                  {log}
                </motion.p>
              ))}
              <p className="text-[#00ff41] animate-pulse select-none">▋</p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
