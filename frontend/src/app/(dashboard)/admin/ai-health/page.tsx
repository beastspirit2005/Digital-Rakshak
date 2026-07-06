"use client";

import { api } from "@/lib/api";
import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Loader2, Server, Database, Cloud, Zap, Cpu, Activity, AlertTriangle } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";

interface HealthService {
  status: "up" | "down";
  latency_ms?: number;
  provider?: string;
  model?: string;
  error?: string;
}

interface HealthData {
  status: "healthy" | "degraded" | "critical";
  timestamp: number;
  ai_mode?: string;
  services: {
    postgres?: HealthService;
    neo4j?: HealthService;
    ai?: HealthService;
  };
}

export default function AIHealthDashboard() {
  const [healthData, setHealthData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { token } = useAuthStore();

  const fetchHealth = async () => {
    try {
      setLoading(true);
      const response = await axios.get(api("/health"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      setHealthData(response.data);
      setError("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch AI health metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchHealth();
    // Poll every 30 seconds
    const interval = setInterval(() => {
      if (token) fetchHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [token]);

  if (loading && !healthData) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const aiService = healthData?.services?.ai;
  const dbService = healthData?.services?.postgres;
  const graphService = healthData?.services?.neo4j;

  const isCloud = healthData?.ai_mode === "groq";

  return (
    <div className="max-w-6xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-primary to-blue-500">
            AI Infrastructure Health
          </h1>
          <p className="text-muted-foreground mt-1">Real-time telemetry and orchestrator status monitoring.</p>
        </div>
        <button
          onClick={fetchHealth}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 bg-primary/10 text-primary border border-primary/20 rounded-xl hover:bg-primary/20 transition-all font-medium"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
          Refresh Metrics
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 text-red-600 dark:text-red-400 p-4 rounded-xl flex items-center gap-3 text-sm border border-red-500/20">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Global Status Banner */}
      <div className={`p-6 rounded-2xl border flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between ${
        healthData?.status === "healthy" ? "bg-emerald-500/10 border-emerald-500/20" : 
        healthData?.status === "degraded" ? "bg-orange-500/10 border-orange-500/20" : 
        "bg-red-500/10 border-red-500/20"
      }`}>
        <div className="flex items-center gap-4">
          <div className={`p-3 rounded-xl ${
            healthData?.status === "healthy" ? "bg-emerald-500/20 text-emerald-500" : 
            healthData?.status === "degraded" ? "bg-orange-500/20 text-orange-500" : 
            "bg-red-500/20 text-red-500"
          }`}>
            {healthData?.status === "healthy" ? <CheckCircle2 className="w-6 h-6" /> : <AlertTriangle className="w-6 h-6" />}
          </div>
          <div>
            <h2 className="text-lg font-bold capitalize">System {healthData?.status}</h2>
            <p className="text-sm opacity-80">
              {healthData?.status === "healthy" ? "All core services and inference endpoints are operational." : "Some services are experiencing degradation."}
            </p>
          </div>
        </div>
        <div className="sm:text-right">
          <div className="text-xs uppercase tracking-wider opacity-60 font-semibold mb-1">Architecture Mode</div>
          <div className="flex items-center gap-2 sm:justify-end">
            {isCloud ? <Cloud className="w-5 h-5 text-blue-500" /> : <Server className="w-5 h-5 text-emerald-500" />}
            <span className="font-bold text-lg">{isCloud ? "Cloud Mode (Groq)" : "Offline Mode (Qwen)"}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Inference Engine Card */}
        <div className="glass-panel p-6 rounded-2xl border border-border relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -z-10 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-6">
            <div className="p-3 bg-primary/10 text-primary rounded-xl">
              <Cpu className="w-6 h-6" />
            </div>
            <StatusBadge status={aiService?.status || "down"} />
          </div>
          <h3 className="text-xl font-bold mb-1">Inference Engine</h3>
          <p className="text-sm text-muted-foreground mb-4">RAIC Orchestrator & Models</p>
          
          <div className="space-y-3">
            <MetricRow label="Provider" value={aiService?.provider || "Unknown"} />
            <MetricRow label="Active Model" value={aiService?.model || "Unknown"} />
            <MetricRow label="Latency" value={aiService?.latency_ms ? `${aiService.latency_ms}ms` : "—"} highlight={aiService?.latency_ms ? aiService.latency_ms < 500 : false} />
          </div>
          {aiService?.error && <p className="text-xs text-red-500 mt-4 bg-red-500/10 p-2 rounded-lg">{aiService.error}</p>}
        </div>

        {/* Knowledge Graph Card */}
        <div className="glass-panel p-6 rounded-2xl border border-border relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/5 rounded-bl-full -z-10 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-6">
            <div className="p-3 bg-purple-500/10 text-purple-500 rounded-xl">
              <Zap className="w-6 h-6" />
            </div>
            <StatusBadge status={graphService?.status || "down"} />
          </div>
          <h3 className="text-xl font-bold mb-1">Intelligence Graph</h3>
          <p className="text-sm text-muted-foreground mb-4">Neo4j Correlation Engine</p>
          
          <div className="space-y-3">
            <MetricRow label="Status" value={graphService?.status === "up" ? "Connected" : "Disconnected"} />
            <MetricRow label="Latency" value={graphService?.latency_ms ? `${graphService.latency_ms}ms` : "—"} />
          </div>
          {graphService?.error && <p className="text-xs text-red-500 mt-4 bg-red-500/10 p-2 rounded-lg">{graphService.error}</p>}
        </div>

        {/* Database Card */}
        <div className="glass-panel p-6 rounded-2xl border border-border relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-bl-full -z-10 transition-transform group-hover:scale-110" />
          <div className="flex justify-between items-start mb-6">
            <div className="p-3 bg-emerald-500/10 text-emerald-500 rounded-xl">
              <Database className="w-6 h-6" />
            </div>
            <StatusBadge status={dbService?.status || "down"} />
          </div>
          <h3 className="text-xl font-bold mb-1">Primary Database</h3>
          <p className="text-sm text-muted-foreground mb-4">PostgreSQL Persistence Layer</p>
          
          <div className="space-y-3">
            <MetricRow label="Status" value={dbService?.status === "up" ? "Connected" : "Disconnected"} />
            <MetricRow label="Latency" value={dbService?.latency_ms ? `${dbService.latency_ms}ms` : "—"} />
          </div>
          {dbService?.error && <p className="text-xs text-red-500 mt-4 bg-red-500/10 p-2 rounded-lg">{dbService.error}</p>}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: "up" | "down" }) {
  if (status === "up") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
        Operational
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-500 border border-red-500/20">
      <XCircle className="w-3 h-3" />
      Down
    </span>
  );
}

function MetricRow({ label, value, highlight = false }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <span className={`text-sm font-medium ${highlight ? "text-emerald-500" : "text-foreground"}`}>
        {value}
      </span>
    </div>
  );
}
