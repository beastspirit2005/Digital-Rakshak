"use client";


import { api } from "@/lib/api";
import { AlertTriangle, ShieldAlert, Users, Target, MoreHorizontal, Loader2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { useEffect, useState } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import Link from "next/link";

const stats = [
  { name: "Total Cases", value: "1,248", change: "+12.5%", isPositive: true, icon: ShieldAlert },
  { name: "High Priority", value: "156", change: "-8.3%", isPositive: false, icon: Target },
  { name: "Under Review", value: "342", change: "+4.1%", isPositive: true, icon: AlertTriangle },
  { name: "Resolved", value: "750", change: "+15.2%", isPositive: true, icon: Users },
];

const trendData = [
  { name: "22 May", upi: 120, digital: 80, phishing: 40 },
  { name: "23 May", upi: 132, digital: 90, phishing: 45 },
  { name: "24 May", upi: 101, digital: 70, phishing: 55 },
  { name: "25 May", upi: 145, digital: 110, phishing: 60 },
  { name: "26 May", upi: 190, digital: 130, phishing: 80 },
  { name: "27 May", upi: 150, digital: 100, phishing: 65 },
  { name: "28 May", upi: 165, digital: 115, phishing: 70 },
];

const categoryData = [
  { name: "UPI Fraud", value: 35, color: "#4f46e5" },
  { name: "Digital Arrest", value: 22, color: "#ec4899" },
  { name: "Phishing", value: 18, color: "#06b6d4" },
  { name: "Investment Scam", value: 12, color: "#eab308" },
  { name: "Others", value: 13, color: "#64748b" },
];

export default function WorkbenchDashboard() {
  const [recentCases, setRecentCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchCases = async () => {
      try {
        const res = await axios.get(api("/cases/?limit=10"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setRecentCases(res.data.cases);
      } catch (err) {
        console.error("Failed to fetch recent cases", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchCases();
  }, [token]);
  return (
    <>
      <div className="flex flex-col gap-2 mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Welcome back, Investigator. Here's what's happening in your jurisdiction today.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        {stats.map((stat) => (
          <div key={stat.name} className="glass-panel p-6 rounded-2xl flex flex-col justify-between h-36 border border-border">
            <div className="flex justify-between items-start">
              <p className="text-sm font-medium text-muted-foreground">{stat.name}</p>
              <stat.icon className="w-4 h-4 text-muted-foreground" />
            </div>
            <div>
              <h3 className="text-3xl font-bold tracking-tight">{stat.value}</h3>
              <p className={`text-xs font-medium mt-1 ${stat.isPositive ? 'text-emerald-500' : 'text-red-500'}`}>
                {stat.change} vs last 7 days
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        {/* Threat Trend Chart */}
        <div className="lg:col-span-2 glass-panel p-6 rounded-2xl border border-border h-[400px] flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold text-lg">Threat Trend (Last 7 Days)</h3>
            <MoreHorizontal className="w-5 h-5 text-muted-foreground" />
          </div>
          <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorUpi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#4f46e5" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDigital" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ec4899" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ec4899" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  itemStyle={{ color: 'hsl(var(--foreground))' }}
                />
                <Area type="monotone" dataKey="upi" stroke="#4f46e5" strokeWidth={2} fillOpacity={1} fill="url(#colorUpi)" />
                <Area type="monotone" dataKey="digital" stroke="#ec4899" strokeWidth={2} fillOpacity={1} fill="url(#colorDigital)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Top Scam Categories Donut */}
        <div className="glass-panel p-6 rounded-2xl border border-border h-[400px] flex flex-col">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-lg">Top Scam Categories</h3>
            <MoreHorizontal className="w-5 h-5 text-muted-foreground" />
          </div>
          <div className="flex-1 relative min-h-0 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={80}
                  outerRadius={110}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px' }}
                  itemStyle={{ color: 'hsl(var(--foreground))' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-3xl font-bold">1,248</span>
              <span className="text-xs text-muted-foreground uppercase tracking-widest mt-1">Total</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs mt-4">
            {categoryData.map(cat => (
              <div key={cat.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: cat.color }} />
                  <span className="text-muted-foreground">{cat.name}</span>
                </div>
                <span className="font-medium">{cat.value}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-2 glass-panel rounded-2xl border border-border overflow-hidden">
          <div className="p-6 border-b border-border flex items-center justify-between bg-card/50">
            <h3 className="font-semibold text-lg">Recent Cases</h3>
            <Link href="/workbench/reports" className="text-sm text-primary hover:underline">View All</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-6 py-4 font-medium">Case ID</th>
                  <th className="px-6 py-4 font-medium">Type</th>
                  <th className="px-6 py-4 font-medium">Location</th>
                  <th className="px-6 py-4 font-medium">Priority</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                      <Loader2 className="w-5 h-5 animate-spin inline mr-2" />
                      Loading cases...
                    </td>
                  </tr>
                ) : recentCases.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                      No recent cases found.
                    </td>
                  </tr>
                ) : (
                  recentCases.map((c) => (
                    <tr key={c.id} className="hover:bg-muted/30 transition-colors">
                      <td className="px-6 py-4 font-medium text-primary">{c.case_number}</td>
                      <td className="px-6 py-4">{c.scam_type_code || "Unknown"}</td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {c.city ? `${c.city}${c.state ? `, ${c.state}` : ''}` : "Unknown"}
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-md text-xs font-medium capitalize ${
                          c.priority === 'critical' ? 'bg-red-500/10 text-red-500' : 
                          c.priority === 'high' ? 'bg-orange-500/10 text-orange-500' :
                          'bg-blue-500/10 text-blue-500'
                        }`}>
                          {c.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border capitalize ${
                          c.status === 'under_review' ? 'border-orange-500/30 text-orange-500 bg-orange-500/10' :
                          c.status === 'investigating' ? 'border-blue-500/30 text-blue-500 bg-blue-500/10' :
                          c.status === 'submitted' ? 'border-purple-500/30 text-purple-500 bg-purple-500/10' :
                          'border-gray-500/30 text-gray-500 bg-gray-500/10'
                        }`}>
                          {c.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link href={`/workbench/reports`} className="text-primary hover:underline font-medium text-xs">
                          View Details
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-panel rounded-2xl border border-border overflow-hidden flex flex-col">
          <div className="p-6 border-b border-border flex items-center justify-between bg-card/50">
            <h3 className="font-semibold text-lg">Threat Map Snapshot</h3>
            <Link href="/workbench/map" className="text-sm text-primary hover:underline">View Map</Link>
          </div>
          <div className="flex-1 bg-gradient-to-b from-blue-900/10 to-transparent flex items-center justify-center p-6 relative">
            <div className="absolute inset-0 opacity-40 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary/20 via-background to-background" />
            <div className="w-full h-full border border-border/50 rounded-xl bg-background/50 backdrop-blur-sm flex items-center justify-center text-muted-foreground relative overflow-hidden">
               {/* Decorative dots to simulate heatmap */}
               <div className="absolute top-1/3 left-1/4 w-8 h-8 rounded-full bg-red-500/40 blur-md animate-pulse" />
               <div className="absolute top-1/2 left-1/2 w-12 h-12 rounded-full bg-red-500/30 blur-lg animate-pulse" style={{animationDelay: '1s'}} />
               <div className="absolute bottom-1/3 right-1/4 w-6 h-6 rounded-full bg-orange-500/40 blur-md animate-pulse" style={{animationDelay: '2s'}} />
               <p className="z-10">MapLibre GL Map Canvas</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
