"use client";

import { api } from "@/lib/api";
import React, { useEffect, useMemo, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";
import { Search, FileText, ChevronDown, ChevronUp, Send, MessageSquare, Compass, Radio, AlertTriangle, BellRing, CheckCircle2, Download } from "lucide-react";
import { CaseChatPanel } from "@/components/chat/CaseChatPanel";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Card, Inset } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatusBadge, PriorityBadge, Badge } from "@/components/ui/badge";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { ZtivfMeters } from "@/components/ztivf-meters";
import { useToast } from "@/components/ui/toast";
import { CaseActivityTimeline } from "@/components/case/CaseActivityTimeline";
import { CaseStepper } from "@/components/case/CaseStepper";
import { LoadingOverlay } from "@/components/ui/loading-overlay";

function CaseDetail({
  c,
  chatQuery,
  setChatQuery,
  chatHistory,
  chatLoading,
  onChatSubmit,
  userRole,
  investigators,
  onAssign,
  onAccept,
  onUndertake,
  onCompleteInvestigation,
  token,
  isNudged,
  onRefresh,
}: {
  c: any;
  chatQuery: string;
  setChatQuery: (v: string) => void;
  chatHistory: { role: string; text: string }[];
  chatLoading: boolean;
  onChatSubmit: (e: React.FormEvent) => void;
  userRole?: string;
  investigators: any[];
  onAssign: (caseId: string, invId: string) => void;
  onAccept?: (caseId: string) => void;
  onUndertake?: (caseId: string) => void;
  onCompleteInvestigation?: (caseId: string, formData: FormData) => void;
  token: string | null;
  isNudged?: boolean;
  onRefresh?: () => void;
}) {
  const [selectedInv, setSelectedInv] = useState("");
  const [osintFlags, setOsintFlags] = useState<any[] | null>(null);
  const [scanningOsint, setScanningOsint] = useState(false);
  const [remark, setRemark] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);
  const [showVictimChat, setShowVictimChat] = useState(false);
  const [progressRemark, setProgressRemark] = useState("");
  const [submittingRemark, setSubmittingRemark] = useState(false);
  const pushToast = useToast();

  const handleProgressRemarkSubmit = async () => {
    if (!progressRemark.trim()) return;
    setSubmittingRemark(true);
    try {
      await axios.post(
        api(`/cases/${c.case_number}/progress-remark`),
        { remark: progressRemark.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      pushToast("success", "Evidentiary progress update logged and transmitted to Administrator.");
      setProgressRemark("");
      onRefresh?.();
    } catch (err: any) {
      console.error("Failed to submit progress remark", err);
      pushToast("danger", err?.response?.data?.detail || "Failed to log progress remark");
    } finally {
      setSubmittingRemark(false);
    }
  };

  const downloadDossierPdf = async () => {
    try {
      const res = await axios.get(api(`/assistance-requests/${c.case_number}/dossier-pdf`), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        responseType: "blob",
        withCredentials: true,
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Legal_FIR_Dossier_${c.case_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      pushToast("success", "Legal FIR Dossier PDF downloaded successfully.");
    } catch (err: any) {
      pushToast("danger", "Failed to generate FIR Dossier PDF.");
    }
  };

  const runOsintScan = async () => {
    if (!token) return;
    setScanningOsint(true);
    try {
      const res = await axios.get(api(`/admin/osint/scan-case/${c.case_number}`), {
        headers: { Authorization: `Bearer ${token}` }
      });
      setOsintFlags(res.data.flags || []);
      if (res.data.flags?.length > 0) {
        pushToast("danger", `Found ${res.data.flags.length} global OSINT threat indicators!`);
      } else {
        pushToast("success", "No external OSINT threat indicators found for this case.");
      }
    } catch (err) {
      pushToast("danger", "Failed to run OSINT scan.");
    } finally {
      setScanningOsint(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 sm:p-6 relative">
      {/* Priority Admin Investigation Inquiry Banner */}
      {(c.is_nudged || isNudged) && (
        <div className="lg:col-span-3 p-4 rounded-xl border border-rose-500/50 bg-gradient-to-r from-rose-500/15 via-rose-500/10 to-amber-500/10 shadow-lg animate-in fade-in duration-300">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2.5 rounded-lg bg-rose-500/20 text-rose-500 mt-0.5 shrink-0">
                <AlertTriangle className="w-5 h-5 animate-bounce" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="text-sm font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
                    Priority Admin Investigation Inquiry
                  </h4>
                  <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-500 border border-rose-500/40">
                    SLA SUPERVISION ACTIVE
                  </span>
                </div>
                <p className="text-xs text-ink-2 mt-1 leading-relaxed">
                  Platform Administrator requested an expedited progress update and evidentiary submission for this case under priority SLA supervision.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <Button
                size="sm"
                variant="secondary"
                className="text-xs border-sky-500/30 text-sky-400 hover:bg-sky-500/15"
                onClick={() => setShowVictimChat(true)}
              >
                <MessageSquare className="w-3.5 h-3.5 mr-1" />
                Case Chat
              </Button>
            </div>
          </div>

          {/* Quick Evidentiary Remark Input to answer Admin & resolve inquiry */}
          <div className="mt-3 pt-3 border-t border-rose-500/20 flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <input
              type="text"
              placeholder="Enter evidentiary progress update to answer administrator..."
              value={progressRemark}
              onChange={(e) => setProgressRemark(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleProgressRemarkSubmit();
                }
              }}
              className="flex-1 h-9 px-3 rounded-control text-xs bg-surface border border-rose-500/30 text-ink placeholder:text-ink-3 focus:outline-none focus:border-rose-400"
            />
            <Button
              size="sm"
              variant="primary"
              disabled={submittingRemark || !progressRemark.trim()}
              onClick={handleProgressRemarkSubmit}
              className="bg-rose-600 hover:bg-rose-500 text-white text-xs h-9 font-medium shrink-0"
            >
              {submittingRemark ? "Submitting..." : "Submit Remark & Resolve Nudge"}
            </Button>
          </div>
        </div>
      )}
      <LoadingOverlay
        open={scanningOsint}
        variant="cyber"
        fullscreen={false}
        title={`Scanning Case ${c.case_number} Indicators`}
        subtitle="Querying global open-source intelligence and threat actor repositories..."
        badge="OSINT Case Scanner"
        steps={[
          "Extracting suspect phone numbers, UPI handles & URLs...",
          "Querying CIRT, VirusTotal & MISP threat databases...",
          "Correlating indicators against active campaign syndicates...",
          "Synthesizing threat intelligence flags..."
        ]}
      />
      <div className="col-span-full pb-2">
        <CaseStepper status={c.status} />
      </div>

      <div className="lg:col-span-2 space-y-4">
        {/* If investigation is completed, show the official concluded card */}
        {(c.status === "investigation_completed" || c.investigation_findings) && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-950/20 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-ink flex items-center gap-2">
                  <span>Investigation Concluded & Docket Filed</span>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500 text-white font-semibold">
                    Submitted
                  </span>
                </h4>
                <p className="text-xs text-ink-3">
                  Investigated by: <strong className="text-ink">{c.investigated_by || "Assigned Officer"}</strong>
                  {c.investigation_completed_at && (
                    <span> • {new Date(c.investigation_completed_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</span>
                  )}
                </p>
              </div>
            </div>

            <div>
              <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                Submitted Findings & Evidence Summary:
              </p>
              <p className="text-sm text-ink whitespace-pre-wrap leading-relaxed bg-surface/70 p-3 rounded-lg border border-line">
                {c.investigation_findings || "Findings submitted successfully."}
              </p>
            </div>

            {c.investigation_attachment && (
              <div className="flex items-center justify-between p-2.5 bg-surface rounded-lg border border-line">
                <div className="flex items-center gap-2 truncate">
                  <FileText className="w-4 h-4 text-accent shrink-0" />
                  <span className="text-xs font-mono text-ink truncate">
                    Attached Evidence: {c.investigation_attachment.split("/").pop()}
                  </span>
                </div>
                <a
                  href={c.investigation_attachment}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-accent font-semibold hover:underline shrink-0"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </div>
            )}
          </div>
        )}

        <Inset className="p-4">
          <p className="text-xs text-ink-3 mb-2">Original report</p>
          <p className="text-sm text-ink whitespace-pre-wrap leading-relaxed">{c.scam_text}</p>
        </Inset>

        {c.ai_decision?.evidence && c.ai_decision.evidence.length > 0 && (
          <div>
            <p className="text-xs text-ink-3 mb-2">Extracted evidence</p>
            <ul className="space-y-1.5">
              {c.ai_decision.evidence.map((ev: any, idx: number) => (
                <li key={idx} className="text-sm text-ink bg-surface-2 rounded-control px-3 py-2">
                  {ev.relevance || JSON.stringify(ev)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {c.ai_decision?.raw_explanation && (
          <div>
            <p className="text-xs text-ink-3 mb-2">AI reasoning</p>
            <p className="text-sm text-ink-2 leading-relaxed">{c.ai_decision.raw_explanation}</p>
          </div>
        )}
        
        <div className="pt-2 flex flex-wrap gap-2">
           <Button variant="secondary" size="sm" onClick={downloadDossierPdf} className="border-warning/40 text-warning hover:bg-warning/10">
             Download FIR Dossier PDF
           </Button>
           <Button variant="secondary" size="sm" onClick={runOsintScan} loading={scanningOsint} className="border-red-500/30 text-red-500 hover:bg-red-500/10 hover:text-red-600">
             Scan OSINT Flags
           </Button>
        </div>

        {osintFlags && osintFlags.length > 0 && (
          <div className="mt-4 p-4 border border-red-500/30 bg-red-500/5 rounded-md">
            <p className="text-sm font-semibold text-red-500 mb-2">Global Threat Intelligence Hits</p>
            <ul className="space-y-2">
              {osintFlags.map((flag: any, i: number) => (
                <li key={i} className="text-xs flex gap-2 items-center">
                  <Badge tone="danger">ThreatIntel</Badge>
                  <span className="text-ink">{flag.value}</span>
                  <span className="text-ink-3">— Flagged by {flag.source} ({flag.threat_type})</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {osintFlags && osintFlags.length === 0 && (
          <div className="mt-4">
            <p className="text-xs text-ink-3">No OSINT threats detected for entities in this case.</p>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <Inset className="p-4">
          <p className="text-xs text-ink-3 mb-3">Analysis summary</p>
          <dl className="space-y-2.5 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Decision</dt>
              <dd className="text-ink font-medium text-right capitalize">
                {(c.ai_decision?.decision || "—").replace(/_/g, " ")}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Latency</dt>
              <dd className="text-ink tabular">{c.ai_decision?.inference_time_ms || 0} ms</dd>
            </div>
            {(c.ai_decision?.models_used || []).length > 0 && (
              <div>
                <dt className="text-ink-2 mb-1.5">Models</dt>
                <dd className="flex flex-wrap gap-1.5">
                  {c.ai_decision.models_used.map((m: string) => (
                    <Badge key={m} className="capitalize">{m}</Badge>
                  ))}
                </dd>
              </div>
            )}
          </dl>
        </Inset>

        {c.ai_decision?.ztivf_metrics && (
          <Inset className="p-4">
            <p className="text-xs text-ink-3 mb-3">Zero-trust validation</p>
            <ZtivfMeters metrics={c.ai_decision.ztivf_metrics} className="grid-cols-1 sm:grid-cols-1" />
          </Inset>
        )}
        
        {/* Actions based on Role */}
        <Inset className="p-4">
          <p className="text-xs text-ink-3 mb-3">Case Actions</p>
          {userRole === "admin" && (c.status === "submitted" || c.status === "under_review" || c.status === "escalated") && (
            <div className="space-y-3">
               <select 
                 className="w-full text-sm p-2 rounded-control bg-surface-2 border-transparent text-ink"
                 value={selectedInv}
                 onChange={(e) => setSelectedInv(e.target.value)}
               >
                 <option value="">Select Investigator...</option>
                 {investigators.map((inv) => (
                    <option key={inv.id} value={inv.id}>{inv.full_name} ({inv.role})</option>
                 ))}
               </select>
               <Button size="sm" variant="primary" className="w-full" disabled={!selectedInv} onClick={() => onAssign(c.case_number, selectedInv)}>
                  Assign Case
               </Button>
            </div>
          )}
          {(userRole === "police" || userRole === "cyber_cell") && c.status === "assigned" && (
             <div className="space-y-2">
               <Button variant="primary" className="w-full" onClick={() => onAccept?.(c.case_number)}>
                  Accept Case for Investigation
               </Button>
             </div>
          )}
          {(userRole === "police" || userRole === "cyber_cell") && (c.status === "submitted" || c.status === "under_review" || c.status === "escalated") && (
             <Button variant="primary" className="w-full" onClick={() => onUndertake?.(c.case_number)}>
                Undertake Case
             </Button>
          )}
          {(userRole === "police" || userRole === "cyber_cell") && (c.status === "investigating" || c.status === "assigned") && (
             <div className="space-y-3 pt-2 border-t border-line/40">
               <div className="flex items-center justify-between">
                 <p className="text-[11px] font-bold text-ink">Submit Final Investigation Findings:</p>
                 <span className="text-[10px] text-ink-3">Docket Entry</span>
               </div>
               <textarea 
                 placeholder="Enter detailed investigation findings, recovered assets, frozen accounts, or actions taken..." 
                 value={remark} 
                 onChange={(e) => setRemark(e.target.value)}
                 className="w-full text-sm p-2 rounded-control bg-surface-2 border border-line text-ink resize-none h-20"
               />
               <input 
                 type="file" 
                 onChange={(e) => setAttachment(e.target.files?.[0] || null)}
                 className="w-full text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-full file:border-0 file:text-xs file:font-medium file:bg-surface file:text-ink hover:file:bg-surface-2 text-ink-2"
               />
               <Button 
                 size="sm" 
                 variant="primary" 
                 className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold" 
                 disabled={!remark.trim()}
                 onClick={() => {
                   const fd = new FormData();
                   fd.append("remark", remark);
                   if (attachment) fd.append("file", attachment);
                   onCompleteInvestigation?.(c.case_number, fd);
                 }}
               >
                  Complete Investigation & Submit Docket
               </Button>
             </div>
          )}
          {c.status === "investigation_completed" && (
            <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-500" />
              <span>Investigation complete. Final findings submitted to Admin & Complainant.</span>
            </div>
          )}
          {userRole !== "admin" && userRole !== "police" && userRole !== "cyber_cell" && (
             <p className="text-xs text-ink-3">No actions available.</p>
          )}

          {/* Direct Monitored Victim-Officer Chat */}
          <div className="pt-2 border-t border-line/40">
            <Button
              variant="secondary"
              size="sm"
              className="w-full inline-flex items-center justify-center gap-2 border-sky-500/30 text-sky-400 hover:bg-sky-500/10"
              onClick={() => setShowVictimChat(true)}
            >
              <MessageSquare className="w-4 h-4" />
              <span>Direct Monitored Chat with Victim</span>
            </Button>
          </div>
        </Inset>

        {c.assignment_source === "map_radar_claim" && (
          <Inset className="p-4 bg-accent/5 border border-accent/25">
            <div className="flex items-center gap-2 text-xs font-bold text-accent mb-1">
              <Compass className="w-4 h-4" />
              <span>Origin: Self-Claimed via Tactical Map Radar</span>
            </div>
            <p className="text-xs text-ink-2 leading-relaxed">
              This case was undertaken by you directly from the Proximity Radar. Victim identity was unmasked and direct monitored chat was enabled upon claim.
              {c.claimed_at && ` Claim recorded on ${new Date(c.claimed_at).toLocaleString('en-IN')}.`}
            </p>
          </Inset>
        )}

        {c.timeline_events && c.timeline_events.length > 0 && (
          <Inset className="p-4">
            <p className="text-xs text-ink-3 mb-3">Case activity timeline</p>
            <CaseActivityTimeline events={c.timeline_events} />
          </Inset>
        )}

        {/* per-case co-pilot */}
        <Inset className="p-4 flex flex-col h-72">
          <p className="text-xs text-ink-3 mb-3">Ask the co-pilot about this case</p>
          <div className="flex-1 overflow-y-auto mb-3 space-y-2 text-sm">
            {chatHistory.length === 0 ? (
              <p className="text-ink-3 text-center mt-6 text-xs">
                Questions about the evidence, entities, or next steps.
              </p>
            ) : (
              chatHistory.map((msg, i) => (
                <div
                  key={i}
                  className={cn(
                    "rounded-control px-3 py-2",
                    msg.role === "user"
                      ? "bg-surface-3 text-ink ml-6"
                      : "bg-surface text-ink mr-6 shadow-card"
                  )}
                >
                  {msg.text}
                </div>
              ))
            )}
            {chatLoading && <p className="text-xs text-ink-3 animate-pulse">Thinking…</p>}
          </div>
          <form onSubmit={onChatSubmit} className="flex gap-2">
            <input
              type="text"
              value={chatQuery}
              onChange={(e) => setChatQuery(e.target.value)}
              placeholder="Ask a question"
              className="flex-1 h-9 px-3 bg-surface rounded-control text-sm text-ink placeholder:text-ink-3 border border-transparent focus:border-accent-text focus:outline-none"
              disabled={chatLoading}
            />
            <Button type="submit" size="sm" variant="primary" disabled={chatLoading} aria-label="Send">
              <Send className="w-3.5 h-3.5" />
            </Button>
          </form>
        </Inset>

        {/* Direct Monitored Victim-Officer Chat Modal */}
        {showVictimChat && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200">
            <div className="w-full max-w-2xl h-[640px] max-h-[90vh]">
              <CaseChatPanel
                caseId={String(c.id)}
                caseNumber={c.case_number}
                assignedOfficerName={c.assigned_phone ? `Station (${c.assigned_phone})` : undefined}
                onClose={() => setShowVictimChat(false)}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function ReportsRegisterContent() {
  const searchParams = useSearchParams();
  const targetCaseNum = searchParams.get("case");
  const targetAction = searchParams.get("action");

  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; text: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [investigators, setInvestigators] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"unassigned" | "assigned">("unassigned");
  const { token, user } = useAuthStore();
  const pushToast = useToast();
  const reduced = useReducedMotion();
  
const fetchAllCases = async () => {
  if (!token) {
    setCases([]);
    setError("Authentication required.");
    setLoading(false);
    return;
  }

  setLoading(true);
  setError("");

  try {
    const res = await axios.get(api("/cases/?limit=500&t=1"), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const apiCases = Array.isArray(res.data?.cases)
      ? res.data.cases
      : [];

    setCases(apiCases);
  } catch (err: any) {
    console.error("Failed to load case register", err);

    setCases([]);

    setError(
      err.response?.data?.detail ||
        "The case register couldn't be loaded from the backend."
    );
  } finally {
    setLoading(false);
  }
};
useEffect(() => {
  if (!token) return;

  fetchAllCases();

  if (user?.role === "admin") {
    axios
      .get(api("/users/"), {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
      .then((res) => {
        const users = Array.isArray(res.data)
          ? res.data
          : [];

        setInvestigators(
          users.filter(
            (u: any) =>
              u.role === "police" ||
              u.role === "cyber_cell"
          )
        );
      })
      .catch((err) => {
        console.error("Failed to load investigators", err);

        setInvestigators([]);

        pushToast(
          "danger",
          "Investigators couldn't be loaded from the backend."
        );
      });
  }
}, [token, user]);
  
  const handleAssign = async (caseNumber: string, invId: string) => {
    try {
      const formData = new FormData();
      formData.append("investigator_id", invId);
      await axios.post(api(`/cases/${caseNumber}/assign`), formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Case Assigned!");
      fetchAllCases();
    } catch (err) {
      pushToast("danger", "Failed to assign case.");
    }
  };
  
  const handleUndertake = async (caseNumber: string) => {
    if (!token) return;
    try {
      await axios.post(api(`/cases/${caseNumber}/undertake`), {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Case Undertaken!");
      fetchAllCases();
    } catch (err) {
      pushToast("danger", "Failed to undertake case.");
    }
  };

  const handleAccept = async (caseNumber: string) => {
    try {
      await axios.post(api(`/cases/${caseNumber}/accept`), {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Case Accepted!");
      fetchAllCases();
    } catch (err) {
      pushToast("danger", "Failed to accept case.");
    }
  };

  const handleCompleteInvestigation = async (caseNumber: string, formData: FormData) => {
    try {
      await axios.post(api(`/cases/${caseNumber}/complete_investigation`), formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Investigation Completed!");
      fetchAllCases();
    } catch (err) {
      pushToast("danger", "Failed to complete investigation.");
    }
  };

  const visibleCases = useMemo(() => {
    let result = [...cases];
    if (activeTab === "assigned") {
      result = result.filter((c) => c.assigned_to === user?.id || c.assigned_phone === user?.station_phone_number);
    } else if (activeTab === "unassigned") {
      result = result.filter((c) => !c.assigned_to && !c.assigned_phone);
    }

    // Automatically shift urgent nudged cases and recently claimed map radar cases to the very top!
    result.sort((a, b) => {
      const aNudged = Boolean(a.is_nudged || (targetCaseNum && a.case_number === targetCaseNum));
      const bNudged = Boolean(b.is_nudged || (targetCaseNum && b.case_number === targetCaseNum));
      if (aNudged && !bNudged) return -1;
      if (!aNudged && bNudged) return 1;

      const aClaimed = a.assignment_source === "map_radar_claim" || a.is_claimed_recently;
      const bClaimed = b.assignment_source === "map_radar_claim" || b.is_claimed_recently;
      if (aClaimed && !bClaimed) return -1;
      if (!aClaimed && bClaimed) return 1;
      const aTime = new Date(a.claimed_at || a.created_at || 0).getTime();
      const bTime = new Date(b.claimed_at || b.created_at || 0).getTime();
      return bTime - aTime;
    });

    const q = search.trim().toLowerCase();
    if (!q) return result;
    return result.filter(
      (c) =>
        (c.case_number || "").toLowerCase().includes(q) ||
        (c.scam_type_code || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q) ||
        (c.scam_text || "").toLowerCase().includes(q)
    );
  }, [cases, search, activeTab, user, targetCaseNum]);

  // Auto-Tab Switch, Auto-Expand, and Auto-Scroll on Deep Link
  useEffect(() => {
    if (!targetCaseNum || cases.length === 0) return;

    const matched = cases.find(
      (c) => c.case_number === targetCaseNum || c.id === targetCaseNum
    );
    if (matched) {
      if (matched.assigned_to) {
        setActiveTab("assigned");
      } else {
        setActiveTab("unassigned");
      }
      setExpandedId(matched.id);

      setTimeout(() => {
        const el = document.getElementById(`case-row-${matched.case_number}`);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
        }
      }, 350);
    }
  }, [targetCaseNum, cases]);

  const toggleExpanded = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
    setChatHistory([]);
    setChatQuery("");
  };

  const handleChatSubmit = async (e: React.FormEvent, caseId: string) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    const userMessage = chatQuery.trim();
    setChatHistory((prev) => [...prev, { role: "user", text: userMessage }]);
    setChatQuery("");
    setChatLoading(true);

    try {
      const res = await axios.post(
        api(`/cases/${caseId}/chat`),
        { query: userMessage },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setChatHistory((prev) => [...prev, { role: "ai", text: res.data.reply }]);
    } catch (err) {
      console.error("Chat failed", err);
      setChatHistory((prev) => [
        ...prev,
        { role: "ai", text: "The co-pilot couldn't be reached. Try again." },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="space-y-6 pt-2">
      <PageHeader
        title={user?.role === "admin" ? "Platform-wide Case Register" : "Case Register"}
        sub={user?.role === "admin" ? "Browse, review, and assign cases to investigators." : "Review and manage cases in your jurisdiction."}
        actions={
          <div className="flex flex-col sm:flex-row items-center gap-4">
            {(user?.role === "police" || user?.role === "cyber_cell") && (
              <div className="flex bg-surface-2 p-1 rounded-control">
                <button
                  onClick={() => setActiveTab("unassigned")}
                  className={cn(
                    "px-4 py-1.5 text-sm font-medium rounded-control transition-all",
                    activeTab === "unassigned" ? "bg-surface shadow-sm text-ink" : "text-ink-3 hover:text-ink"
                  )}
                >
                  Unassigned Cases
                </button>
                <button
                  onClick={() => setActiveTab("assigned")}
                  className={cn(
                    "px-4 py-1.5 text-sm font-medium rounded-control transition-all",
                    activeTab === "assigned" ? "bg-surface shadow-sm text-ink" : "text-ink-3 hover:text-ink"
                  )}
                >
                  Assigned to Me
                </button>
              </div>
            )}
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search case, type, or city"
                className="h-10 pl-10 pr-4 w-full sm:w-72 rounded-pill bg-surface text-sm text-ink placeholder:text-ink-3 border border-transparent hover:border-line focus:border-accent-text focus:outline-none transition-colors"
              />
            </div>
          </div>
        }
      />
      {error && (
  <div className="rounded-control border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
    {error}
  </div>
)}

      <Card>
        {loading ? (
          <TableSkeleton rows={8} />
        ) : visibleCases.length === 0 ? (
          <EmptyState
            icon={FileText}
            title={search ? "No matches" : "No reports on file"}
            body={
              search
                ? `Nothing matches "${search}". Try a case number, scam type, or city.`
                : "Reports will appear here as they're filed."
            }
          />
        ) : (
          <>
            {/* desktop table */}
            <div className="hidden lg:block">
              <table className="w-full text-sm text-left">
                <thead className="sticky top-0 z-10 bg-surface-2 text-ink-2">
                  <tr>
                    <th className="px-6 py-3 text-xs font-medium">Case</th>
                    <th className="px-6 py-3 text-xs font-medium">Filed</th>
                    <th className="px-6 py-3 text-xs font-medium">Type</th>
                    <th className="px-6 py-3 text-xs font-medium">Location</th>
                    <th className="px-6 py-3 text-xs font-medium text-right">Confidence</th>
                    <th className="px-6 py-3 text-xs font-medium">Priority</th>
                    <th className="px-6 py-3 text-xs font-medium">Status</th>
                    <th className="px-6 py-3" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {visibleCases.map((c) => {
                    const isNudgedOrTargeted = Boolean(
                      c.is_nudged || (targetCaseNum && c.case_number === targetCaseNum)
                    );
                    return (
                      <React.Fragment key={c.id}>
                        <tr
                          id={`case-row-${c.case_number}`}
                          className={cn(
                            "cursor-pointer transition-all duration-200 hover:bg-surface-2/60",
                            expandedId === c.id && "bg-surface-2/60",
                            isNudgedOrTargeted &&
                              "ring-2 ring-rose-500 bg-rose-500/10 shadow-[0_0_24px_rgba(244,63,94,0.35)] border-rose-500/60"
                          )}
                          onClick={() => toggleExpanded(c.id)}
                        >
                          <td className="px-6 py-4 font-medium text-ink tabular">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span>{c.case_number}</span>
                              {isNudgedOrTargeted && (
                                <span className="inline-flex items-center gap-1.5 text-[10px] font-black px-2 py-0.5 rounded-full bg-rose-600 text-white shadow-xs animate-pulse tracking-wide">
                                  <span className="w-1.5 h-1.5 rounded-full bg-white animate-ping" />
                                  <BellRing className="w-3 h-3" />
                                  <span>Admin Inquiry • Action Required</span>
                                </span>
                              )}
                              {(c.assignment_source === "map_radar_claim" || c.is_claimed_recently) && (
                                <span
                                  className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-accent border border-accent/30 shadow-xs"
                                  title={`Claimed directly from Proximity Radar ${c.claimed_at ? new Date(c.claimed_at).toLocaleTimeString() : ''}`}
                                >
                                  <Compass className="w-3 h-3 text-accent" />
                                  <span>Map Claimed</span>
                                </span>
                              )}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-ink-2">
                            {new Date(c.created_at.endsWith("Z") || c.created_at.includes("+") ? c.created_at : c.created_at + "Z").toLocaleString("en-IN", {
                              dateStyle: "short",
                              timeStyle: "short",
                            })}
                          </td>
                          <td className="px-6 py-4 capitalize">
                            {(c.scam_type_code || "Unknown").replace(/_/g, " ")}
                          </td>
                          <td className="px-6 py-4 text-ink-2">
                            {c.city ? `${c.city}${c.state ? `, ${c.state}` : ""}` : "Unknown"}
                          </td>
                          <td className="px-6 py-4 text-right font-medium tabular">
                            {c.threat_confidence_score != null ? `${(c.threat_confidence_score * 100).toFixed(1)}%` : "N/A"}
                          </td>
                          <td className="px-6 py-4">
                            <PriorityBadge priority={c.priority} />
                          </td>
                          <td className="px-6 py-4">
                            <StatusBadge status={c.status} />
                          </td>
                          <td className="px-6 py-4 text-right text-ink-3">
                            {expandedId === c.id ? (
                              <ChevronUp className="w-4 h-4 inline" />
                            ) : (
                              <ChevronDown className="w-4 h-4 inline" />
                            )}
                          </td>
                        </tr>
                        <AnimatePresence initial={false}>
                          {expandedId === c.id && (
                            <tr>
                              <td colSpan={8} className="p-0">
                                <motion.div
                                  initial={reduced ? { opacity: 0 } : { height: 0, opacity: 0 }}
                                  animate={reduced ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                                  exit={reduced ? { opacity: 0 } : { height: 0, opacity: 0 }}
                                  transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                                  className="overflow-hidden bg-bg/50"
                                >
                                  <CaseDetail
                                    c={c}
                                    chatQuery={chatQuery}
                                    setChatQuery={setChatQuery}
                                    chatHistory={chatHistory}
                                    chatLoading={chatLoading}
                                    onChatSubmit={(e) => handleChatSubmit(e, c.id)}
                                    userRole={user?.role || ""}
                                    investigators={investigators}
                                    onAssign={handleAssign}
                                    onAccept={handleAccept}
                                    onUndertake={handleUndertake}
                                    onCompleteInvestigation={handleCompleteInvestigation}
                                    token={token}
                                    isNudged={isNudgedOrTargeted}
                                    onRefresh={fetchAllCases}
                                  />
                                </motion.div>
                              </td>
                            </tr>
                          )}
                        </AnimatePresence>
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* mobile / tablet cards */}
            <ul className="lg:hidden divide-y divide-line">
              {visibleCases.map((c) => {
                const isNudgedOrTargeted = Boolean(
                  c.is_nudged || (targetCaseNum && c.case_number === targetCaseNum)
                );
                return (
                  <li
                    key={c.id}
                    id={`case-row-mobile-${c.case_number}`}
                    className={cn(
                      "transition-all duration-200",
                      isNudgedOrTargeted &&
                        "ring-2 ring-rose-500 bg-rose-500/10 shadow-[0_0_20px_rgba(244,63,94,0.25)] rounded-xl my-2"
                    )}
                  >
                    <button
                      className="w-full text-left px-4 py-4 active:bg-surface-2/60"
                      onClick={() => toggleExpanded(c.id)}
                    >
                      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-ink tabular text-sm">{c.case_number}</span>
                          {isNudgedOrTargeted && (
                            <span className="inline-flex items-center gap-1 text-[9px] font-black px-2 py-0.5 rounded-full bg-rose-600 text-white animate-pulse">
                              <BellRing className="w-2.5 h-2.5" />
                              <span>Action Required</span>
                            </span>
                          )}
                        </div>
                        <StatusBadge status={c.status} />
                      </div>
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span className="text-ink-2 capitalize">
                          {(c.scam_type_code || "Unknown").replace(/_/g, " ")}
                          {c.city ? ` · ${c.city}` : ""}
                        </span>
                        <span className="text-ink font-medium tabular">
                          {c.threat_confidence_score != null ? `${(c.threat_confidence_score * 100).toFixed(0)}%` : "N/A"}
                        </span>
                      </div>
                    </button>
                    <AnimatePresence initial={false}>
                      {expandedId === c.id && (
                        <motion.div
                          initial={reduced ? { opacity: 0 } : { height: 0, opacity: 0 }}
                          animate={reduced ? { opacity: 1 } : { height: "auto", opacity: 1 }}
                          exit={reduced ? { opacity: 0 } : { height: 0, opacity: 0 }}
                          transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                          className="overflow-hidden bg-bg/50"
                        >
                          <CaseDetail
                            c={c}
                            chatQuery={chatQuery}
                            setChatQuery={setChatQuery}
                            chatHistory={chatHistory}
                            chatLoading={chatLoading}
                            onChatSubmit={(e) => handleChatSubmit(e, c.id)}
                            userRole={user?.role || ""}
                            investigators={investigators}
                            onAssign={handleAssign}
                            onAccept={handleAccept}
                            onUndertake={handleUndertake}
                            onCompleteInvestigation={handleCompleteInvestigation}
                            token={token}
                            isNudged={isNudgedOrTargeted}
                            onRefresh={fetchAllCases}
                          />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}

export default function ReportsRegisterPage() {
  return (
    <Suspense fallback={<TableSkeleton rows={8} />}>
      <ReportsRegisterContent />
    </Suspense>
  );
}
