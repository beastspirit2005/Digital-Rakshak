"use client";

import { api } from "@/lib/api";
import { useState, useEffect } from "react";
import { Server, Database, Cloud, Cpu, Zap, RefreshCw, AlertTriangle, CheckCircle2 } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FormError } from "@/components/ui/field";
import { Skeleton } from "@/components/ui/skeleton";
import { Rise } from "@/components/ui/motion";

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

function ServiceStatus({ status }: { status: "up" | "down" }) {
  return status === "up" ? (
    <Badge tone="success">Operational</Badge>
  ) : (
    <Badge tone="danger">Down</Badge>
  );
}

function MetricRow({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-line last:border-0">
      <span className="text-sm text-ink-2">{label}</span>
      <span className="text-sm font-medium text-ink tabular">{value}</span>
    </div>
  );
}

function ServiceCard({
  icon: Icon,
  title,
  sub,
  service,
  children,
  index,
}: {
  icon: typeof Cpu;
  title: string;
  sub: string;
  service?: HealthService;
  children: React.ReactNode;
  index: number;
}) {
  return (
    <Rise index={index}>
      <Card className="p-6 h-full">
        <div className="flex justify-between items-start mb-5">
          <div className="p-2.5 bg-surface-2 rounded-control">
            <Icon className="w-5 h-5 text-ink-2" />
          </div>
          <ServiceStatus status={service?.status || "down"} />
        </div>
        <h3 className="font-display font-semibold text-base text-ink">{title}</h3>
        <p className="text-sm text-ink-2 mb-4">{sub}</p>
        <div>{children}</div>
        {service?.error && (
          <p className="text-xs text-danger mt-4 bg-danger-tint rounded-control px-3 py-2">
            {service.error}
          </p>
        )}
      </Card>
    </Rise>
  );
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
      setError(err.response?.data?.detail || "Health metrics couldn't be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchHealth();
    const interval = setInterval(() => {
      if (token) fetchHealth();
    }, 30000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (loading && !healthData) {
    return (
      <div className="space-y-6 pt-2">
        <PageHeader title="AI health" sub="Live telemetry for the inference stack." />
        <Skeleton className="h-24 rounded-card" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-64 rounded-card" />
          <Skeleton className="h-64 rounded-card" />
          <Skeleton className="h-64 rounded-card" />
        </div>
      </div>
    );
  }

  const aiService = healthData?.services?.ai;
  const dbService = healthData?.services?.postgres;
  const graphService = healthData?.services?.neo4j;
  const isCloud = healthData?.ai_mode === "groq";
  const healthy = healthData?.status === "healthy";

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="AI health"
          sub="Live telemetry for the inference stack, refreshed every 30 seconds."
          actions={
            <Button loading={loading} onClick={fetchHealth}>
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
          }
        />
      </Rise>

      <FormError>{error}</FormError>

      <Rise index={1}>
        <Card className="px-6 py-5 flex flex-col sm:flex-row gap-4 sm:items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="p-2.5 rounded-control bg-surface-2">
              {healthy ? (
                <CheckCircle2 className="w-5 h-5 text-success" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-warning" />
              )}
            </div>
            <div>
              <h2 className="font-display font-semibold text-base text-ink capitalize">
                System {healthData?.status}
              </h2>
              <p className="text-sm text-ink-2">
                {healthy
                  ? "All core services and inference endpoints are responding."
                  : "Some services are degraded — check the cards below."}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:text-right">
            {isCloud ? (
              <Cloud className="w-4 h-4 text-ink-2" />
            ) : (
              <Server className="w-4 h-4 text-ink-2" />
            )}
            <span className="text-sm font-medium text-ink">
              {isCloud ? "Cloud mode (Groq)" : "Offline mode (local models)"}
            </span>
          </div>
        </Card>
      </Rise>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ServiceCard
          icon={Cpu}
          title="Inference engine"
          sub="RAIC orchestrator and models"
          service={aiService}
          index={2}
        >
          <MetricRow label="Provider" value={aiService?.provider || "Unknown"} />
          <MetricRow label="Model" value={aiService?.model || "Unknown"} />
          <MetricRow
            label="Latency"
            value={aiService?.latency_ms ? `${aiService.latency_ms} ms` : "—"}
          />
        </ServiceCard>

        <ServiceCard
          icon={Zap}
          title="Intelligence graph"
          sub="Neo4j correlation engine"
          service={graphService}
          index={3}
        >
          <MetricRow
            label="Connection"
            value={graphService?.status === "up" ? "Connected" : "Disconnected"}
          />
          <MetricRow
            label="Latency"
            value={graphService?.latency_ms ? `${graphService.latency_ms} ms` : "—"}
          />
        </ServiceCard>

        <ServiceCard
          icon={Database}
          title="Primary database"
          sub="PostgreSQL persistence"
          service={dbService}
          index={4}
        >
          <MetricRow
            label="Connection"
            value={dbService?.status === "up" ? "Connected" : "Disconnected"}
          />
          <MetricRow
            label="Latency"
            value={dbService?.latency_ms ? `${dbService.latency_ms} ms` : "—"}
          />
        </ServiceCard>
      </div>
    </div>
  );
}
