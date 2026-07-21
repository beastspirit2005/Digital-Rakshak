"use client";

import { api } from "@/lib/api";
import React, { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";
import { Search, FileText, ChevronDown, ChevronUp, Send } from "lucide-react";
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
}) {
  const [selectedInv, setSelectedInv] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState<string | null>(null);
  const [osintFlags, setOsintFlags] = useState<any[] | null>(null);
  const [scanningOsint, setScanningOsint] = useState(false);
  const [remark, setRemark] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);
  const pushToast = useToast();
  
  const loadEvidence = async () => {
    try {
      const res = await axios.get(api(`/cases/${c.case_number}/evidence`), {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      // Check if the response is JSON (contains a signed URL) or a raw blob
      const contentType = String(res.headers['content-type'] || '');
      if (contentType.includes('application/json')) {
        const text = await res.data.text();
        const json = JSON.parse(text);
        if (json.url) {
          setEvidenceUrl(json.url);
          return;
        }
      }
      const url = window.URL.createObjectURL(res.data);
      setEvidenceUrl(url);
    } catch (err) {
      pushToast("danger", "No evidence found or failed to load.");
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
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4 sm:p-6">
      <div className="lg:col-span-2 space-y-4">
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
           <Button variant="secondary" size="sm" onClick={loadEvidence}>View Attached Evidence</Button>
           <Button variant="secondary" size="sm" onClick={runOsintScan} loading={scanningOsint} className="border-red-500/30 text-red-500 hover:bg-red-500/10 hover:text-red-600">
             Scan OSINT Flags
           </Button>
        </div>
        
        {evidenceUrl && (
          <div className="mt-4">
            <a href={evidenceUrl} target="_blank" rel="noreferrer" className="text-accent-text text-sm underline">Open Evidence File</a>
          </div>
        )}

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
             <Button variant="primary" className="w-full" onClick={() => onAccept?.(c.case_number)}>
                Accept Case for Investigation
             </Button>
          )}
          {(userRole === "police" || userRole === "cyber_cell") && (c.status === "submitted" || c.status === "under_review" || c.status === "escalated") && (
             <Button variant="primary" className="w-full" onClick={() => onUndertake?.(c.case_number)}>
                Undertake Case
             </Button>
          )}
          {(userRole === "police" || userRole === "cyber_cell") && c.status === "investigating" && (
             <div className="space-y-3">
               <textarea 
                 placeholder="Investigation remarks (required)..." 
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
                 className="w-full bg-success hover:bg-success/90" 
                 disabled={!remark.trim()}
                 onClick={() => {
                   const fd = new FormData();
                   fd.append("remark", remark);
                   if (attachment) fd.append("file", attachment);
                   onCompleteInvestigation?.(c.case_number, fd);
                 }}
               >
                  Complete Investigation
               </Button>
             </div>
          )}
          {userRole !== "admin" && userRole !== "police" && userRole !== "cyber_cell" && (
             <p className="text-xs text-ink-3">No actions available.</p>
          )}
        </Inset>

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
      </div>
    </div>
  );
}

export default function ReportsRegisterPage() {
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
    let result = cases;
    if (activeTab === "assigned") {
      result = result.filter((c) => c.assigned_to === user?.id || c.assigned_phone === user?.station_phone_number);
    } else if (activeTab === "unassigned") {
      result = result.filter((c) => !c.assigned_to && !c.assigned_phone);
    }
    const q = search.trim().toLowerCase();
    if (!q) return result;
    return result.filter(
      (c) =>
        (c.case_number || "").toLowerCase().includes(q) ||
        (c.scam_type_code || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q) ||
        (c.scam_text || "").toLowerCase().includes(q)
    );
  }, [cases, search, activeTab, user]);

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
                  {visibleCases.map((c) => (
                    <React.Fragment key={c.id}>
                      <tr
                        className={cn(
                          "cursor-pointer transition-colors duration-150 hover:bg-surface-2/60",
                          expandedId === c.id && "bg-surface-2/60"
                        )}
                        onClick={() => toggleExpanded(c.id)}
                      >
                        <td className="px-6 py-4 font-medium text-ink tabular">{c.case_number}</td>
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
                                />
                              </motion.div>
                            </td>
                          </tr>
                        )}
                      </AnimatePresence>
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>

            {/* mobile / tablet cards */}
            <ul className="lg:hidden divide-y divide-line">
              {visibleCases.map((c) => (
                <li key={c.id}>
                  <button
                    className="w-full text-left px-4 py-4 active:bg-surface-2/60"
                    onClick={() => toggleExpanded(c.id)}
                  >
                    <div className="flex items-center justify-between gap-3 mb-2">
                      <span className="font-medium text-ink tabular text-sm">{c.case_number}</span>
                      <StatusBadge status={c.status} />
                    </div>
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="text-ink-2 capitalize">
                        {(c.scam_type_code || "Unknown").replace(/_/g, " ")}
                        {c.city ? ` · ${c.city}` : ""}
                      </span>
                      <span className="text-ink font-medium tabular">
                        {(c.threat_confidence_score * 100).toFixed(0)}%
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
                          token={token}
                        />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  );
}
