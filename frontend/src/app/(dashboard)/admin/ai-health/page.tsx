"use client";

import { api } from "@/lib/api";
import React, { useState, useEffect } from "react";
import {
  Server,
  Database,
  Cloud,
  Cpu,
  Zap,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Lock,
  Unlock,
  ShieldCheck,
  Activity,
  Sliders,
  History,
  GitBranch,
  ArrowRight,
  Shield,
  Layers
} from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { Rise } from "@/components/ui/motion";

interface ModelConfig {
  id: string;
  name: string;
  version: string;
  role: string;
  status: "ONLINE" | "STANDBY" | "DEGRADED";
  latency_ms: number;
  drift_index: number;
  vram_usage?: string;
  is_active: boolean;
}

interface AuditLogEntry {
  id: string;
  timestamp: string;
  officer: string;
  action: string;
  impact: string;
  verification_hash: string;
}

export default function AIHealthGovernanceDashboard() {
  const { token } = useAuthStore();
  const toast = useToast();
  const [loading, setLoading] = useState(false);

  const [models, setModels] = useState<ModelConfig[]>([
    {
      id: "groq-llama-3.3",
      name: "Groq Llama-3.3-70B-Versatile",
      version: "llama-3.3-70b-v",
      role: "Primary RAIC 6-Factor Consensus & Deep Threat Synthesis",
      status: "ONLINE",
      latency_ms: 42,
      drift_index: 0.03,
      is_active: true
    },
    {
      id: "qwen-2.5-vl",
      name: "Qwen 2.5-VL-7B-Instruct (Vision Core)",
      version: "qwen-vl-2.5-7b",
      role: "Counterfeit Note & Phishing Document Optical Deconstruction",
      status: "ONLINE",
      latency_ms: 184,
      drift_index: 0.04,
      vram_usage: "18.4 / 24 GB (NVIDIA A10G)",
      is_active: true
    },
    {
      id: "whisper-v3",
      name: "Whisper-large-v3 (Audio Forensics)",
      version: "whisper-v3-large-hi-en",
      role: "Voice Note & Deepfake Audio Acoustic Transcriber",
      status: "ONLINE",
      latency_ms: 142,
      drift_index: 0.01,
      is_active: true
    }
  ]);

  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([
    {
      id: "log-101",
      timestamp: "2026-07-15 12:44:02 UTC",
      officer: "nodal.delhi@cyberpolice.gov.in",
      action: "RLHF Weight Tuning (CASE-2026-8419)",
      impact: "+0.05 Qwen Vision Weight applied to 6-Factor Core",
      verification_hash: "0x89f4b1a8c92b..."
    },
    {
      id: "log-102",
      timestamp: "2026-07-14 18:20:11 UTC",
      officer: "admin@digitalrakshak.in",
      action: "Primary Engine Switch",
      impact: "Activated Gemini 3.1 Pro as primary 6-Factor reasoning tier",
      verification_hash: "0x44a1e902df1c..."
    },
    {
      id: "log-103",
      timestamp: "2026-07-12 09:15:40 UTC",
      officer: "rbi.currency@bankgrid.in",
      action: "Counterfeit Signature Calibration",
      impact: "Updated Grade B+ Super-note optical match threshold to 0.94",
      verification_hash: "0x33b82c19fa0e..."
    }
  ]);



  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-cyan-900/40 border border-cyan-500/40 text-cyan-400 shadow-xl flex items-center justify-center">
            <Cpu className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-white uppercase">
                AI Health & Model Governance Desk (`/admin/ai-health`)
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                Sprint 8 Governance Core
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Model Versioning & Drift Auditing</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400 font-semibold">Zero-Cloud Sovereign Enforce Ready</span>
            </p>
          </div>
        </div>
      </div>
      {/* Model Grid & Version Switcher */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wide flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" /> Active AI Inference Engines & Version Governance
          </h3>
          <span className="text-xs font-mono text-slate-400">Drift Threshold: 0.10 max</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
          {models.map((m) => (
            <div
              key={m.id}
              className={`p-4 rounded-xl border transition-all flex flex-col justify-between space-y-3 ${
                m.is_active
                  ? "bg-slate-900/90 border-cyan-500/50 shadow-xl"
                  : "bg-slate-950/60 border-slate-800 opacity-70"
              }`}
            >
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-black text-white truncate text-sm">{m.name}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      m.status === "ONLINE"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                        : "bg-amber-500/20 text-amber-400 border border-amber-500/40"
                    }`}
                  >
                    {m.status}
                  </span>
                </div>
                <div className="mt-1 text-[11px] text-cyan-300 font-bold">{m.version}</div>
                <p className="text-slate-400 text-[11px] mt-2 leading-relaxed">{m.role}</p>
              </div>

              <div className="pt-3 border-t border-slate-800 space-y-2">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-500">Avg Latency:</span>
                  <strong className="text-emerald-400">{m.latency_ms} ms</strong>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-500">Drift Index:</span>
                  <strong className={m.drift_index < 0.05 ? "text-emerald-400" : "text-amber-400"}>
                    {m.drift_index} ({m.drift_index < 0.05 ? "STABLE" : "MONITOR"})
                  </strong>
                </div>
                {m.vram_usage && (
                  <div className="flex justify-between text-[11px]">
                    <span className="text-slate-500">VRAM Load:</span>
                    <strong className="text-purple-300">{m.vram_usage}</strong>
                  </div>
                )}

              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model Drift & RLHF Audit Ledger */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4 font-mono text-xs">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-cyan-400" />
            <h3 className="font-bold text-white uppercase tracking-wide">
              Model Governance & RLHF Weight Tuning Audit Ledger
            </h3>
          </div>
          <span className="text-slate-400">Chronological Immutable Record</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] text-slate-500 uppercase tracking-wider">
                <th className="py-2.5 px-3">Timestamp (UTC)</th>
                <th className="py-2.5 px-3">Authorizing Officer</th>
                <th className="py-2.5 px-3">Governance Action</th>
                <th className="py-2.5 px-3">Model Matrix Impact</th>
                <th className="py-2.5 px-3 text-right">Verification Hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-slate-300">
              {auditLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-all">
                  <td className="py-3 px-3 text-slate-400 tabular-nums">{log.timestamp}</td>
                  <td className="py-3 px-3 font-semibold text-white">{log.officer}</td>
                  <td className="py-3 px-3 text-cyan-400 font-bold">{log.action}</td>
                  <td className="py-3 px-3 text-emerald-300">{log.impact}</td>
                  <td className="py-3 px-3 text-right text-slate-500 font-mono text-[10px] tabular-nums">
                    {log.verification_hash}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
