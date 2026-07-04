"use client";


import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2, Activity, ShieldAlert, CheckCircle, TrendingUp, Globe, RefreshCw } from "lucide-react";
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts';

export default function PolicyMakerDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const res = await axios.get(api("/analytics/dashboard"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setData(res.data);
      } catch (err) {
        console.error("Failed to load analytics", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchAnalytics();
  }, [token]);

  if (loading || !data) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const COLORS = ['#3b82f6', '#8b5cf6', '#ef4444', '#10b981', '#f59e0b'];

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto h-full overflow-y-auto pb-10 pr-2">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">National Intelligence Analytics</h1>
          <p className="text-muted-foreground mt-1">Live aggregated metrics for policy makers and administrators.</p>
        </div>
        <div className={`px-4 py-2 rounded-full border font-bold flex items-center gap-2 ${
          data.stats.threat_level === 'CRITICAL' 
            ? 'bg-red-500/20 text-red-500 border-red-500/50' 
            : 'bg-yellow-500/20 text-yellow-500 border-yellow-500/50'
        }`}>
          <Activity className="w-4 h-4" />
          NATIONAL THREAT: {data.stats.threat_level}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl border border-border flex items-center gap-4">
          <div className="p-4 bg-primary/20 rounded-xl text-primary">
            <Activity className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground font-semibold uppercase tracking-wider">Total Incidents</p>
            <h2 className="text-4xl font-black">{data.stats.total_cases}</h2>
          </div>
        </div>
        
        <div className="glass-panel p-6 rounded-2xl border border-border flex items-center gap-4">
          <div className="p-4 bg-green-500/20 rounded-xl text-green-500">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground font-semibold uppercase tracking-wider">Resolved</p>
            <h2 className="text-4xl font-black">{data.stats.resolved_cases}</h2>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-border flex items-center gap-4">
          <div className="p-4 bg-red-500/20 rounded-xl text-red-500">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground font-semibold uppercase tracking-wider">High Priority Threats</p>
            <h2 className="text-4xl font-black">{data.stats.high_priority}</h2>
          </div>
        </div>
      </div>

      {/* OSINT Section */}
      <div className="glass-panel p-6 rounded-2xl border border-border">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="font-bold text-lg flex items-center gap-2">
              <Globe className="w-5 h-5 text-purple-500" /> Public Threat Feeds (OSINT)
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              Synchronize known malicious IoCs and scam scripts from external global databases (e.g. MHA, PhishTank).
            </p>
          </div>
          <button 
            onClick={async () => {
              try {
                setLoading(true);
                await axios.post(api("/admin/osint/sync"), {}, {
                  headers: { Authorization: `Bearer ${token}` }
                });
                alert("OSINT Feeds Synchronized Successfully! The AI now has access to the latest supervised learning RAG data.");
              } catch (err) {
                alert("Failed to sync OSINT feeds.");
              } finally {
                setLoading(false);
                window.location.reload();
              }
            }}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-xl text-sm font-medium transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" /> Sync Global OSINT Feeds
          </button>
        </div>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 h-96">
        <div className="glass-panel p-6 rounded-2xl border border-border flex flex-col">
          <h3 className="font-bold text-lg mb-6 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" /> Incident Timeline (Last 7 Days)
          </h3>
          <div className="flex-1 w-full h-full min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.timeline}>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis dataKey="date" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip contentStyle={{ backgroundColor: '#000', borderColor: '#333' }} />
                <Line type="monotone" dataKey="reports" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-border flex flex-col">
          <h3 className="font-bold text-lg mb-6">Threat Distribution by Type</h3>
          <div className="flex-1 w-full h-full min-h-0 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.scam_types}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {data.scam_types.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#000', borderColor: '#333' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2 */}
      <div className="glass-panel p-6 rounded-2xl border border-border h-96 flex flex-col">
        <h3 className="font-bold text-lg mb-6">Incident Volume by State/Region</h3>
        <div className="flex-1 w-full h-full min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.state_distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="state" stroke="#888" />
              <YAxis stroke="#888" />
              <Tooltip contentStyle={{ backgroundColor: '#000', borderColor: '#333' }} cursor={{fill: '#222'}} />
              <Bar dataKey="cases" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
