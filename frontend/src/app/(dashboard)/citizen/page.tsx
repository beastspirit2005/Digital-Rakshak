"use client";


import { api } from "@/lib/api";
import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { 
  FileText, 
  Clock, 
  CheckCircle, 
  Plus, 
  AlertTriangle,
  ChevronRight,
  ShieldAlert,
  Loader2
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";

interface Case {
  id: string | number;
  case_number: string;
  created_at: string;
  scam_type: string;
  priority: string;
  status: string;
}

export default function CitizenDashboard() {
  const { token, user } = useAuthStore();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchCases = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      
      try {
        setLoading(true);
        const response = await axios.get(api("/cases/my"), {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        
        setCases(response.data.cases || []);
      } catch (err) {
        console.error("Failed to fetch cases:", err);
        setError("Failed to load your reports. Please try again later.");
      } finally {
        setLoading(false);
      }
    };

    fetchCases();
  }, [token]);

  // Derived stats
  const totalReports = cases.length;
  const normalizeStatus = (status: string) => (status || "").toLowerCase().replace(/_/g, ' ');
  const underReview = cases.filter(c => {
    const s = normalizeStatus(c.status);
    return s === "under review" || s === "pending" || s === "submitted" || s === "analyzing";
  }).length;
  const resolved = cases.filter(c => {
    const s = normalizeStatus(c.status);
    return s === "resolved" || s === "closed" || s === "completed";
  }).length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-foreground tracking-tight">
            Welcome back, <span className="text-emerald-500 dark:text-emerald-400">{user?.full_name || 'Citizen'}</span>
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-2 text-lg">
            Track your submitted reports and stay updated on their progress.
          </p>
        </div>
        
        <Link 
          href="/report"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-foreground font-medium rounded-xl transition-all duration-300 shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] active:scale-95"
        >
          <Plus className="w-5 h-5" />
          Report New Scam
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-panel p-6 rounded-2xl flex items-center gap-5 border border-slate-200 dark:border-white/5 hover:border-emerald-500/30 transition-all duration-300 group bg-white/50 dark:bg-white/5">
          <div className="p-4 rounded-xl bg-blue-100 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 group-hover:scale-110 transition-transform duration-300">
            <FileText className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Reports Filed</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-foreground mt-1">{loading ? "-" : totalReports}</p>
          </div>
        </div>
        
        <div className="glass-panel p-6 rounded-2xl flex items-center gap-5 border border-slate-200 dark:border-white/5 hover:border-amber-500/30 transition-all duration-300 group bg-white/50 dark:bg-white/5">
          <div className="p-4 rounded-xl bg-amber-100 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 group-hover:scale-110 transition-transform duration-300">
            <Clock className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Reports Under Review</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-foreground mt-1">{loading ? "-" : underReview}</p>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl flex items-center gap-5 border border-slate-200 dark:border-white/5 hover:border-emerald-500/30 transition-all duration-300 group bg-white/50 dark:bg-white/5">
          <div className="p-4 rounded-xl bg-emerald-100 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform duration-300">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Resolved Reports</p>
            <p className="text-3xl font-bold text-slate-900 dark:text-foreground mt-1">{loading ? "-" : resolved}</p>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="glass-panel rounded-2xl overflow-hidden flex flex-col shadow-2xl border border-slate-200 dark:border-white/5 bg-white/50 dark:bg-white/[0.02]">
        <div className="p-6 border-b border-slate-200 dark:border-white/5 flex justify-between items-center">
          <h2 className="text-xl font-semibold text-slate-900 dark:text-foreground flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-emerald-500 dark:text-emerald-400" />
            My Reports
          </h2>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <Loader2 className="w-12 h-12 animate-spin text-emerald-500 mb-4" />
              <p className="text-lg">Loading your reports...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <AlertTriangle className="w-14 h-14 text-rose-500 mb-4" />
              <h3 className="text-xl font-medium text-foreground mb-2">Oops! Something went wrong</h3>
              <p className="text-slate-400 max-w-md">{error}</p>
            </div>
          ) : cases.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-24 h-24 rounded-full bg-emerald-500/10 flex items-center justify-center mb-6">
                <FileText className="w-12 h-12 text-emerald-400" />
              </div>
              <h3 className="text-2xl font-medium text-foreground mb-3">No Reports Filed Yet</h3>
              <p className="text-slate-400 max-w-md mb-8 text-lg">
                You haven't filed any scam reports yet. If you have been a victim or noticed suspicious activity, you can report it to get help.
              </p>
              <Link 
                href="/report"
                className="inline-flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl text-foreground font-medium transition-colors"
              >
                File Your First Report
                <ChevronRight className="w-5 h-5" />
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr className="text-slate-500 dark:text-slate-400 text-sm border-b border-slate-200 dark:border-white/10">
                    <th className="pb-4 font-semibold px-4 uppercase tracking-wider text-xs">Case Number</th>
                    <th className="pb-4 font-semibold px-4 uppercase tracking-wider text-xs">Date</th>
                    <th className="pb-4 font-semibold px-4 uppercase tracking-wider text-xs">Scam Type</th>
                    <th className="pb-4 font-semibold px-4 uppercase tracking-wider text-xs">Priority</th>
                    <th className="pb-4 font-semibold px-4 uppercase tracking-wider text-xs text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-white/5">
                  {cases.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-50 dark:hover:bg-white/[0.03] transition-colors group">
                      <td className="py-5 px-4">
                        <span className="font-mono font-medium text-emerald-600 dark:text-emerald-400 group-hover:text-emerald-500 dark:group-hover:text-emerald-300 transition-colors">
                          {report.case_number}
                        </span>
                      </td>
                      <td className="py-5 px-4 text-slate-600 dark:text-slate-300">
                        {new Date(report.created_at).toLocaleDateString(undefined, {
                          year: 'numeric', month: 'short', day: 'numeric'
                        })}
                      </td>
                      <td className="py-5 px-4">
                        <span className="text-slate-700 dark:text-slate-200 capitalize font-medium">
                          {((report as any).scam_type_code || report.scam_type || 'Unknown').replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="py-5 px-4">
                        <span className={`inline-flex px-3 py-1 rounded-full text-xs font-bold border tracking-wide uppercase ${
                          report.priority.toLowerCase() === 'high' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                          report.priority.toLowerCase() === 'medium' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                          'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}>
                          {report.priority}
                        </span>
                      </td>
                      <td className="py-5 px-4 text-right">
                        <span className={`inline-flex items-center justify-end gap-1.5 px-3 py-1 rounded-full text-xs font-bold border tracking-wide uppercase ${
                          normalizeStatus(report.status) === 'resolved' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          normalizeStatus(report.status) === 'under review' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                          'bg-blue-500/10 text-blue-400 border-blue-500/20'
                        }`}>
                          {normalizeStatus(report.status) === 'resolved' && <CheckCircle className="w-3.5 h-3.5" />}
                          {normalizeStatus(report.status) === 'under review' && <Clock className="w-3.5 h-3.5" />}
                          {report.status.replace(/_/g, ' ')}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
