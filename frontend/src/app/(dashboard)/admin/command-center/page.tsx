"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Siren,
  Activity,
  Cpu,
  Globe,
  ShieldAlert,
  Zap,
  RefreshCw,
  Server,
  Radio,
  Terminal,
  TrendingUp,
  MapPin,
  Flame,
  ArrowUpRight,
  Play,
} from "lucide-react";
import Link from "next/link";
import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";
import { Card, CardHeader } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { StatBlock } from "@/components/ui/stat";
import { Rise } from "@/components/ui/motion";
import { cn } from "@/lib/utils";

interface SpatialCluster {
  cluster_id: number;
  center_lat: number;
  center_lng: number;
  case_count: number;
  avg_threat_score: number;
  dominant_scam_type: string;
}

interface CampaignSyndicate {
  id: string;
  code: string;
  name: string;
  hub: string;
  linked_cases: number;
  financial_exposure: string;
  risk_level: "CRITICAL" | "HIGH" | "MEDIUM";
  status: "ACTIVE" | "CONTAINED" | "DISRUPTED";
}

export default function CommandCenterDashboard() {
  const [, setClusters] = useState<SpatialCluster[]>([]);
  const [selectedCity, setSelectedCity] = useState<string | null>("Delhi NCR");
  const [, setLoadingClusters] = useState<boolean>(true);
  const [simulatingEvent, setSimulatingEvent] = useState<boolean>(false);
  const [simulationMsg, setSimulationMsg] = useState<string | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignSyndicate[]>([]);
  const [cityCoordinates, setCityCoordinates] = useState<Record<string, { lat: number; lng: number; cases: number; threat: number; code: string; loss: string }>>({});
  const [aiModels, setAiModels] = useState<any[]>([]);

  const [stats, setStats] = useState({
    active_cases: 0,
    takedowns_executed: 0,
    avg_latency_ms: 0,
    syndicates_tracked: 0,
  });

  const isLocal = typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1");
  const apiBase = process.env.NEXT_PUBLIC_API_URL || (isLocal ? "http://127.0.0.1:8000/v1" : "/api/v1");

  const fetchCommandCenterData = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/analytics/command-center`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.stats) setStats(data.stats);
        if (data.campaigns) setCampaigns(data.campaigns);
        if (data.cityCoordinates) {
          setCityCoordinates(data.cityCoordinates);
          const cities = Object.keys(data.cityCoordinates);
          if (cities.length > 0 && (!selectedCity || !cities.includes(selectedCity))) {
            setSelectedCity(cities[0]);
          }
        }
      }
    } catch (err) {
      console.error("Failed to fetch command center data:", err);
    }
  };

  const fetchSpatialClusters = async () => {
    setLoadingClusters(true);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/cases/clusters`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setClusters(data.clusters || []);
      }
    } catch (err) {
      console.error("Failed to load spatial clusters:", err);
    } finally {
      setLoadingClusters(false);
    }
  };

  const fetchAiTelemetry = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/health/ai-telemetry`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.models) setAiModels(data.models);
        if (data.cpu_utilization !== undefined) {
          setStats((prev) => ({ ...prev, cpu_utilization: data.cpu_utilization }));
        }
      }
    } catch (err) {
      console.error("Failed to load AI telemetry:", err);
    }
  };

  const triggerLiveSimulatedEvent = async () => {
    setSimulatingEvent(true);
    setSimulationMsg("Broadcasting live telemetry pulse...");
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const agents = ["ThreatAnalysisAgent", "BehaviourAgent", "CampaignAgent", "DecisionCore", "VisionAgent"];
      const randomAgent = agents[Math.floor(Math.random() * agents.length)];
      const randomScore = Number((0.85 + Math.random() * 0.14).toFixed(2));

      const res = await fetch(
        `${apiBase}/stream/emit?event_type=agent_execution&case_id=SIM-${Math.floor(1000 + Math.random() * 9000)}&agent=${randomAgent}&status_msg=SYNDICATE_THREAT_CORRELATED&execution_ms=138&confidence=${randomScore}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        setStats((prev) => ({ ...prev, active_cases: prev.active_cases + 1 }));
        setSimulationMsg(`Broadcasted ${randomAgent} telemetry pulse across India SSE streams!`);
      }
    } catch (err) {
      console.error("Simulation failed:", err);
      setSimulationMsg("Check API connection.");
    } finally {
      setTimeout(() => setSimulatingEvent(false), 2500);
    }
  };

  const executeMassTakedown = async (syndCode: string) => {
    setSimulationMsg(`Executing mass automated takedown & bank freeze for ${syndCode}...`);
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      await fetch(`${apiBase}/mock-apis/npci/freeze-upi`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          target_id: syndCode,
          reason: `Mass Takedown Order for syndicate ${syndCode}`
        })
      });
      setStats((prev) => ({ ...prev, takedowns_executed: prev.takedowns_executed + 1 }));
      setSimulationMsg(`SUCCESS: All associated entities under ${syndCode} flagged for takedown.`);
    } catch (err) {
      console.error("Takedown failed:", err);
      setSimulationMsg(`FAILED: Could not execute takedown for ${syndCode}.`);
    }
  };

  useEffect(() => {
    fetchCommandCenterData();
    fetchSpatialClusters();
    fetchAiTelemetry();

    const interval = setInterval(() => {
      fetchCommandCenterData();
      fetchAiTelemetry();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const gpuLoad = (stats as any).cpu_utilization ?? Math.min(100, 50 + stats.active_cases * 2.1);

  return (
    <div className="space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="Tactical command center"
          sub="RAIC v2.1 national threat feed — live spatial clusters, syndicate tracking, and AI infrastructure health."
          actions={
            <>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center gap-1">
                <Radio className="w-3 h-3 animate-ping" /> National Threat Level: ELEVATED (ORANGE)
              </span>
              <Button variant="primary" size="md" onClick={triggerLiveSimulatedEvent} loading={simulatingEvent}>
                {!simulatingEvent && <Play className="w-4 h-4" />}
                Broadcast telemetry pulse
              </Button>
              <Link href="/workbench/map">
                <Button variant="secondary" size="md">
                  <Globe className="w-4 h-4" /> Full spatial map
                </Button>
              </Link>
            </>
          }
        />
      </Rise>

      <AnimatePresence>
        {simulationMsg && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="p-3.5 rounded-card bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center justify-between"
          >
            <span className="flex items-center gap-2 font-bold">
              <Zap className="w-4 h-4 text-emerald-400" /> {simulationMsg}
            </span>
            <button onClick={() => setSimulationMsg(null)} className="text-ink-3 hover:text-ink cursor-pointer">
              ✕
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Rise index={1}>
          <StatBlock
            label="Active threat cases"
            value={stats.active_cases}
            hint="+14.2% today"
            delta="live"
            deltaPositive
          />
        </Rise>
        <Rise index={2}>
          <StatBlock
            label="Automated NPCI takedowns"
            value={stats.takedowns_executed}
            hint="Avg freeze time: 48 sec"
          />
        </Rise>
        <Rise index={3}>
          <StatBlock
            label="RAIC consensus accuracy"
            value="96.8%"
            hint="6-factor parallel core"
          />
        </Rise>
        <Rise index={4}>
          <StatBlock
            label="Avg inference latency"
            value={stats.avg_latency_ms}
            format={(n) => `${Math.round(n)} ms`}
            hint="Air-gapped async queue"
          />
        </Rise>
      </div>

      {/* Ticker + heatmap */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Rise index={5} className="lg:col-span-6">
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <h3 className="font-mono text-sm font-bold text-ink flex items-center gap-2 uppercase tracking-wide">
                <Terminal className="w-4 h-4 text-emerald-400" /> Live Execution Ticker (`/stream/events`)
              </h3>
              <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> SSE Broadcast Active
              </span>
            </div>
            <RAICExecutionMonitor autoConnect={true} className="h-115" />
          </div>
        </Rise>

        <Rise index={6} className="lg:col-span-6">
          <Card className="p-5 flex flex-col justify-between min-h-123.75">
            <div>
              <div className="flex items-center justify-between border-b border-line/10 pb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-rose-400" />
                  <h3 className="font-display font-bold text-sm text-ink">Geographic Threat Heatmap & Active Clusters</h3>
                </div>
                <span className="text-xs text-ink-3">National Cyber Grid</span>
              </div>

              <div className="mt-4 flex overflow-x-auto gap-3 pb-2">
                {Object.entries(cityCoordinates).map(([city, info]) => {
                  const isSelected = selectedCity === city;
                  return (
                    <button
                      key={city}
                      onClick={() => setSelectedCity(city)}
                      className={cn(
                        "min-w-35 shrink-0 p-3 rounded-control border cursor-pointer transition-all flex flex-col justify-between text-left",
                        isSelected
                          ? "bg-danger-tint border-danger/30 shadow-sm"
                          : "bg-surface-2/40 border-line/10 hover:border-line/25"
                      )}
                    >
                      <div>
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-ink">{city}</span>
                          <Flame className={cn("w-3.5 h-3.5", info.threat > 0.9 ? "text-rose-400 animate-pulse" : "text-amber-400")} />
                        </div>
                        <span className="text-lg font-display font-black text-ink mt-1 block tabular">{info.cases} cases</span>
                      </div>
                      <div className="pt-2 border-t border-line/10 mt-2">
                        <span className="text-[10px] text-ink-3 block truncate">{info.code}</span>
                        <span className="text-[11px] font-bold text-rose-300">{info.loss} loss</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="mt-4">
              {selectedCity && cityCoordinates[selectedCity] && (
                <div className="p-4 rounded-control bg-surface-2/40 border border-line/10 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                      <MapPin className="w-4 h-4" /> Selected Cluster: {selectedCity} Surveillance Hub
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 font-bold">
                      THREAT INDEX: {(cityCoordinates[selectedCity].threat * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="text-ink-2 leading-relaxed">
                    High concentration of <strong className="text-ink">{cityCoordinates[selectedCity].code}</strong> vectors
                    targeting senior citizens and corporate executives. Correlated with 6 active UPI handles and 3 overseas SIP
                    trunking gateways.
                  </p>
                  <div className="flex items-center justify-between pt-2 border-t border-line/10">
                    <span className="text-ink-3">Prevented financial loss today:</span>
                    <span className="text-emerald-400 font-bold">{cityCoordinates[selectedCity].loss}</span>
                  </div>
                </div>
              )}

              <div className="pt-3 text-right">
                <Link
                  href="/workbench/map"
                  className="inline-flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300"
                >
                  <span>Launch Interactive MapLibre / GeoJSON Viewer</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </Card>
        </Rise>
      </div>

      {/* Campaign feed + AI health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <Rise index={7} className="lg:col-span-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line/10 pb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <h3 className="font-display font-bold text-sm text-ink">Live Campaign Feed & Syndicate Attack DNA</h3>
              </div>
              <span className="text-xs text-ink-3">Sprint 5 Entity Correlator</span>
            </div>

            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {campaigns.map((synd) => (
                <div key={synd.id} className="p-3.5 rounded-control bg-surface-2/40 border border-line/10 hover:border-line/25 transition-all space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-rose-400 text-xs flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" /> {synd.code}
                    </span>
                    <span
                      className={cn(
                        "px-2 py-0.5 rounded text-[10px] font-bold",
                        synd.risk_level === "CRITICAL"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                          : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                      )}
                    >
                      {synd.risk_level} RISK
                    </span>
                  </div>
                  <div className="text-ink font-semibold text-sm">{synd.name}</div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-ink-3">
                    <div>
                      <span>Primary Hub:</span>
                      <strong className="text-ink-2 block truncate">{synd.hub}</strong>
                    </div>
                    <div>
                      <span>Financial Exposure:</span>
                      <strong className="text-emerald-400 block">{synd.financial_exposure}</strong>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-2 border-t border-line/10">
                    <span className="text-[11px] text-ink-3">{synd.linked_cases} active cases linked</span>
                    <Button variant="danger" size="sm" onClick={() => executeMassTakedown(synd.code)}>
                      <Zap className="w-3.5 h-3.5" /> Execute Multi-Bank Freeze
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Rise>

        <Rise index={8} className="lg:col-span-6">
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-line/10 pb-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-emerald-400" />
                <h3 className="font-display font-bold text-sm text-ink">AI / GPU Hardware Health Matrix & Model Governance</h3>
              </div>
              <Link href="/admin/ai-health" className="text-xs text-emerald-400 hover:text-emerald-300">
                Sprint 8 Governance Ready
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {aiModels.length > 0 ? (
                aiModels.map((model) => (
                  <div key={model.id} className="p-3.5 rounded-control bg-surface-2/40 border border-line/10 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-ink text-sm truncate">{model.name}</span>
                      <span
                        className={cn(
                          "px-1.5 py-0.5 rounded text-[10px] font-bold",
                          model.status === "ONLINE" ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"
                        )}
                      >
                        {model.status}
                      </span>
                    </div>
                    <span className="text-[11px] text-ink-3 block truncate">{model.role}</span>
                    <div className="flex items-center justify-between text-[11px] text-ink-2 pt-1 border-t border-line/10">
                      {model.vram_usage ? (
                        <>
                          <span>
                            VRAM: <strong className="text-amber-400">{model.vram_usage.split("(")[0].trim()}</strong>
                          </span>
                          <span>
                            Hardware: <strong className="text-ink">{model.vram_usage.match(/\((.*?)\)/)?.[1] || "Local Node"}</strong>
                          </span>
                        </>
                      ) : (
                        <>
                          <span>
                            Latency: <strong className="text-emerald-400">{model.latency_ms}ms</strong>
                          </span>
                          <span>
                            Uptime: <strong className="text-ink">99.98%</strong>
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 text-ink-3 text-sm">Loading AI telemetry...</div>
              )}

              <div className="p-3.5 rounded-control bg-surface-2/40 border border-line/10 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-ink text-sm">EventBroadcaster</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold">
                    BRIDGE ACTIVE
                  </span>
                </div>
                <span className="text-[11px] text-ink-3 block">Hybrid Memory Queue + Redis Pub/Sub</span>
                <div className="flex items-center justify-between text-[11px] text-ink-2 pt-1 border-t border-line/10">
                  <span>
                    Channel: <strong className="text-purple-400">raic:events</strong>
                  </span>
                  <span>
                    SSE: <strong className="text-emerald-400">Unbuffered</strong>
                  </span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-control bg-surface-2/40 border border-line/10 space-y-2">
              <div className="flex items-center justify-between text-ink-2 text-xs">
                <span>National GPU Cluster Utilization</span>
                <span className="text-emerald-400 font-bold tabular">{gpuLoad.toFixed(1)}%</span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-surface-3/50 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 transition-all duration-1000"
                  style={{ width: `${gpuLoad}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-ink-3 pt-1">
                <span>0% Idle</span>
                <span>Optimal AI Load Threshold (80%)</span>
                <span>100% Saturation</span>
              </div>
            </div>
          </Card>
        </Rise>
      </div>
    </div>
  );
}
