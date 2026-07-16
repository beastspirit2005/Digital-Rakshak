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

  const [models, setModels] = useState<ModelConfig[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        setLoading(true);
        const res = await axios.get(api("/health/ai-telemetry"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setModels(res.data.models);
        setAuditLogs(res.data.auditLogs);
      } catch (err) {
        toast("danger", "Failed to load AI telemetry.");
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchTelemetry();
      const interval = setInterval(fetchTelemetry, 15000); // Live refresh every 15s
      return () => clearInterval(interval);
    }
  }, [token]);



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
