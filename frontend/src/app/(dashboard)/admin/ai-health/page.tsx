"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import { Cpu, Layers, History, ShieldCheck } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";
import { Rise } from "@/components/ui/motion";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

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

const auditColumns: Column<AuditLogEntry>[] = [
  {
    key: "timestamp",
    header: "Timestamp (UTC)",
    mobile: "meta",
    render: (l) => <span className="font-mono text-xs text-ink-2 tabular">{l.timestamp}</span>,
  },
  {
    key: "officer",
    header: "Authorizing Officer",
    mobile: "title",
    render: (l) => <span className="font-semibold text-ink">{l.officer}</span>,
  },
  {
    key: "action",
    header: "Governance Action",
    render: (l) => <span className="text-cyan-400 font-bold">{l.action}</span>,
  },
  {
    key: "impact",
    header: "Model Matrix Impact",
    render: (l) => <span className="text-emerald-300">{l.impact}</span>,
  },
  {
    key: "verification_hash",
    header: "Verification Hash",
    align: "right",
    mobile: "trailing",
    render: (l) => <span className="font-mono text-[11px] text-ink-3 tabular">{l.verification_hash}</span>,
  },
];

export default function AIHealthGovernanceDashboard() {
  const { token } = useAuthStore();
  const toast = useToast();
  const [loading, setLoading] = useState(true);

  const [models, setModels] = useState<ModelConfig[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [environment, setEnvironment] = useState<"cloud" | "local">("local");

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        setLoading(true);
        const res = await axios.get(api("/health/ai-telemetry"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setModels(res.data.models);
        setAuditLogs(res.data.auditLogs);
        if (res.data.environment) setEnvironment(res.data.environment);
      } catch (err) {
        toast("danger", "Failed to load AI telemetry.");
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchTelemetry();
      const interval = setInterval(fetchTelemetry, 15000);
      return () => clearInterval(interval);
    }
  }, [token]);

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="AI Health & Model Governance Desk"
          sub={`Model Versioning & Drift Auditing — ${environment === "cloud" ? "Cloud Serverless Limits" : "Local Workstation Hardware"}.`}
          actions={
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5" /> Sprint 8 Governance Core
            </span>
          }
        />
      </Rise>

      <Rise index={1}>
        <div className="flex items-center justify-between px-1">
          <h3 className="font-display font-bold text-sm text-ink flex items-center gap-2">
            <Layers className="w-4 h-4 text-cyan-400" /> Active AI Inference Engines & Version Governance
          </h3>
          <span className="text-xs text-ink-3 font-medium">Drift Threshold: 0.10 max</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-3">
          {models.map((m) => (
            <Card
              key={m.id}
              className={m.is_active ? "px-4 py-4" : "px-4 py-4 opacity-60"}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-display font-bold text-ink text-sm truncate">{m.name}</span>
                <span
                  className={
                    m.status === "ONLINE"
                      ? "px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                      : "px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40"
                  }
                >
                  {m.status}
                </span>
              </div>
              <div className="mt-1 text-xs font-bold text-cyan-300">{m.version}</div>
              <p className="text-xs text-ink-2 mt-2 leading-relaxed">{m.role}</p>

              <div className="mt-3 pt-3 border-t border-line/10 space-y-1.5 text-xs">
                <div className="flex justify-between">
                  <span className="text-ink-3">Avg Latency:</span>
                  <strong className="text-emerald-400 tabular">{m.latency_ms} ms</strong>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-3">Drift Index:</span>
                  <strong className={m.drift_index < 0.05 ? "text-emerald-400 tabular" : "text-amber-400 tabular"}>
                    {m.drift_index} ({m.drift_index < 0.05 ? "STABLE" : "MONITOR"})
                  </strong>
                </div>
                {m.vram_usage && (
                  <div className="flex justify-between">
                    <span className="text-ink-3">VRAM Load:</span>
                    <strong className="text-purple-300 tabular">{m.vram_usage}</strong>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      </Rise>

      <Rise index={2}>
        <Card>
          <CardHeader
            title="Model Governance & RLHF Weight Tuning Audit Ledger"
            sub="Chronological Immutable Record"
            action={<History className="w-4 h-4 text-cyan-400" />}
          />
          {loading ? (
            <TableSkeleton rows={5} />
          ) : auditLogs.length === 0 ? (
            <EmptyState icon={Cpu} title="No audit entries yet" body="Governance actions on the model matrix will appear here." />
          ) : (
            <DataTable columns={auditColumns} rows={auditLogs} rowKey={(l) => l.id} />
          )}
        </Card>
      </Rise>
    </div>
  );
}
