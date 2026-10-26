"use client";

import { useState, useEffect } from "react";
import {
  AlertOctagon,
  ShieldAlert,
  FileCheck2,
  Lock,
  Download,
  CheckCircle2,
  Clock,
  Eye,
  AlertTriangle,
  Scale,
  RefreshCw,
  Search,
  X,
  FileCode2,
  FileText
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

interface DisputeItem {
  id: string;
  case_id?: string;
  category: string;
  reason_narrative: string;
  status: string;
  decision?: string;
  reporter: { name: string; role: string; email?: string };
  reported_user: { name: string; role: string; email?: string };
  created_at: string;
  resolved_at?: string;
}

export default function AdminDisputesPage() {
  const { token, user } = useAuthStore();
  const [disputes, setDisputes] = useState<DisputeItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedDisputeId, setSelectedDisputeId] = useState<string | null>(null);
  const [detailsData, setDetailsData] = useState<any | null>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Decision state
  const [decisionChoice, setDecisionChoice] = useState("warning_issued");
  const [decisionNotes, setDecisionNotes] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [exporting, setExporting] = useState(false);

  const fetchDisputes = async () => {
    setLoading(true);
    try {
      let url = api("/admin/disputes");
      if (statusFilter !== "ALL") {
        url += `?status_filter=${statusFilter}`;
      }
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setDisputes(data.disputes || []);
      }
    } catch (err) {
      console.error("Error loading disputes", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchDisputes();
    }
  }, [token, statusFilter]);

  const openDetails = async (id: string) => {
    setSelectedDisputeId(id);
    setLoadingDetails(true);
    try {
      const res = await fetch(
        api(`/admin/disputes/${id}`),
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (res.ok) {
        const data = await res.json();
        setDetailsData(data);
      }
    } catch (err) {
      console.error("Error loading dispute details", err);
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleRecordDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDisputeId || decisionNotes.trim().length < 10) {
      alert("Please provide at least 10 characters of written rationale.");
      return;
    }
    setSubmittingDecision(true);
    try {
      const res = await fetch(
        api(`/admin/disputes/${selectedDisputeId}/decision`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            decision: decisionChoice,
            decision_notes: decisionNotes.trim(),
          }),
        }
      );
      if (res.ok) {
        alert("Decision successfully recorded.");
        fetchDisputes();
        openDetails(selectedDisputeId);
      }
    } catch (err) {
      alert("Failed to record decision.");
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleExportBSA = async (reportId: string) => {
    setExporting(true);
    try {
      const res = await fetch(
        api(`/admin/disputes/${reportId}/export-bsa`),
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `BSA_Evidence_Report_${reportId.slice(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err: any) {
      alert(err.message || "Failed to download export package.");
    } finally {
      setExporting(false);
    }
  };

  const handleToggleLegalHold = async (reportId: string, currentVal: boolean) => {
    try {
      const res = await fetch(
        api(`/admin/disputes/${reportId}/legal-hold`),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            is_legal_hold: !currentVal,
            hold_reason: !currentVal ? "Preserved for lawful authority review" : "Hold lifted",
          }),
        }
      );
      if (res.ok) {
        openDetails(reportId);
      }
    } catch (err) {
      alert("Failed to toggle legal hold");
    }
  };

  return (
    <div className="p-6 sm:p-8 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <Scale className="w-4 h-4" />
            Trust & Safety Oversight
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
            Misconduct & Dispute Resolution Queue
          </h1>
          <p className="text-xs sm:text-sm text-gray-400 mt-1">
            Review reported violations, examine preserved context windows, and enforce accountability across victims and investigators.
          </p>
        </div>

        <button
          onClick={fetchDisputes}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 text-xs font-semibold transition"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh Queue
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 text-xs">
        {["ALL", "pending_review", "under_review", "protective_action", "resolved_closed"].map((st) => (
          <button
            key={st}
            onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-lg border font-semibold transition ${
              statusFilter === st
                ? "bg-amber-500 text-black border-amber-500"
                : "bg-white/5 text-gray-400 border-white/10 hover:text-white"
            }`}
          >
            {st === "ALL" ? "All Reports" : st.replace("_", " ").toUpperCase()}
          </button>
        ))}
      </div>

      {/* Disputes Table */}
      <div className="rounded-xl border border-white/10 bg-[#0e1320] overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-gray-400 text-xs">
            <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            Loading reports...
          </div>
        ) : disputes.length === 0 ? (
          <div className="py-16 text-center text-gray-400 text-xs">
            <CheckCircle2 className="w-10 h-10 text-emerald-500/40 mx-auto mb-3" />
            No reports in queue for selected filter.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-white/5 text-gray-400 uppercase tracking-wider border-b border-white/5 font-semibold">
                <tr>
                  <th className="p-4">Report ID / Date</th>
                  <th className="p-4">Category</th>
                  <th className="p-4">Reporter</th>
                  <th className="p-4">Reported Party</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-gray-300">
                {disputes.map((d) => (
                  <tr key={d.id} className="hover:bg-white/[0.02] transition">
                    <td className="p-4 font-mono">
                      <span className="text-white block font-semibold">{d.id.slice(0, 8)}...</span>
                      <span className="text-[10px] text-gray-500">{new Date(d.created_at).toLocaleDateString()}</span>
                    </td>
                    <td className="p-4">
                      <span className="capitalize font-semibold text-amber-300">{d.category.replace("_", " ")}</span>
                      <p className="text-[11px] text-gray-400 max-w-xs truncate">{d.reason_narrative}</p>
                    </td>
                    <td className="p-4">
                      <span className="font-semibold text-white block">{d.reporter.name}</span>
                      <span className="text-[10px] uppercase text-gray-500">{d.reporter.role}</span>
                    </td>
                    <td className="p-4">
                      <span className="font-semibold text-red-300 block">{d.reported_user.name}</span>
                      <span className="text-[10px] uppercase text-gray-500">{d.reported_user.role}</span>
                    </td>
                    <td className="p-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        d.status === "pending_review" ? "bg-amber-500/15 text-amber-400 border border-amber-500/30" :
                        d.status === "protective_action" ? "bg-red-500/15 text-red-400 border border-red-500/30" :
                        "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                      }`}>
                        {d.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="p-4 text-right">
                      <button
                        onClick={() => openDetails(d.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold transition"
                      >
                        <Eye className="w-3.5 h-3.5" />
                        Examine Evidence
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Evidence Examination Drawer/Modal */}
      {selectedDisputeId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md">
          <div className="bg-[#0e1320] border border-white/10 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6 sm:p-8 space-y-6 shadow-2xl relative text-gray-200">
            <button
              onClick={() => setSelectedDisputeId(null)}
              className="absolute top-5 right-5 text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            {loadingDetails || !detailsData ? (
              <div className="py-20 text-center text-gray-400 text-xs">
                <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                Loading preserved evidence snapshot...
              </div>
            ) : (
              <>
                {/* Details Header */}
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-xs font-mono bg-white/5 px-2.5 py-1 rounded text-gray-400">
                      Report: {detailsData.report.id}
                    </span>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded bg-amber-500/15 text-amber-400 uppercase">
                      Category: {detailsData.report.category.replace("_", " ")}
                    </span>
                    {detailsData.evidence_package.is_legal_hold && (
                      <span className="text-xs font-semibold px-2.5 py-1 rounded bg-red-500/20 text-red-300 border border-red-500/40">
                        LEGAL HOLD ACTIVE
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-white">
                    Preserved Context Window & Dispute Review
                  </h2>
                </div>

                {/* Cryptographic Hash Banner */}
                <div className="p-4 rounded-xl bg-black/50 border border-emerald-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-gray-400 block">
                      Preserved SHA-256 Digest (BSA 2023 Sec. 63)
                    </span>
                    <span className="font-mono text-emerald-400 text-[11px] break-all select-all">
                      {detailsData.evidence_package.package_sha256}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExportBSA(detailsData.report.id)}
                      disabled={exporting}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                      {exporting ? "Generating..." : "Export BSA Package"}
                    </button>
                    <button
                      onClick={() => handleToggleLegalHold(detailsData.report.id, detailsData.evidence_package.is_legal_hold)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 text-xs font-semibold transition"
                    >
                      <Lock className="w-3.5 h-3.5 text-amber-400" />
                      {detailsData.evidence_package.is_legal_hold ? "Lift Legal Hold" : "Apply Legal Hold"}
                    </button>
                  </div>
                </div>

                {/* Statement of Facts Narrative */}
                <div className="p-4 rounded-xl bg-white/5 border border-white/5 space-y-1">
                  <span className="text-[10px] uppercase font-bold text-gray-400 block">Report Reason / Allegation</span>
                  <p className="text-xs text-gray-200 leading-relaxed">{detailsData.report.reason_narrative}</p>
                </div>

                {/* Preserved Conversation Context Window */}
                <div className="space-y-3">
                  <span className="text-xs uppercase font-bold text-gray-400 block">
                    Preserved Incident Context Window (Preceding 5 + Target + Succeeding 2)
                  </span>
                  <div className="p-4 rounded-xl bg-[#090d16] border border-white/10 space-y-3 max-h-72 overflow-y-auto">
                    {detailsData.evidence_package.context_window?.messages?.length > 0 ? (
                      detailsData.evidence_package.context_window.messages.map((m: any, idx: number) => (
                        <div
                          key={idx}
                          className={`p-3 rounded-lg text-xs space-y-1 ${
                            m.is_target
                              ? "bg-red-950/40 border border-red-500/50"
                              : "bg-white/[0.03] border border-white/5"
                          }`}
                        >
                          <div className="flex items-center justify-between text-[10px] text-gray-400">
                            <span className="font-semibold text-gray-300">
                              Sender: {m.sender_id.slice(0, 8)}... {m.is_target && "(REPORTED MESSAGE)"}
                            </span>
                            <span className="font-mono">{new Date(m.created_at).toLocaleTimeString()}</span>
                          </div>
                          <p className="text-gray-200 font-sans">{m.content}</p>
                          {m.moderation_flag !== "clean" && (
                            <span className="inline-block text-[10px] px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 font-mono">
                              Flag: {m.moderation_flag} ({m.scanner_rule})
                            </span>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-gray-500">No message snapshot captured.</p>
                    )}
                  </div>
                </div>

                {/* Decision Form */}
                <form onSubmit={handleRecordDecision} className="p-5 rounded-xl bg-white/5 border border-white/10 space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Scale className="w-4 h-4 text-amber-400" />
                    Record Administrative Finding & Outcome
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-gray-300 block mb-1">
                        Review Decision
                      </label>
                      <select
                        value={decisionChoice}
                        onChange={(e) => setDecisionChoice(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-amber-500"
                      >
                        <option value="warning_issued">Issue Formal In-Chat Warning</option>
                        <option value="message_restricted">Apply Temporary Messaging Restriction</option>
                        <option value="account_suspended">Suspend Account (Disables Access)</option>
                        <option value="escalated_police">Escalate to Official Law Enforcement</option>
                        <option value="no_violation">No Violation Found (Dismiss)</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-gray-300 block mb-1">
                        Documented Rationale (Mandatory)
                      </label>
                      <textarea
                        value={decisionNotes}
                        onChange={(e) => setDecisionNotes(e.target.value)}
                        placeholder="Document the factual findings and reasons for this decision..."
                        rows={3}
                        className="w-full p-2.5 rounded-lg bg-[#161c2e] border border-white/10 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-amber-500"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={submittingDecision}
                      className="px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-black font-bold text-xs transition shadow-lg shadow-amber-500/20"
                    >
                      {submittingDecision ? "Saving Decision..." : "Submit Administrative Finding"}
                    </button>
                  </div>
                </form>

                {/* Audit Chain of Custody */}
                <div className="space-y-2">
                  <span className="text-[10px] uppercase font-bold text-gray-500 block">
                    Chain of Custody & Evidence Access Log
                  </span>
                  <div className="p-3 rounded-lg bg-black/40 border border-white/5 max-h-36 overflow-y-auto font-mono text-[11px] text-gray-400 space-y-1">
                    {detailsData.evidence_package.access_log?.map((log: any, i: number) => (
                      <div key={i} className="flex items-center justify-between">
                        <span>[{log.action}] by {log.actor_id?.slice(0, 8)} ({log.actor_role || "user"})</span>
                        <span className="text-gray-500">{new Date(log.timestamp).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
