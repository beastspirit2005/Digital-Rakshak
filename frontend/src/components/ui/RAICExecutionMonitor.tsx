"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, CheckCircle2, Loader2, AlertCircle, Cpu, ShieldAlert, Activity } from "lucide-react";

export interface RAICEvent {
  type: string;
  case_id: string;
  agent: string;
  status: string;
  execution_ms: number;
  confidence: number;
  timestamp: string;
  data?: any;
}

interface RAICExecutionMonitorProps {
  caseNumber?: string;
  onExecutionComplete?: (finalDecision?: any) => void;
  className?: string;
  autoConnect?: boolean;
}

export function RAICExecutionMonitor({
  caseNumber = "",
  onExecutionComplete,
  className = "",
  autoConnect = true,
}: RAICExecutionMonitorProps) {
  const [events, setEvents] = useState<RAICEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [activeAgent, setActiveAgent] = useState<string>("Waiting for SSE stream...");
  const [consensusScore, setConsensusScore] = useState<number>(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoConnect) return;

    let eventSource: EventSource | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/v1";
      eventSource = new EventSource(`${apiBase}/stream/events`);

      eventSource.addEventListener("connected", (e) => {
        setConnected(true);
        setActiveAgent("Stream Connected. Waiting for AI Core dispatch...");
      });

      eventSource.addEventListener("agent_execution", (e) => {
        try {
          const payload: RAICEvent = JSON.parse(e.data);
          if (caseNumber && payload.case_id && payload.case_id !== caseNumber) return;

          setEvents((prev) => [...prev, payload]);
          setActiveAgent(`${payload.agent}: ${payload.status}`);

          if (payload.confidence && payload.confidence > consensusScore) {
            setConsensusScore(payload.confidence);
          }

          if (payload.agent === "DecisionCore" && payload.status === "Completed") {
            if (onExecutionComplete) onExecutionComplete(payload.data);
          }
        } catch (err) {
          console.error("Error parsing SSE agent execution event:", err);
        }
      });

      eventSource.addEventListener("case_created", (e) => {
        try {
          const payload: RAICEvent = JSON.parse(e.data);
          if (caseNumber && payload.case_id && payload.case_id !== caseNumber) return;
          setEvents((prev) => [...prev, payload]);
          setActiveAgent(`Case #${payload.case_id} ingested into pipeline.`);
        } catch (err) {
          console.error("Error parsing case_created event:", err);
        }
      });

      eventSource.onerror = (err) => {
        setConnected(false);
        setActiveAgent("Connection interrupted. Reconnecting to EventBroadcaster...");
        eventSource?.close();
        // Vercel Serverless cuts off SSE randomly, force a new connection loop
        reconnectTimeout = setTimeout(connect, 2000);
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      eventSource?.close();
      setConnected(false);
    };
  }, [caseNumber, autoConnect]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  const getStatusBadge = (status: string) => {
    if (status === "Completed" || status.includes("Verified")) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Completed
        </span>
      );
    }
    if (status.includes("Running") || status.includes("Extracting") || status.includes("Transcribing")) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-400" /> Running...
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/15 text-slate-400 border border-slate-500/30">
        <Activity className="w-3.5 h-3.5 text-slate-400" /> {status}
      </span>
    );
  };

  return (
    <div className={`rounded-xl border border-slate-800 bg-slate-950/90 shadow-2xl overflow-hidden ${className}`}>
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-gradient-to-r from-slate-900 to-slate-950">
        <div className="flex items-center gap-2.5">
          <div className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
            <span className={`w-2.5 h-2.5 rounded-full ${connected ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`} />
          </div>
          <Cpu className="w-4 h-4 text-emerald-400 ml-1" />
          <span className="text-xs font-mono font-bold text-slate-200 tracking-wider uppercase">
            RAIC Real-Time Execution Monitor
          </span>
          {caseNumber && (
            <span className="ml-2 px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300">
              Case #{caseNumber}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <span className="text-[10px] font-mono text-slate-400 block uppercase tracking-wider">RAIC Consensus</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              {(consensusScore * 100).toFixed(1)}%
            </span>
          </div>
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-500 animate-ping" : "bg-rose-500"}`} />
        </div>
      </div>

      {/* Active Ticker status */}
      <div className="px-4 py-2 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-300">
        <div className="flex items-center gap-2 truncate">
          <span className="text-emerald-400 font-bold select-none">{">>"}</span>
          <span className="truncate">{activeAgent}</span>
        </div>
        <span className="text-[10px] text-slate-500 select-none">Live SSE (`/stream/events`)</span>
      </div>

      {/* Event List / Logs */}
      <div
        ref={scrollRef}
        className="p-4 max-h-80 overflow-y-auto space-y-2.5 font-mono text-xs scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-transparent"
      >
        {events.length === 0 ? (
          <div className="py-8 text-center text-slate-500 flex flex-col items-center gap-2">
            <Loader2 className="w-6 h-6 animate-spin text-emerald-500/50" />
            <p className="text-xs">Listening for RAIC agent executions...</p>
            <p className="text-[10px] text-slate-600">Subscribed to real-time FastAPI Server-Sent Events</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((ev, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="p-3 rounded-lg bg-slate-900/80 border border-slate-800/80 flex items-center justify-between gap-3 hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">{ev.agent}</span>
                      {ev.execution_ms > 0 && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                          {ev.execution_ms}ms
                        </span>
                      )}
                    </div>
                    {ev.data && ev.data.message && (
                      <p className="text-[11px] text-slate-400 mt-0.5 truncate">{ev.data.message}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  {ev.confidence > 0 && (
                    <span className="text-xs font-bold text-emerald-400">
                      {(ev.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                  {getStatusBadge(ev.status)}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}
      </div>

      {/* Footer info */}
      <div className="px-4 py-2 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-[11px] text-slate-500 font-mono">
        <div className="flex items-center gap-2">
          <span>Connection Status:</span>
          <span className={connected ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
            {connected ? "LIVE (SSE Active)" : "DISCONNECTED"}
          </span>
        </div>
        <span>Digital Rakshak v2.1 Engine</span>
      </div>
    </div>
  );
}
