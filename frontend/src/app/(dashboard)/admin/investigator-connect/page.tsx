"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  UserCheck,
  AlertTriangle,
  RefreshCw,
  Search,
  Filter,
  ArrowRight,
  Clock,
  CheckCircle2,
  PhoneCall,
  SlidersHorizontal,
  X,
  FileText
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

interface TriageCase {
  id: string;
  reference: string;
  incident_type: string;
  urgency_level: string;
  status: string;
  city?: string;
  state?: string;
  estimated_loss_inr?: number;
  is_ongoing_fraud: boolean;
  assigned_to?: string;
  created_at: string;
  submitter?: { name: string; email: string };
}

export default function AdminInvestigatorConnectPage() {
  const { token } = useAuthStore();
  const [cases, setCases] = useState<TriageCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [urgencyFilter, setUrgencyFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Modals state
  const [assignModalCase, setAssignModalCase] = useState<TriageCase | null>(null);
  const [assigneeId, setAssigneeId] = useState("");
  const [assignNotes, setAssignNotes] = useState("");
  const [submittingAssign, setSubmittingAssign] = useState(false);

  const [overrideModalCase, setOverrideModalCase] = useState<TriageCase | null>(null);
  const [newUrgency, setNewUrgency] = useState("critical");
  const [overrideReason, setOverrideReason] = useState("");
  const [submittingOverride, setSubmittingOverride] = useState(false);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      let url = api("/admin/cases/queue");
      const params = new URLSearchParams();
      if (urgencyFilter !== "ALL") {
        params.append("urgency_level", urgencyFilter);
      }
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setCases(data.cases || []);
      }
    } catch (err) {
      console.error("Failed to fetch queue", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchQueue();
    }
  }, [token, urgencyFilter]);

  const handleAssign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!assignModalCase || !assigneeId.trim()) return;
    setSubmittingAssign(true);
    try {
      const res = await fetch(
        api(`/admin/cases/${assignModalCase.id}/assign`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            assignee_id: assigneeId.trim(),
            notes: assignNotes.trim() || undefined,
          }),
        }
      );
      if (res.ok) {
        alert("Case successfully assigned.");
        setAssignModalCase(null);
        setAssigneeId("");
        setAssignNotes("");
        fetchQueue();
      } else {
        const err = await res.json();
        alert(err.detail || "Assignment failed.");
      }
    } catch (err) {
      alert("Error making assignment.");
    } finally {
      setSubmittingAssign(false);
    }
  };

  const handleOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!overrideModalCase || overrideReason.trim().length < 5) {
      alert("Please enter a documented reason (min 5 chars).");
      return;
    }
    setSubmittingOverride(true);
    try {
      const res = await fetch(
        api(`/admin/cases/${overrideModalCase.id}/triage-override`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            new_urgency: newUrgency,
            override_reason: overrideReason.trim(),
          }),
        }
      );
      if (res.ok) {
        alert("Urgency level successfully updated.");
        setOverrideModalCase(null);
        setOverrideReason("");
        fetchQueue();
      } else {
        const err = await res.json();
        alert(err.detail || "Override failed.");
      }
    } catch (err) {
      alert("Error overriding triage.");
    } finally {
      setSubmittingOverride(false);
    }
  };

  const filteredCases = cases.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.reference.toLowerCase().includes(q) ||
      c.incident_type.toLowerCase().includes(q) ||
      (c.city && c.city.toLowerCase().includes(q)) ||
      (c.state && c.state.toLowerCase().includes(q))
    );
  });

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <ShieldAlert className="w-4 h-4" />
            Investigator Connect Command
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Assistance Request Triage & Assignment Queue
          </h1>
          <p className="text-xs sm:text-sm text-gray-400 mt-1">
            Urgency-first case routing based strictly on active harm velocity and financial impact.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/admin/disputes"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-red-950/40 hover:bg-red-900/40 text-red-300 border border-red-500/30 text-xs font-semibold transition"
          >
            Misconduct Queue
          </Link>
          <button
            onClick={fetchQueue}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 text-xs font-semibold transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-8 relative">
          <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by DR-Reference, Incident Type, City, or State..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#0e1320] border border-white/10 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-amber-500"
          />
        </div>

        <div className="md:col-span-4 flex gap-2">
          {["ALL", "critical", "high", "standard"].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setUrgencyFilter(lvl)}
              className={`flex-1 py-2 rounded-lg text-xs font-bold uppercase transition border ${
                urgencyFilter === lvl
                  ? "bg-amber-500 text-black border-amber-500"
                  : "bg-[#0e1320] text-gray-400 border-white/10 hover:text-white"
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>
      </div>

      {/* Case Table */}
      <div className="rounded-xl border border-white/10 bg-[#0e1320] overflow-hidden shadow-xl">
        {loading ? (
          <div className="py-16 text-center text-gray-400 text-xs">
            <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Loading triage queue...
          </div>
        ) : filteredCases.length === 0 ? (
          <div className="py-16 text-center text-gray-400 text-xs">
            <CheckCircle2 className="w-10 h-10 text-emerald-500/40 mx-auto mb-3" />
            No cases pending in triage.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-gray-400 uppercase tracking-wider border-b border-white/5 font-semibold">
                <tr>
                  <th className="p-4">Reference</th>
                  <th className="p-4">Incident Type</th>
                  <th className="p-4">Urgency</th>
                  <th className="p-4">Loss / Harm</th>
                  <th className="p-4">Jurisdiction</th>
                  <th className="p-4">Assignment</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-gray-300">
                {filteredCases.map((c) => {
                  const isCritical = c.urgency_level === "critical";
                  const isHigh = c.urgency_level === "high";

                  return (
                    <tr key={c.id} className="hover:bg-white/[0.02] transition">
                      <td className="p-4 font-mono font-bold text-white">
                        {c.reference}
                        <span className="block text-[10px] text-gray-500 font-normal">
                          {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </td>
                      <td className="p-4 font-semibold text-gray-200 capitalize">
                        {c.incident_type.replace(/_/g, " ")}
                        {c.is_ongoing_fraud && (
                          <span className="inline-block ml-2 px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-[10px] uppercase font-bold animate-pulse">
                            LIVE
                          </span>
                        )}
                      </td>
                      <td className="p-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                          isCritical
                            ? "bg-red-500/20 text-red-400 border border-red-500/40"
                            : isHigh
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/40"
                            : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        }`}>
                          {c.urgency_level}
                        </span>
                      </td>
                      <td className="p-4 font-mono">
                        {c.estimated_loss_inr && c.estimated_loss_inr > 0 ? (
                          <span className="text-red-400 font-bold">₹{c.estimated_loss_inr.toLocaleString()}</span>
                        ) : (
                          <span className="text-gray-500">Nil / Threat Only</span>
                        )}
                      </td>
                      <td className="p-4 text-gray-300">
                        {c.city || "N/A"}, {c.state || "N/A"}
                      </td>
                      <td className="p-4">
                        {c.assigned_to ? (
                          <span className="inline-flex items-center gap-1 text-emerald-400 font-semibold text-[11px]">
                            <UserCheck className="w-3.5 h-3.5" />
                            Assigned
                          </span>
                        ) : (
                          <span className="text-gray-500 text-[11px]">Unassigned</span>
                        )}
                      </td>
                      <td className="p-4 text-right space-x-2">
                        <button
                          onClick={() => setAssignModalCase(c)}
                          className="px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 font-semibold transition"
                        >
                          Assign
                        </button>
                        <button
                          onClick={() => setOverrideModalCase(c)}
                          className="px-2.5 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold transition"
                        >
                          Override
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Assignment Modal */}
      {assignModalCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <form onSubmit={handleAssign} className="bg-[#0e1320] border border-white/10 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl relative text-gray-200">
            <button
              type="button"
              onClick={() => setAssignModalCase(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-bold text-white">Assign Case to Officer</h3>
            <p className="text-xs text-gray-400">Case Ref: {assignModalCase.reference}</p>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                Authorized Officer UUID
              </label>
              <input
                type="text"
                placeholder="Enter Officer UUID..."
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value)}
                required
                className="w-full px-3 py-2 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500 font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                Assignment Notes (Optional)
              </label>
              <textarea
                placeholder="Special instructions or jurisdictional notes..."
                value={assignNotes}
                onChange={(e) => setAssignNotes(e.target.value)}
                rows={3}
                className="w-full p-2.5 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setAssignModalCase(null)}
                className="px-4 py-2 rounded-lg bg-white/5 text-gray-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingAssign}
                className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs"
              >
                {submittingAssign ? "Assigning..." : "Confirm Assignment"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Urgency Override Modal */}
      {overrideModalCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <form onSubmit={handleOverride} className="bg-[#0e1320] border border-white/10 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl relative text-gray-200">
            <button
              type="button"
              onClick={() => setOverrideModalCase(null)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="text-base font-bold text-white">Override Urgency Level</h3>
            <p className="text-xs text-gray-400">Case Ref: {overrideModalCase.reference} (Current: {overrideModalCase.urgency_level})</p>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                New Urgency Tier
              </label>
              <select
                value={newUrgency}
                onChange={(e) => setNewUrgency(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500"
              >
                <option value="critical">CRITICAL (Immediate containment needed)</option>
                <option value="high">HIGH (Active within 48h / High loss)</option>
                <option value="standard">STANDARD (Routine inquiry / Historical)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                Documented Written Rationale (Mandatory)
              </label>
              <textarea
                placeholder="Explain the factual basis for overriding automated triage..."
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                required
                rows={3}
                className="w-full p-2.5 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setOverrideModalCase(null)}
                className="px-4 py-2 rounded-lg bg-white/5 text-gray-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingOverride}
                className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs"
              >
                {submittingOverride ? "Updating..." : "Record Override"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
