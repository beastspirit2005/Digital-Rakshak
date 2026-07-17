"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import { 
  FileText, 
  TrendingUp, 
  ShieldAlert, 
  CheckCircle2, 
  AlertCircle,
  Activity,
  Cpu,
  RefreshCw,
  Zap,
  Globe,
  Siren,
  Terminal
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";
import { motion } from "framer-motion";

const chartColors = [
  "#10b981", // emerald-500
  "#3b82f6", // blue-500
  "#f43f5e", // rose-500
  "#8b5cf6", // violet-500
  "#f59e0b", // amber-500
  "#06b6d4"  // cyan-500
];

interface CaseRow {
  id: string;
  case_number: string;
  scam_type_code?: string;
  city?: string;
  state?: string;
  priority: string;
  status: string;
}

export default function WorkbenchDashboard() {
  const [recentCases, setRecentCases] = useState<CaseRow[]>([]);
  const [statsData, setStatsData] = useState<any>({ total_cases: 0, resolved_cases: 0, high_priority: 0, under_review: 0 });
  const [trendData, setTrendData] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [telemetry, setTelemetry] = useState<string>("Loading telemetry...");
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [casesRes, analyticsRes, telemetryRes] = await Promise.all([
          axios.get(api("/cases/?limit=10"), { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(api("/analytics/dashboard"), { headers: { Authorization: `Bearer ${token}` } }),
          axios.get(api("/health/ai-telemetry")).catch(() => ({ data: { models: [] } }))
        ]);
        
        const qwenModel = telemetryRes.data?.models?.find((m: any) => m.id === "qwen-2.5-vl");
        if (qwenModel && qwenModel.vram_usage) {
          setTelemetry(qwenModel.vram_usage);
        } else {
          setTelemetry("Cloud Engine");
        }
        
        setRecentCases(casesRes.data.cases);
        
        const analytics = analyticsRes.data;
        setStatsData({
          ...analytics.stats,
          under_review: analytics.stats.total_cases - analytics.stats.resolved_cases
        });
        
        setTrendData(analytics.timeline || []);
        
        const types = analytics.scam_types || [];
        const totalCases = analytics.stats.total_cases || 1;
        setCategoryData(types.map((t: any, idx: number) => ({
          name: (t.name || "Unknown").replace(/_/g, " "),
          value: Math.round((t.value / totalCases) * 100),
          count: t.value,
          color: chartColors[idx % chartColors.length]
        })));
        
      } catch (err) {
        console.error("Failed to fetch dashboard data", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchData();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="font-mono text-sm tracking-wide">Loading Workbench Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 font-sans">
      {/* Top Title Bar & Status Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-gradient-to-br from-emerald-900 to-emerald-600 text-white shadow-xl flex items-center justify-center border border-emerald-500/30">
            <Activity className="w-7 h-7 text-emerald-100" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl md:text-3xl font-black font-mono tracking-tight text-white uppercase">
                Investigator Workbench
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
                <Globe className="w-3 h-3" /> NATIONAL HUB
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5 flex items-center gap-2">
              <span>Jurisdictional Cyber Threat Activity</span>
              <span className="text-slate-600">•</span>
              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                <Cpu className="w-3 h-3" /> Hardware: {telemetry}
              </span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/workbench/map"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold bg-slate-900 hover:bg-slate-800 text-emerald-400 shadow-lg transition-all border border-emerald-500/30"
          >
            <Globe className="w-4 h-4" /> Spatial Intelligence Map
          </Link>
          <Link
            href="/workbench/counterfeit"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold bg-rose-950 hover:bg-rose-900 text-rose-400 shadow-lg transition-all border border-rose-500/30"
          >
            <Siren className="w-4 h-4" /> Counterfeit Hub
          </Link>
        </div>
      </div>

      {/* Top KPI Metrics Matrix */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono">
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex items-center justify-between relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <span className="text-[10px] text-slate-400 uppercase block tracking-wider flex items-center gap-1">
              <Terminal className="w-3 h-3 text-slate-500" /> Total Cases Ingested
            </span>
            <span className="text-2xl font-black text-white mt-1 block tabular-nums">{statsData.total_cases}</span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
              Real-time synchronization active
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-900/50 flex items-center justify-between relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-r from-rose-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <span className="text-[10px] text-rose-400/70 uppercase block tracking-wider flex items-center gap-1">
              <AlertCircle className="w-3 h-3 text-rose-500" /> High Priority Threats
            </span>
            <span className="text-2xl font-black text-rose-100 mt-1 block tabular-nums">{statsData.high_priority}</span>
            <span className="text-[10px] text-rose-400 flex items-center gap-1 mt-1">
              Requires immediate action
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/50 flex items-center justify-between relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-r from-amber-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <span className="text-[10px] text-amber-400/70 uppercase block tracking-wider flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-amber-500" /> Pending Investigation
            </span>
            <span className="text-2xl font-black text-amber-100 mt-1 block tabular-nums">{statsData.under_review}</span>
            <span className="text-[10px] text-amber-400 flex items-center gap-1 mt-1">
              Queued for review
            </span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/50 flex items-center justify-between relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-r from-emerald-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="relative z-10">
            <span className="text-[10px] text-emerald-400/70 uppercase block tracking-wider flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-500" /> Successfully Resolved
            </span>
            <span className="text-2xl font-black text-emerald-100 mt-1 block tabular-nums">{statsData.resolved_cases}</span>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 mt-1">
              Cases closed
            </span>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 p-4 md:p-6 rounded-xl bg-slate-900/80 border border-slate-800 font-mono flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-emerald-400" /> Tactical Threat Trend
              </h2>
              <p className="text-xs text-slate-500 mt-1">Daily incident report volume across all vectors</p>
            </div>
          </div>
          
          <div className="flex-1 min-h-[250px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="fillReports" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis 
                  dataKey="date" 
                  stroke="#475569" 
                  tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                  tickLine={false}
                  axisLine={false}
                  dy={10}
                />
                <YAxis 
                  stroke="#475569" 
                  tick={{ fill: '#94a3b8', fontSize: 10, fontFamily: 'monospace' }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'monospace', fontSize: '12px', color: '#f1f5f9' }}
                  itemStyle={{ color: '#10b981' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="reports" 
                  name="Daily Incidents"
                  stroke="#10b981" 
                  strokeWidth={2} 
                  fill="url(#fillReports)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="p-4 md:p-6 rounded-xl bg-slate-900/80 border border-slate-800 font-mono flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest flex items-center gap-2">
                <PieChart className="w-4 h-4 text-emerald-400" /> Attack Vectors
              </h2>
              <p className="text-xs text-slate-500 mt-1">Classification breakdown</p>
            </div>
          </div>
          
          <div className="flex-1 relative min-h-[200px] flex items-center justify-center my-4">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius="65%"
                  outerRadius="85%"
                  paddingAngle={3}
                  dataKey="value"
                  stroke="#020617"
                  strokeWidth={3}
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#020617', border: '1px solid #334155', borderRadius: '8px', fontFamily: 'monospace', fontSize: '12px', color: '#f1f5f9' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="font-black text-2xl text-white tabular-nums">{statsData.total_cases}</span>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Total</span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 gap-y-2 mt-2">
            {categoryData.slice(0, 4).map((cat) => (
              <div key={cat.name} className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-2 text-slate-400 truncate pr-2">
                  <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: cat.color }} />
                  {cat.name}
                </span>
                <span className="text-slate-200 font-bold tabular-nums shrink-0">{cat.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Threat Reports Table */}
      <div className="p-4 md:p-6 rounded-xl bg-slate-900/80 border border-slate-800 font-mono">
        <div className="flex items-center justify-between mb-6 border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-200 uppercase tracking-widest flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-400" /> Active Intelligence Vault
            </h2>
            <p className="text-xs text-slate-500 mt-1">Recent unredacted cyber case files</p>
          </div>
          <Link href="/workbench/reports" className="text-xs font-bold text-emerald-400 hover:text-emerald-300 underline underline-offset-4 decoration-emerald-500/40">
            View All Records
          </Link>
        </div>
        
        <div className="overflow-x-auto">
          {recentCases.length === 0 ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-500">
              <FileText className="w-8 h-8 mb-3 opacity-20" />
              <p className="text-sm">No recent cases loaded into the vault.</p>
            </div>
          ) : (
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/50 text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 font-semibold rounded-l-lg border-b border-slate-800">Case ID</th>
                  <th className="px-4 py-3 font-semibold border-b border-slate-800">Attack Vector</th>
                  <th className="px-4 py-3 font-semibold border-b border-slate-800">Jurisdiction</th>
                  <th className="px-4 py-3 font-semibold border-b border-slate-800">Threat Priority</th>
                  <th className="px-4 py-3 font-semibold rounded-r-lg border-b border-slate-800 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {recentCases.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-800/30 transition-colors group">
                    <td className="px-4 py-3.5">
                      <Link 
                        href={`/workbench/workspace/${c.case_number}`} 
                        className="font-bold text-emerald-400 group-hover:text-emerald-300 flex items-center gap-2"
                      >
                        <Zap className="w-3 h-3 opacity-50" /> {c.case_number}
                      </Link>
                    </td>
                    <td className="px-4 py-3.5 text-slate-400 capitalize">
                      {(c.scam_type_code || "Unknown").replace(/_/g, " ")}
                    </td>
                    <td className="px-4 py-3.5 text-slate-400">
                      {c.city ? `${c.city}${c.state ? `, ${c.state}` : ""}` : "Unknown"}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider inline-flex items-center gap-1 ${
                        c.priority.toLowerCase() === 'high' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                        c.priority.toLowerCase() === 'medium' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                        'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {c.priority}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider inline-block ${
                        ['resolved', 'closed'].includes(c.status.toLowerCase()) ? 'text-slate-400 bg-slate-800' :
                        'text-sky-400 bg-sky-500/10 border border-sky-500/20'
                      }`}>
                        {c.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}