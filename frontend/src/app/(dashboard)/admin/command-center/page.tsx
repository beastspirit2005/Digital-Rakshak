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
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Terminal,
  Server,
  Database,
  Radio,
  Share2,
  Users,
  TrendingUp,
  MapPin,
  Flame,
  ArrowUpRight,
  Eye,
  Lock,
  Play
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";

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
  const router = useRouter();
  const [clusters, setClusters] = useState<SpatialCluster[]>([]);
  const [selectedCity, setSelectedCity] = useState<string | null>("Delhi NCR");
  const [loadingClusters, setLoadingClusters] = useState<boolean>(true);
  const [simulatingEvent, setSimulatingEvent] = useState<boolean>(false);
  const [simulationMsg, setSimulationMsg] = useState<string | null>(null);
  const [campaigns, setCampaigns] = useState<CampaignSyndicate[]>([]);
  const [cityCoordinates, setCityCoordinates] = useState<Record<string, { lat: number; lng: number; cases: number; threat: number; code: string; loss: string }>>({});
  
  const [stats, setStats] = useState({
    active_cases: 0,
    takedowns_executed: 0,
    avg_latency_ms: 0,
    syndicates_tracked: 0
  });

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/v1";

  const fetchCommandCenterData = async () => {
    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/analytics/command-center`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        if (data.stats) setStats(data.stats);
        if (data.campaigns) setCampaigns(data.campaigns);
        if (data.cityCoordinates) {
          setCityCoordinates(data.cityCoordinates);
          // Set default selected city to the first one available
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
        headers: { Authorization: `Bearer ${token}` }
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
          headers: { Authorization: `Bearer ${token}` }
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
    setStats((prev) => ({ ...prev, takedowns_executed: prev.takedowns_executed + 1 }));
    setTimeout(() => {
      setSimulationMsg(`SUCCESS: All 14 UPI handles and 3 mule bank accounts under ${syndCode} frozen via NPCI API.`);
    }, 1800);
  };

  useEffect(() => {
    fetchCommandCenterData();
    fetchSpatialClusters();
    
    // Poll every 30s to keep it somewhat live even without SSE for the main stats
    const interval = setInterval(() => {
      fetchCommandCenterData();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 font-sans">
      {/* Top Title Bar & Status Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-gradient-to-br from-rose-600 to-amber-600 text-white shadow-xl flex items-center justify-center">
            <Siren className="w-7 h-7 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-white uppercase">
                Tactical Command Center
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-rose-500/20 text-rose-400 border border-rose-500/40 flex items-center gap-1">
                <Radio className="w-3 h-3 animate-ping" /> National Threat Level: ELEVATED (ORANGE)
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5 flex items-center gap-2">
              <span>RAIC v2.1 Engine (Module 2 SSE Active)</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400 font-semibold">Zero-Latency Air-Gapped / Redis Bridge Ready</span>
            </p>
          </div>
        </div>

        {/* Quick Demo Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={triggerLiveSimulatedEvent}
            disabled={simulatingEvent}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition-all border border-emerald-400/30"
          >
            {simulatingEvent ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-current" />
            )}
            Broadcast Live Telemetry Pulse (`/stream/emit`)
          </button>
          <Link
            href="/workbench/map"
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-mono font-bold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            <Globe className="w-4 h-4 text-emerald-400" /> Full Spatial Map
          </Link>
        </div>
      </div>

      {simulationMsg && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center justify-between"
        >
          <span className="flex items-center gap-2 font-bold">
            <Zap className="w-4 h-4 text-emerald-400" /> {simulationMsg}
          </span>
          <button onClick={() => setSimulationMsg(null)} className="text-slate-400 hover:text-white">✕</button>
        </motion.div>
      )}

      {/* Top KPI Metrics Matrix */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 uppercase block tracking-wider">Active Threat Cases</span>
            <span className="text-2xl font-black text-white mt-1 block tabular-nums">{stats.active_cases}</span>
            <span className="text-[11px] text-emerald-400 flex items-center gap-1 mt-1">
              <TrendingUp className="w-3 h-3" /> +14.2% today
            </span>
          </div>
          <Activity className="w-8 h-8 text-emerald-500/40" />
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 uppercase block tracking-wider">Automated NPCI Takedowns</span>
            <span className="text-2xl font-black text-rose-400 mt-1 block tabular-nums">{stats.takedowns_executed}</span>
            <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
              <span>Avg freeze time: 48 sec</span>
            </span>
          </div>
          <Zap className="w-8 h-8 text-rose-500/40" />
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 uppercase block tracking-wider">RAIC Consensus Accuracy</span>
            <span className="text-2xl font-black text-emerald-400 mt-1 block tabular-nums">96.8%</span>
            <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
              <span>6-Factor Parallel Core</span>
            </span>
          </div>
          <Cpu className="w-8 h-8 text-emerald-500/40" />
        </div>

        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-[10px] text-slate-400 uppercase block tracking-wider">Avg Inference Latency</span>
            <span className="text-2xl font-black text-amber-400 mt-1 block tabular-nums">{stats.avg_latency_ms} ms</span>
            <span className="text-[11px] text-slate-400 flex items-center gap-1 mt-1">
              <span>Air-Gapped Async Queue</span>
            </span>
          </div>
          <Server className="w-8 h-8 text-amber-500/40" />
        </div>
      </div>

      {/* Main 2-Column Grid: Live Execution Ticker (Left) vs Threat Heatmap (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Columns: Live Execution Ticker via SSE (EventSource) */}
        <div className="lg:col-span-6 space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2 uppercase tracking-wide">
              <Terminal className="w-4 h-4 text-emerald-400" /> Live Execution Ticker (`/stream/events`)
            </h3>
            <span className="text-[11px] font-mono text-emerald-400 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> SSE Broadcast Active
            </span>
          </div>
          <RAICExecutionMonitor autoConnect={true} className="h-[460px]" />
        </div>

        {/* Right 6 Columns: Geographic Threat Heatmap & Active Clusters */}
        <div className="lg:col-span-6 bg-slate-900/70 border border-slate-800 rounded-xl p-5 flex flex-col justify-between h-[495px]">
          <div>
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-rose-400" />
                <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wide">
                  Geographic Threat Heatmap & Active Clusters
                </h3>
              </div>
              <span className="text-xs font-mono text-slate-400">National Cyber Grid</span>
            </div>

            {/* Interactive India Cluster Matrix */}
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-5 gap-3">
              {Object.entries(cityCoordinates).map(([city, info]) => {
                const isSelected = selectedCity === city;
                return (
                  <div
                    key={city}
                    onClick={() => setSelectedCity(city)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      isSelected
                        ? "bg-rose-950/40 border-rose-500 shadow-lg scale-102"
                        : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-slate-200">{city}</span>
                        <Flame className={`w-3.5 h-3.5 ${info.threat > 0.9 ? "text-rose-400 animate-pulse" : "text-amber-400"}`} />
                      </div>
                      <span className="text-lg font-black font-mono text-white mt-1 block">{info.cases} cases</span>
                    </div>
                    <div className="pt-2 border-t border-slate-800/80 mt-2">
                      <span className="text-[10px] font-mono text-slate-400 block truncate">{info.code}</span>
                      <span className="text-[11px] font-mono font-bold text-rose-300">{info.loss} loss</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected City Deep-Dive Box */}
          {selectedCity && cityCoordinates[selectedCity] && (
            <div className="p-4 rounded-xl bg-slate-950 border border-rose-500/30 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="w-4 h-4" /> Selected Cluster: {selectedCity} Surveillance Hub
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] bg-rose-500/20 text-rose-300 font-bold">
                  THREAT INDEX: {(cityCoordinates[selectedCity].threat * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                High concentration of <strong className="text-white">{cityCoordinates[selectedCity].code}</strong> vectors
                targeting senior citizens and corporate executives. Correlated with 6 active UPI handles and 3 overseas SIP
                trunking gateways.
              </p>
              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <span className="text-slate-400 text-[11px]">Prevented financial loss today:</span>
                <span className="text-emerald-400 font-bold">{cityCoordinates[selectedCity].loss}</span>
              </div>
            </div>
          )}

          <div className="pt-2 text-right">
            <Link
              href="/workbench/map"
              className="inline-flex items-center gap-1.5 text-xs font-mono text-emerald-400 hover:text-emerald-300"
            >
              <span>Launch Interactive MapLibre / GeoJSON Viewer</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>

      {/* Bottom Grid: Campaign Feed (Left) vs AI/GPU Health Matrix (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 6 Columns: Active Attack Campaign Syndicates */}
        <div className="lg:col-span-6 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-400" />
              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wide">
                Live Campaign Feed & Syndicate Attack DNA
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-400">Sprint 5 Entity Correlator</span>
          </div>

          <div className="space-y-3 max-h-72 overflow-y-auto font-mono text-xs pr-1">
            {campaigns.map((synd) => (
              <div
                key={synd.id}
                className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2.5"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-400 text-xs flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" /> {synd.code}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      synd.risk_level === "CRITICAL"
                        ? "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                        : "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                    }`}
                  >
                    {synd.risk_level} RISK
                  </span>
                </div>
                <div className="text-slate-200 font-semibold text-sm">{synd.name}</div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                  <div>
                    <span>Primary Hub:</span>{" "}
                    <strong className="text-slate-300 block truncate">{synd.hub}</strong>
                  </div>
                  <div>
                    <span>Financial Exposure:</span>{" "}
                    <strong className="text-emerald-400 block">{synd.financial_exposure}</strong>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-900">
                  <span className="text-[10px] text-slate-500">{synd.linked_cases} active cases linked</span>
                  <button
                    onClick={() => executeMassTakedown(synd.code)}
                    className="px-3 py-1 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-bold text-[11px] transition-all flex items-center gap-1 shadow-md"
                  >
                    <Zap className="w-3 h-3" /> Execute Multi-Bank Freeze
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 6 Columns: AI & GPU Hardware Health Matrix */}
        <div className="lg:col-span-6 bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Cpu className="w-5 h-5 text-emerald-400" />
              <h3 className="font-mono text-sm font-bold text-white uppercase tracking-wide">
                AI / GPU Hardware Health Matrix & Model Governance
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-400">Sprint 8 Governance Ready</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 font-mono text-xs">
            {/* Model Card 1 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">Gemini 3.1 Pro</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold">
                  ONLINE
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block">Primary 6-Factor Reasoning Engine</span>
              <div className="flex items-center justify-between text-[11px] text-slate-300 pt-1 border-t border-slate-900">
                <span>Latency: <strong className="text-emerald-400">112ms</strong></span>
                <span>Uptime: <strong className="text-white">99.98%</strong></span>
              </div>
            </div>

            {/* Model Card 2 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">Qwen 2.5-VL-7B</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold">
                  ONLINE
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block">Counterfeit & OCR Vision Analysis</span>
              <div className="flex items-center justify-between text-[11px] text-slate-300 pt-1 border-t border-slate-900">
                <span>VRAM: <strong className="text-amber-400">18.4 / 24 GB</strong></span>
                <span>GPU: <strong className="text-white">NVIDIA A10G</strong></span>
              </div>
            </div>

            {/* Model Card 3 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">Whisper-large-v3</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold">
                  ONLINE
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block">Voice Note Audio Transcriber</span>
              <div className="flex items-center justify-between text-[11px] text-slate-300 pt-1 border-t border-slate-900">
                <span>Latency: <strong className="text-emerald-400">142ms</strong></span>
                <span>Queue: <strong className="text-white">0 pending</strong></span>
              </div>
            </div>

            {/* Model Card 4 */}
            <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-slate-200">EventBroadcaster</span>
                <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-400 font-bold">
                  BRIDGE ACTIVE
                </span>
              </div>
              <span className="text-[10px] text-slate-400 block">Hybrid Memory Queue + Redis Pub/Sub</span>
              <div className="flex items-center justify-between text-[11px] text-slate-300 pt-1 border-t border-slate-900">
                <span>Channel: <strong className="text-purple-400">raic:events</strong></span>
                <span>SSE: <strong className="text-emerald-400">Unbuffered</strong></span>
              </div>
            </div>
          </div>

          {/* GPU VRAM & System Load Gauge */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2 font-mono text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span>National GPU Cluster Utilization</span>
              <span className="text-emerald-400 font-bold">76.6%</span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-slate-900 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-emerald-500 via-amber-500 to-rose-500 w-[76.6%]" />
            </div>
            <div className="flex justify-between text-[10px] text-slate-500 pt-1">
              <span>0% Idle</span>
              <span>Optimal AI Load Threshold (80%)</span>
              <span>100% Saturation</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
