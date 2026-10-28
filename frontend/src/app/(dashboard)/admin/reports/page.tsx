"use client";

import { api } from "@/lib/api";
import React, { useEffect, useMemo, useState } from "react";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";
import { Search, FileText, ChevronDown, ChevronUp, Send, ShieldCheck, CheckCircle2, Download } from "lucide-react";
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
  onResolve,
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
  onResolve?: (caseId: string) => void;
  token: string | null;
}) {
  const [selectedInv, setSelectedInv] = useState("");
  const [osintFlags, setOsintFlags] = useState<any[] | null>(null);
  const [scanningOsint, setScanningOsint] = useState(false);
  const pushToast = useToast();

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
      <div className="col-span-full pb-2">
        <CaseStepper status={c.status} />
      </div>

      <div className="lg:col-span-2 space-y-4">
        {/* Official Police Investigation Concluded & Findings Report */}
        {(c.status === "investigation_completed" || c.investigation_findings) && (
          <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 dark:bg-emerald-950/20 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-emerald-500/20 pb-2.5">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-ink flex items-center gap-2">
                    <span>Official Police Investigation Concluded</span>
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500 text-white font-semibold">
                      Action Report
                    </span>
                  </h4>
                  <p className="text-xs text-ink-3">
                    Investigated by: <strong className="text-ink">{c.investigated_by || c.investigator?.name || "Lead Officer"}</strong>
                    {c.investigation_completed_at && (
                      <span> • {new Date(c.investigation_completed_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" })}</span>
                    )}
                  </p>
                </div>
              </div>
              {onResolve && c.status !== "resolved" && (
                <Button
                  variant="primary"
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs shrink-0"
                  onClick={() => onResolve(c.case_number)}
                >
                  Approve & Mark Case Resolved
                </Button>
              )}
            </div>

            <div>
              <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
                Submitted Findings & Conclusions:
              </p>
              <p className="text-sm text-ink whitespace-pre-wrap leading-relaxed bg-surface/70 p-3 rounded-lg border border-line">
                {c.investigation_findings || "No detailed remarks provided."}
              </p>
            </div>

            {c.investigation_attachment && (
              <div className="flex items-center justify-between p-2.5 bg-surface rounded-lg border border-line">
                <div className="flex items-center gap-2 truncate">
                  <FileText className="w-4 h-4 text-accent shrink-0" />
                  <span className="text-xs font-mono text-ink truncate">
                    Evidentiary Attachment: {c.investigation_attachment.split("/").pop()}
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

        {c.timeline_events && c.timeline_events.length > 0 && (
          <CaseActivityTimeline events={c.timeline_events} />
        )}

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
          <p className="text-xs text-ink-3 mb-3">Citizen Profile (Submitter)</p>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Name</dt>
              <dd className="text-ink font-medium">{c.submitter_name || "Unknown"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Email</dt>
              <dd className="text-ink truncate">{c.submitter_email || "N/A"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Phone</dt>
              <dd className="text-ink">{c.victim_phone || c.submitter_phone || "Not provided"}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-ink-2">Address</dt>
              <dd className="text-ink text-right">{c.victim_address || "Not provided"}</dd>
            </div>
          </dl>
        </Inset>
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
        
        <Inset className="p-4">
          <p className="text-xs text-ink-3 mb-3">Officer Assignment & Actions</p>
          {c.investigator ? (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs space-y-1">
                <div className="flex items-center justify-between font-bold text-ink">
                  <span className="flex items-center gap-1.5">
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    <span>{c.investigator.name}</span>
                  </span>
                  {c.investigator.badge_number && c.investigator.badge_number !== "N/A" && (
                    <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-3 text-ink-2">
                      #{c.investigator.badge_number}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-ink-2">
                  {c.investigator.designation || "Investigating Officer"} • {c.investigator.station || "Cyber Crime Police Station"}
                </p>
                <div className="pt-1 text-[11px] text-ink-3 space-y-0.5">
                  <p>Contact: <span className="font-mono text-ink">{c.investigator.phone || c.assigned_phone || "Station Direct"}</span></p>
                  <p>Email: <span className="font-mono text-ink">{c.investigator.email || "N/A"}</span></p>
                  <p className="text-accent font-semibold pt-0.5">
                    Origin: {c.assignment_source === "map_radar_claim" ? "Claimed via Proximity Radar" : "Admin HQ Dispatch"}
                  </p>
                </div>
              </div>

              {userRole === "admin" && (
                <div className="space-y-2 pt-1 border-t border-line/40">
                  <p className="text-[11px] font-bold text-ink">Reassign to another officer:</p>
                  <select 
                    className="w-full text-xs p-2 rounded-control bg-surface-2 border border-line text-ink"
                    value={selectedInv}
                    onChange={(e) => setSelectedInv(e.target.value)}
                  >
                    <option value="">Select Officer to Reassign...</option>
                    {investigators.map((inv) => (
                       <option key={inv.id} value={inv.id}>{inv.full_name} ({inv.role})</option>
                    ))}
                  </select>
                  <Button size="sm" variant="secondary" className="w-full text-xs font-bold" disabled={!selectedInv} onClick={() => onAssign(c.case_number, selectedInv)}>
                     Confirm Reassignment
                  </Button>
                </div>
              )}
            </div>
          ) : userRole === "admin" ? (
            <div className="space-y-3">
               <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400 font-medium">
                 ⚠️ No officer assigned to this case.
               </div>
               <select 
                 className="w-full text-xs p-2 rounded-control bg-surface-2 border border-line text-ink"
                 value={selectedInv}
                 onChange={(e) => setSelectedInv(e.target.value)}
               >
                 <option value="">Select Nearest Police Station / Officer...</option>
                 {investigators.map((inv) => (
                    <option key={inv.id} value={inv.id}>{inv.full_name} ({inv.role})</option>
                 ))}
               </select>
               <Button size="sm" variant="primary" className="w-full text-xs font-bold" disabled={!selectedInv} onClick={() => onAssign(c.case_number, selectedInv)}>
                  Assign Lead Officer
               </Button>
            </div>
          ) : (
             <p className="text-xs text-ink-3">Case is pending assignment.</p>
          )}
        </Inset>

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
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterAssignment, setFilterAssignment] = useState<"all" | "assigned" | "unassigned">("all");
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<{ role: string; text: string }[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [investigators, setInvestigators] = useState<any[]>([]);
  const { token, user } = useAuthStore();
  const pushToast = useToast();
  const reduced = useReducedMotion();
  
  const fetchAllCases = async () => {
    try {
      const res = await axios.get(api("/cases/?limit=500&t=1"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      setCases(res.data.cases);
    } catch (err) {
      console.error("Failed to load cases", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchAllCases();
    if (token && user?.role === "admin") {
       axios.get(api("/users/"), { headers: { Authorization: `Bearer ${token}` }})
         .then(res => setInvestigators(res.data.filter((u: any) => u.role === "police" || u.role === "cyber_cell")))
         .catch(err => console.error("Failed to fetch investigators"));
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

  const handleResolve = async (caseNumber: string) => {
    try {
      await axios.post(api(`/cases/${caseNumber}/resolve`), {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Case marked as Resolved!");
      fetchAllCases();
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Failed to resolve case.");
    }
  };

  const visibleCases = useMemo(() => {
    let result = cases;
    if (filterAssignment === "assigned") {
      result = result.filter((c) => Boolean(c.is_assigned || c.assigned_to));
    } else if (filterAssignment === "unassigned") {
      result = result.filter((c) => !c.is_assigned && !c.assigned_to);
    }

    const q = search.trim().toLowerCase();
    if (!q) return result;
    return result.filter(
      (c) =>
        (c.case_number || "").toLowerCase().includes(q) ||
        (c.scam_type_code || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q) ||
        (c.investigator?.name || "").toLowerCase().includes(q) ||
        (c.investigator?.station || "").toLowerCase().includes(q)
    );
  }, [cases, search, filterAssignment]);

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
        title="Registered Reports"
        sub="Browse all citizen reports and assign them to the nearest police station."
        actions={
          <div className="flex flex-col sm:flex-row items-center gap-3">
            <div className="flex items-center gap-1 bg-surface-2 p-1 rounded-pill border border-line">
              <button
                onClick={() => setFilterAssignment("all")}
                className={cn(
                  "px-3 py-1 rounded-pill text-xs font-semibold transition-colors",
                  filterAssignment === "all" ? "bg-accent text-accent-contrast shadow-xs" : "text-ink-3 hover:text-ink"
                )}
              >
                All Cases ({cases.length})
              </button>
              <button
                onClick={() => setFilterAssignment("assigned")}
                className={cn(
                  "px-3 py-1 rounded-pill text-xs font-semibold transition-colors",
                  filterAssignment === "assigned" ? "bg-accent text-accent-contrast shadow-xs" : "text-ink-3 hover:text-ink"
                )}
              >
                Assigned
              </button>
              <button
                onClick={() => setFilterAssignment("unassigned")}
                className={cn(
                  "px-3 py-1 rounded-pill text-xs font-semibold transition-colors",
                  filterAssignment === "unassigned" ? "bg-amber-600 text-white shadow-xs" : "text-amber-500/80 hover:text-amber-500"
                )}
              >
                Unassigned
              </button>
            </div>

            <div className="relative">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-ink-3" />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search case, officer, city..."
                className="h-10 pl-10 pr-4 w-full sm:w-64 rounded-pill bg-surface text-sm text-ink placeholder:text-ink-3 border border-transparent hover:border-line focus:border-accent-text focus:outline-none transition-colors"
              />
            </div>
          </div>
        }
      />

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
                    <th className="px-6 py-3 text-xs font-medium">Assigned Officer</th>
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
                        <td className="px-6 py-4 whitespace-nowrap text-xs">
                          {c.investigator ? (
                            <div>
                              <p className="font-semibold text-ink flex items-center gap-1">
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                                <span className="truncate max-w-[130px]" title={c.investigator.name}>{c.investigator.name}</span>
                              </p>
                              <p className="text-[10px] text-ink-3 truncate max-w-[130px]" title={c.investigator.station}>
                                {c.investigator.station || "Cyber Unit"}
                              </p>
                            </div>
                          ) : c.assigned_to ? (
                            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium text-xs">
                              <ShieldCheck className="w-3.5 h-3.5" />
                              <span>Assigned</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                              Unassigned
                            </span>
                          )}
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
                            <td colSpan={9} className="p-0">
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
                                  userRole={user?.role}
                                  investigators={investigators}
                                  onAssign={handleAssign}
                                  onAccept={() => {}}
                                  onResolve={handleResolve}
                                  token={token}/>
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
                          userRole={user?.role}
                          investigators={investigators}
                          onAssign={handleAssign}
                          onResolve={handleResolve}
                          token={token}/>
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
