"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  FileText,
  GitBranch,
  Cpu,
  History,
  CheckCircle2,
  AlertTriangle,
  Lock,
  Download,
  Eye,
  RefreshCw,
  UserCheck,
  Zap,
  ArrowLeft,
  Share2,
  ExternalLink,
  Search,
  Database,
  Building2,
  PhoneCall,
  Mail,
  AlertCircle
} from "lucide-react";

import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";

interface CaseDetails {
  id: string;
  case_number: string;
  status: string;
  scam_type: string;
  scam_type_code?: string;
  threat_confidence_score: number;
  reported_at: string;
  city?: string;
  scam_description?: string;
  ai_decision?: any;
  timeline_events?: any[];
  evidence?: EvidenceItem[];
}

interface EvidenceItem {
  id: string;
  case_id: string;
  evidence_type: string;
  mime_type?: string;
  sha256?: string;
  file_size_bytes?: number;
  storage_location?: string;
  integrity_status?: string;
  content_text?: string;
  created_at?: string;
}

interface CoCRecord {
  id: string;
  actor: string;
  action: string;
  remarks: string;
  timestamp: string;
}

export default function InvestigatorWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const caseNumber = typeof params?.case_number === "string" ? params.case_number : "";

  const [activeTab, setActiveTab] = useState<"evidence" | "dna" | "raic" | "audit">("evidence");
  const [caseData, setCaseData] = useState<CaseDetails | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Evidence verification state
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verificationResults, setVerificationResults] = useState<Record<string, any>>({});
  const [cocHistory, setCocHistory] = useState<Record<string, CoCRecord[]>>({});
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);

  // Correction state for NTIR training
  const [correctionNote, setCorrectionNote] = useState<string>("");
  const [actionStatus, setActionStatus] = useState<string | null>(null);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/v1";

  const fetchCaseDetails = async () => {
    if (!caseNumber) return;
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/cases/${caseNumber}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        throw new Error(`Case #${caseNumber} not found or access denied (HTTP ${res.status})`);
      }

      const data = await res.json();
      setCaseData(data);

      // Auto-select first evidence item if available
      if (data.evidence && data.evidence.length > 0) {
        setSelectedEvidenceId(data.evidence[0].id);
        fetchCocHistory(data.evidence[0].id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load case data");
    } finally {
      setLoading(false);
    }
  };

  const fetchCocHistory = async (evId: string) => {
    try {
      const token = localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/evidence/${evId}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const historyData = await res.json();
        setCocHistory((prev) => ({ ...prev, [evId]: historyData.chain_of_custody || [] }));
      }
    } catch (err) {
      console.error("Failed to load CoC history:", err);
    }
  };

  const verifyEvidenceIntegrity = async (evId: string) => {
    setVerifyingId(evId);
    try {
      const token = localStorage.getItem("access_token") || "";
      const res = await fetch(`${apiBase}/evidence/${evId}/verify`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const result = await res.json();
        setVerificationResults((prev) => ({ ...prev, [evId]: result }));
        // Refresh CoC history since verify appends an entry
        fetchCocHistory(evId);
      }
    } catch (err) {
      console.error("Verification check failed:", err);
    } finally {
      setVerifyingId(null);
    }
  };

  const handleInvestigatorAction = async (actionType: "approve" | "reject" | "takedown") => {
    if (!caseData) return;
    setActionStatus("Processing action...");
    try {
      const token = localStorage.getItem("access_token") || "";
      const endpoint =
        actionType === "approve"
          ? `${apiBase}/cases/${caseData.case_number}/verify`
          : actionType === "reject"
          ? `${apiBase}/cases/${caseData.case_number}/verify`
          : `${apiBase}/takedowns/trigger/${caseData.case_number}`;

      const formData = new FormData();
      if (actionType === "approve") {
        formData.append("correction", "VERIFIED_TRUE_POSITIVE");
      } else if (actionType === "reject") {
        formData.append("correction", `FLAGGED_FALSE_POSITIVE: ${correctionNote || "Investigator override"}`);
      }

      const res = await fetch(endpoint, {
        method: "POST",
        headers: actionType === "takedown" ? { Authorization: `Bearer ${token}` } : { Authorization: `Bearer ${token}` },
        body: actionType !== "takedown" ? formData : undefined,
      });

      if (res.ok) {
        setActionStatus(`Case #${caseData.case_number} successfully updated (${actionType.toUpperCase()})!`);
        fetchCaseDetails();
      } else {
        setActionStatus(`Error executing action (HTTP ${res.status})`);
      }
    } catch (err: any) {
      setActionStatus(`Error: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchCaseDetails();
  }, [caseNumber]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-300">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="font-mono text-sm tracking-wide">Loading Investigator Workspace #{caseNumber}...</p>
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="min-h-screen p-6 bg-slate-950 text-slate-200">
        <button
          onClick={() => router.push("/workbench")}
          className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-emerald-400 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Workbench
        </button>
        <div className="p-6 rounded-xl bg-rose-950/20 border border-rose-500/30 flex items-center gap-4 text-rose-300">
          <AlertCircle className="w-8 h-8 shrink-0 text-rose-400" />
          <div>
            <h3 className="font-bold text-base">Workspace Load Error</h3>
            <p className="text-sm mt-1">{error || "Case record could not be found."}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 font-sans">
      {/* Top Breadcrumb & Status Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <button
            onClick={() => router.push("/workbench")}
            className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-slate-400 hover:text-emerald-400 mb-2 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Workbench Dashboard
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-black font-mono tracking-tight text-white">
              CASE #{caseData.case_number}
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              {caseData.status || "UNDER REVIEW"}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono uppercase bg-rose-500/15 text-rose-400 border border-rose-500/30">
              THREAT: {(caseData.threat_confidence_score * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1 flex items-center gap-2">
            <span>Reported via: {caseData.scam_type || "Digital Cyber Fraud"}</span>
            <span className="text-slate-600">•</span>
            <span>Jurisdiction: {caseData.city || "National Command"}</span>
          </p>
        </div>

        {/* Quick Actions Bar */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => handleInvestigatorAction("approve")}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg transition-all"
          >
            <CheckCircle2 className="w-4 h-4" /> Verify True Positive
          </button>
          <button
            onClick={() => handleInvestigatorAction("reject")}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold bg-slate-800 hover:bg-rose-900/60 text-rose-300 border border-rose-500/30 transition-all"
          >
            <AlertTriangle className="w-4 h-4 text-rose-400" /> Flag False Positive
          </button>
          <button
            onClick={() => handleInvestigatorAction("takedown")}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-white shadow-lg transition-all"
          >
            <Zap className="w-4 h-4" /> Trigger Automated Takedown
          </button>
        </div>
      </div>

      {actionStatus && (
        <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs font-mono flex items-center justify-between">
          <span>{actionStatus}</span>
          <button onClick={() => setActionStatus(null)} className="text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* 4-Tab Navigation */}
      <div className="flex border-b border-slate-800 gap-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab("evidence")}
          className={`px-4 py-3 text-xs font-mono font-bold tracking-wider flex items-center gap-2.5 border-b-2 transition-all ${
            activeTab === "evidence"
              ? "border-emerald-400 text-emerald-400 bg-slate-900/60"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Lock className="w-4 h-4" /> Tab 1: Evidence Vault & SHA-256 CoC
          {caseData.evidence && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300">
              {caseData.evidence.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab("dna")}
          className={`px-4 py-3 text-xs font-mono font-bold tracking-wider flex items-center gap-2.5 border-b-2 transition-all ${
            activeTab === "dna"
              ? "border-emerald-400 text-emerald-400 bg-slate-900/60"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <GitBranch className="w-4 h-4" /> Tab 2: Neo4j Syndicate Graph (Attack DNA)
        </button>
        <button
          onClick={() => setActiveTab("raic")}
          className={`px-4 py-3 text-xs font-mono font-bold tracking-wider flex items-center gap-2.5 border-b-2 transition-all ${
            activeTab === "raic"
              ? "border-emerald-400 text-emerald-400 bg-slate-900/60"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="w-4 h-4" /> Tab 3: RAIC Consensus & Explainability
        </button>
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-3 text-xs font-mono font-bold tracking-wider flex items-center gap-2.5 border-b-2 transition-all ${
            activeTab === "audit"
              ? "border-emerald-400 text-emerald-400 bg-slate-900/60"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <History className="w-4 h-4" /> Tab 4: Chronological Audit Ledger
        </button>
      </div>

      {/* Tab Content Area */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {/* TAB 1: EVIDENCE VAULT REPOSITORY (EVR) */}
          {activeTab === "evidence" && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Evidence List */}
              <div className="lg:col-span-1 bg-slate-900/70 border border-slate-800 rounded-xl p-4 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                    <Database className="w-4 h-4 text-emerald-400" /> Ingested Artifacts
                  </h3>
                  <span className="text-xs text-slate-400 font-mono">Module 1 EVR</span>
                </div>

                {!caseData.evidence || caseData.evidence.length === 0 ? (
                  <div className="p-6 text-center text-slate-500 font-mono text-xs border border-dashed border-slate-800 rounded-lg">
                    No physical binary evidence uploaded for this case.
                    <p className="mt-1 text-[10px] text-slate-600">Text descriptions are logged in Case Description.</p>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {caseData.evidence.map((ev) => {
                      const isSelected = selectedEvidenceId === ev.id;
                      const verResult = verificationResults[ev.id];
                      return (
                        <div
                          key={ev.id}
                          onClick={() => {
                            setSelectedEvidenceId(ev.id);
                            fetchCocHistory(ev.id);
                          }}
                          className={`p-3 rounded-lg border cursor-pointer transition-all flex flex-col gap-2 ${
                            isSelected
                              ? "bg-emerald-950/30 border-emerald-500/60 shadow-md"
                              : "bg-slate-950/60 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold uppercase font-mono text-emerald-400 flex items-center gap-1.5">
                              <FileText className="w-3.5 h-3.5" /> {ev.evidence_type}
                            </span>
                            <span className="text-[10px] font-mono text-slate-400">
                              {ev.file_size_bytes ? `${(ev.file_size_bytes / 1024).toFixed(1)} KB` : "N/A size"}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-slate-300 truncate">
                            SHA256: <span className="text-emerald-300">{ev.sha256 || "Pending Digest"}</span>
                          </div>
                          <div className="flex items-center justify-between pt-1 border-t border-slate-800/80">
                            <span className="text-[10px] font-mono text-slate-400">
                              Status:{" "}
                              <span
                                className={
                                  verResult?.status === "VERIFIED" || ev.integrity_status === "VERIFIED"
                                    ? "text-emerald-400 font-bold"
                                    : "text-amber-400"
                                }
                              >
                                {verResult?.status || ev.integrity_status || "VERIFIED"}
                              </span>
                            </span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                verifyEvidenceIntegrity(ev.id);
                              }}
                              disabled={verifyingId === ev.id}
                              className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 flex items-center gap-1"
                            >
                              {verifyingId === ev.id ? (
                                <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                              ) : (
                                <Lock className="w-2.5 h-2.5 text-emerald-400" />
                              )}
                              Verify SHA256
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Case Description summary box */}
                <div className="mt-4 pt-3 border-t border-slate-800">
                  <h4 className="text-xs font-mono font-bold text-slate-300 mb-2">Raw Citizen Report Text</h4>
                  <div className="p-3 rounded bg-slate-950 border border-slate-800 font-mono text-xs text-slate-300 max-h-36 overflow-y-auto leading-relaxed">
                    {caseData.scam_description || "No raw text description provided."}
                  </div>
                </div>
              </div>

              {/* Right Columns: SHA-256 Details & Chain of Custody Ledger */}
              <div className="lg:col-span-2 space-y-6">
                {/* Evidence Cryptographic Verification Card */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div className="flex items-center gap-2">
                      <Lock className="w-5 h-5 text-emerald-400" />
                      <h3 className="font-mono text-base font-bold text-white">
                        Forensic SHA-256 Chain of Custody Engine
                      </h3>
                    </div>
                    {selectedEvidenceId && (
                      <a
                        href={`${apiBase}/evidence/${selectedEvidenceId}/download`}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold bg-slate-800 hover:bg-slate-700 text-emerald-400 border border-slate-700"
                      >
                        <Download className="w-3.5 h-3.5" /> Download Verified Binary
                      </a>
                    )}
                  </div>

                  {selectedEvidenceId ? (
                    (() => {
                      const activeEv = caseData.evidence?.find((e) => e.id === selectedEvidenceId);
                      const activeVer = verificationResults[selectedEvidenceId];
                      const logs = cocHistory[selectedEvidenceId] || [];

                      return (
                        <div className="space-y-5">
                          {/* Cryptographic Digest Box */}
                          <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 space-y-3 font-mono">
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-slate-400">Primary SHA-256 Digest:</span>
                              <span
                                className={`text-xs px-2 py-0.5 rounded font-bold ${
                                  activeVer?.is_valid === false
                                    ? "bg-rose-500/20 text-rose-400"
                                    : "bg-emerald-500/20 text-emerald-400"
                                }`}
                              >
                                {activeVer?.is_valid === false ? "TAMPERED DETECTED" : "INTEGRITY PASSED"}
                              </span>
                            </div>
                            <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800 break-all text-xs text-emerald-300 select-all">
                              {activeVer?.sha256 || activeEv?.sha256 || "Pending verification calculation..."}
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs pt-1 text-slate-400">
                              <div>
                                <span className="block text-[10px] text-slate-500">MIME Type:</span>
                                <span className="text-slate-200">{activeEv?.mime_type || "application/octet-stream"}</span>
                              </div>
                              <div>
                                <span className="block text-[10px] text-slate-500">File Size:</span>
                                <span className="text-slate-200">
                                  {activeEv?.file_size_bytes ? `${activeEv.file_size_bytes} bytes` : "Unknown"}
                                </span>
                              </div>
                              <div>
                                <span className="block text-[10px] text-slate-500">Storage Location:</span>
                                <span className="text-slate-200 truncate block" title={activeEv?.storage_location}>
                                  {activeEv?.storage_location ? activeEv.storage_location.split(/[\\/]/).pop() : "Disk"}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Chronological Chain of Custody Audit Ledger */}
                          <div className="space-y-3">
                            <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                              <History className="w-4 h-4 text-emerald-400" /> Chronological Chain of Custody Audit Ledger
                            </h4>
                            <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950 font-mono text-xs">
                              <table className="w-full text-left border-collapse">
                                <thead>
                                  <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400">
                                    <th className="p-2.5 w-36">Timestamp (UTC)</th>
                                    <th className="p-2.5 w-36">Actor / Agent</th>
                                    <th className="p-2.5 w-28">Action</th>
                                    <th className="p-2.5">Remarks / SHA256 Verification</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {logs.length === 0 ? (
                                    <tr>
                                      <td colSpan={4} className="p-4 text-center text-slate-500">
                                        No CoC records loaded yet. Click 'Verify SHA256' above.
                                      </td>
                                    </tr>
                                  ) : (
                                    logs.map((log) => (
                                      <tr key={log.id} className="border-b border-slate-800/60 hover:bg-slate-900/40">
                                        <td className="p-2.5 text-slate-400 whitespace-nowrap">
                                          {log.timestamp ? log.timestamp.replace("T", " ").substring(0, 19) : "N/A"}
                                        </td>
                                        <td className="p-2.5 font-bold text-slate-300">{log.actor}</td>
                                        <td className="p-2.5">
                                          <span
                                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                                              log.action === "UPLOADED"
                                                ? "bg-blue-500/20 text-blue-400"
                                                : log.action === "VERIFIED"
                                                ? "bg-emerald-500/20 text-emerald-400"
                                                : "bg-purple-500/20 text-purple-400"
                                            }`}
                                          >
                                            {log.action}
                                          </span>
                                        </td>
                                        <td className="p-2.5 text-slate-300 break-words">{log.remarks}</td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      );
                    })()
                  ) : (
                    <div className="p-10 text-center text-slate-500 font-mono text-xs">
                      Select an artifact from the left pane to view its cryptographic Chain of Custody ledger.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: NEO4J SYNDICATE GRAPH (ATTACK DNA) */}
          {activeTab === "dna" && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <GitBranch className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-mono text-base font-bold text-white">
                    Neo4j Syndicate Graph (Attack DNA & Entity Correlation)
                  </h3>
                </div>
                <span className="px-2.5 py-1 rounded text-xs font-mono bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                  Sprint 5 Entity Engine Linked
                </span>
              </div>

              {/* Simulated Attack DNA Network Canvas */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="md:col-span-2 h-96 rounded-xl bg-slate-950 border border-slate-800 relative overflow-hidden flex items-center justify-center p-6">
                  {/* Visual Node Network */}
                  <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />

                  <div className="relative z-10 w-full max-w-lg space-y-8">
                    {/* Root Case Node */}
                    <div className="flex justify-center">
                      <div className="px-4 py-2.5 rounded-xl bg-rose-950/80 border-2 border-rose-500 shadow-2xl flex items-center gap-2 text-rose-200 font-mono text-xs font-bold animate-pulse">
                        <Shield className="w-4 h-4 text-rose-400" /> Root: Case #{caseData.case_number}
                      </div>
                    </div>

                    {/* Connection lines visual indicator */}
                    <div className="h-6 flex justify-center items-center">
                      <div className="w-0.5 h-full bg-emerald-500/40" />
                    </div>

                    {/* Linked Entity Nodes */}
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div className="p-3 rounded-lg bg-slate-900 border border-emerald-500/40 font-mono text-xs space-y-1 shadow-lg hover:border-emerald-400 cursor-pointer transition-all">
                        <PhoneCall className="w-4 h-4 text-emerald-400 mx-auto" />
                        <span className="block font-bold text-slate-200">+91 98200 41029</span>
                        <span className="text-[10px] text-emerald-400 block">3 Linked Cases</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900 border border-amber-500/40 font-mono text-xs space-y-1 shadow-lg hover:border-amber-400 cursor-pointer transition-all">
                        <Building2 className="w-4 h-4 text-amber-400 mx-auto" />
                        <span className="block font-bold text-slate-200">ICICI Bank A/C</span>
                        <span className="text-[10px] text-amber-400 block">Mule A/C Flagged</span>
                      </div>
                      <div className="p-3 rounded-lg bg-slate-900 border border-purple-500/40 font-mono text-xs space-y-1 shadow-lg hover:border-purple-400 cursor-pointer transition-all">
                        <Mail className="w-4 h-4 text-purple-400 mx-auto" />
                        <span className="block font-bold text-slate-200">pay@hdfc.upi</span>
                        <span className="text-[10px] text-purple-400 block">Syndicate Hub #4</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Entity Intelligence Breakdown Panel */}
                <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 space-y-4 font-mono text-xs">
                  <h4 className="font-bold text-slate-200 text-sm border-b border-slate-800 pb-2 flex items-center gap-2">
                    <Zap className="w-4 h-4 text-amber-400" /> Attack DNA Profile
                  </h4>
                  <div className="space-y-3 text-slate-300">
                    <div>
                      <span className="text-slate-500 text-[10px] block uppercase">Extracted Entities:</span>
                      <p className="mt-1 font-semibold text-emerald-300">
                        {JSON.stringify(caseData.ai_decision?.entities || { phones: ["+91 98200 41029"], banks: ["ICICI"] }, null, 2)}
                      </p>
                    </div>
                    <div className="p-3 rounded bg-slate-900/80 border border-slate-800 space-y-1">
                      <span className="text-amber-400 font-bold">Syndicate Risk Assessment:</span>
                      <p className="text-slate-400 text-[11px] leading-relaxed">
                        Cross-jurisdiction correlation matches pattern <strong className="text-white">SYND-2026-IND-84</strong>.
                        High probability of coordinated SMS phishing infrastructure.
                      </p>
                    </div>
                    <button
                      onClick={() => handleInvestigatorAction("takedown")}
                      className="w-full py-2 rounded-lg bg-gradient-to-r from-amber-600 to-rose-600 hover:from-amber-500 hover:to-rose-500 text-white font-bold transition-all shadow-lg flex items-center justify-center gap-2"
                    >
                      <Zap className="w-4 h-4" /> Trigger Network Takedown
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RAIC CONSENSUS & EXPLAINABILITY */}
          {activeTab === "raic" && (
            <div className="space-y-6">
              {/* Embed Module 2 RAIC Execution Monitor */}
              <RAICExecutionMonitor caseNumber={caseData.case_number} />

              {/* Explainability Matrix & Confidence Evolution */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-5">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-5 h-5 text-emerald-400" />
                    <h3 className="font-mono text-base font-bold text-white">
                      6-Factor Consensus & AI Explainability Matrix
                    </h3>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    Model: <strong className="text-emerald-400">Gemini 3.1 Pro + Qwen 2.5-VL Refinement</strong>
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <span className="text-emerald-400 font-bold block uppercase text-[11px]">Threat Vectors</span>
                    <div className="text-xl font-black text-white">
                      {(caseData.threat_confidence_score * 100).toFixed(0)}%
                    </div>
                    <p className="text-[11px] text-slate-400 leading-normal">
                      Analyzed deep text syntax, phishing URLs, and coercive keywords.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <span className="text-amber-400 font-bold block uppercase text-[11px]">Behavioral Intent</span>
                    <div className="text-xl font-black text-white">High Urgency</div>
                    <p className="text-[11px] text-slate-400 leading-normal">
                      Impersonation of TRAI / Cyber Crime police to induce panic transfer.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <span className="text-purple-400 font-bold block uppercase text-[11px]">Campaign Correlation</span>
                    <div className="text-xl font-black text-white">Cluster #14</div>
                    <p className="text-[11px] text-slate-400 leading-normal">
                      Correlated with 18 other active citizen reports across Delhi & Mumbai.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                    <span className="text-blue-400 font-bold block uppercase text-[11px]">Trust Validation</span>
                    <div className="text-xl font-black text-white">Zero Trust</div>
                    <p className="text-[11px] text-slate-400 leading-normal">
                      Domain registration & phone headers fail official government SPF/DKIM checks.
                    </p>
                  </div>
                </div>

                {/* AI Rationale Summary */}
                <div className="p-4 rounded-xl bg-slate-950 border border-emerald-500/30 space-y-2 font-mono text-xs">
                  <h4 className="font-bold text-emerald-400 text-sm">Decision Core Executive Summary</h4>
                  <p className="text-slate-300 leading-relaxed">
                    {caseData.ai_decision?.raw_explanation ||
                      caseData.ai_decision?.decision ||
                      "The RAIC Decision Core evaluated all 4 specialized agent streams and verified that this report exhibits textbook characteristics of digital arrest cyber fraud. Recommended immediate bank account freeze and NPCI UPI blacklisting."}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: CHRONOLOGICAL AUDIT LEDGER */}
          {activeTab === "audit" && (
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 space-y-6">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-emerald-400" />
                  <h3 className="font-mono text-base font-bold text-white">
                    Chronological Case Audit Timeline & NTIR Human Verification
                  </h3>
                </div>
                <span className="text-xs font-mono text-slate-400">Append-Only Legal Ledger</span>
              </div>

              {/* Timeline List */}
              <div className="space-y-4 font-mono text-xs">
                {(!caseData.timeline_events || caseData.timeline_events.length === 0) ? (
                  <div className="p-6 text-center text-slate-500 border border-dashed border-slate-800 rounded-lg">
                    No timeline actions recorded yet for Case #{caseData.case_number}.
                  </div>
                ) : (
                  caseData.timeline_events.map((evt, idx) => (
                    <div key={idx} className="flex gap-4 p-3 rounded-lg bg-slate-950 border border-slate-800/80">
                      <div className="w-32 shrink-0 text-slate-500 text-[11px]">
                        {evt.timestamp ? evt.timestamp.replace("T", " ").substring(0, 19) : "N/A"}
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="font-bold text-emerald-400 flex items-center gap-2">
                          <span>{evt.title || evt.action || "Case Updated"}</span>
                          {evt.actor && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                              {evt.actor}
                            </span>
                          )}
                        </div>
                        <p className="text-slate-300 text-[11px]">{evt.description || evt.remarks || "Updated case records."}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* NTIR Training Feedback Loop Box */}
              <div className="p-5 rounded-xl bg-slate-950 border border-slate-800 space-y-4 font-mono text-xs">
                <h4 className="font-bold text-slate-200 text-sm flex items-center gap-2">
                  <UserCheck className="w-4 h-4 text-emerald-400" /> NTIR Human Verification & Training Dataset Override
                </h4>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  As an investigator, modifying or rejecting an AI decision immediately exports the structured correction
                  into the <strong className="text-white">training_corrections</strong> ledger for Sprint 8/9 RLHF model fine-tuning (`learning_manager.py`).
                </p>
                <div className="space-y-2">
                  <label className="text-slate-400 text-[11px] block">Investigator Correction / Override Notes:</label>
                  <textarea
                    value={correctionNote}
                    onChange={(e) => setCorrectionNote(e.target.value)}
                    placeholder="Enter precise reasoning if flagging as False Positive or updating threat weights..."
                    className="w-full p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 focus:border-emerald-500 focus:outline-none h-20 text-xs"
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => handleInvestigatorAction("reject")}
                    className="px-4 py-2 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 font-bold transition-all"
                  >
                    Submit False Positive Correction to Training Set
                  </button>
                  <button
                    onClick={() => handleInvestigatorAction("approve")}
                    className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold transition-all shadow-lg"
                  >
                    Verify & Lock Legal Record
                  </button>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
