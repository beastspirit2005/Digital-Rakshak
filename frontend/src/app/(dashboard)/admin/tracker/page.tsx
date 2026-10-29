"use client";

import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import axios from "axios";
import { api, formatApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import {
  CheckSquare,
  Search,
  AlertTriangle,
  Clock,
  User,
  ShieldCheck,
  Building,
  PhoneCall,
  FileText,
  Download,
  MessageSquare,
  ArrowRight,
  Compass,
  RefreshCw,
  Loader2,
  BellRing,
  CheckCircle2,
  Flame,
  UserCheck, AlertCircle, X, Shield } from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { Card, Inset } from "@/components/ui/card";
import { StatusBadge, PriorityBadge, Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";
import { CaseActivityTimeline } from "@/components/case/CaseActivityTimeline";
import { CaseChatPanel } from "@/components/chat/CaseChatPanel";
import { CaseStepper } from "@/components/case/CaseStepper";

interface CaseItem {
  id: string;
  case_number: string;
  created_at: string;
  status: string;
  priority: string;
  urgency_level?: string;
  scam_type_code?: string;
  scam_text?: string;
  city?: string;
  state?: string;
  victim_phone?: string;
  victim_address?: string;
  assigned_to?: string | null;
  assigned_phone?: string | null;
  submitter_name?: string | null;
  submitter_email?: string | null;
  submitter_phone?: string | null;
  timeline_events?: any[];
  assignment_source?: string | null;
  claimed_at?: string | null;
  is_claimed_recently?: boolean;
  hours_overdue?: number;
  sla_limit_hours?: number;
  elapsed_hours?: number;
  investigator?: {
    id: string;
    name: string;
    email: string;
    phone?: string;
    station?: string;
    badge_number?: string;
    designation?: string;
    city?: string;
    state?: string;
  } | null;
  assignee_name?: string | null;
  assignee_station?: string | null;
  assignee_badge?: string | null;
  is_assigned?: boolean;
  investigation_findings?: string | null;
  investigation_attachment?: string | null;
  investigated_by?: string | null;
  investigation_completed_at?: string | null;
}

interface OfficerItem {
  id: string;
  name: string;
  email: string;
  role: string;
  station: string;
  badge_number: string;
  designation: string;
  phone?: string;
  active_cases: number;
}

const normalizeStatus = (status: string) => (status || "").toLowerCase().replace(/_/g, " ");

export default function AdminUniversalTracker() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const initialCaseNum = searchParams.get("case") || "";

  const { token, user } = useAuthStore();
  const pushToast = useToast();

  const [cases, setCases] = useState<CaseItem[]>([]);
  const [overdueMap, setOverdueMap] = useState<Record<string, any>>({});
  const [selectedCaseNum, setSelectedCaseNum] = useState<string>(initialCaseNum);
  const [activeTab, setActiveTab] = useState<"all" | "overdue" | "assigned" | "unassigned" | "investigating" | "completed" | "resolved">("all");
  const [selectedInvestigatorFilter, setSelectedInvestigatorFilter] = useState<string>("all");
  const [roster, setRoster] = useState<OfficerItem[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [nudging, setNudging] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [showChatPanel, setShowChatPanel] = useState(false);
  const [reassignModalOpen, setReassignModalOpen] = useState(false);
  const [targetInvestigatorId, setTargetInvestigatorId] = useState("");
  const [reassigning, setReassigning] = useState(false);

  // Fetch all cases & SLA overdue analytics in parallel
  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [casesRes, overdueRes, rosterRes] = await Promise.all([
        axios.get(api("/cases/?limit=100"), { headers, withCredentials: true }),
        axios.get(api("/cases/sla/overdue"), { headers, withCredentials: true }).catch(() => ({ data: { cases: [] } })),
        axios.get(api("/cases/investigators/roster"), { headers, withCredentials: true }).catch(() => ({ data: { investigators: [] } })),
      ]);

      const casesList = casesRes.data?.cases || [];
      const overdues = overdueRes.data?.cases || [];
      const officerList = rosterRes.data?.investigators || [];

      setRoster(officerList);

      // Map overdue details by case_number
      const oMap: Record<string, any> = {};
      overdues.forEach((o: any) => {
        oMap[o.case_number] = o;
      });
      setOverdueMap(oMap);
      setCases(casesList);

      // Default select initial case if present, else first case
      if (initialCaseNum && casesList.some((c: CaseItem) => c.case_number === initialCaseNum)) {
        setSelectedCaseNum(initialCaseNum);
      } else if (casesList.length > 0 && !selectedCaseNum) {
        setSelectedCaseNum(casesList[0].case_number);
      }
    } catch (err: any) {
      console.error("Failed to load universal cases:", err);
      pushToast("danger", "Could not load cases from server.");
    } finally {
      setLoading(false);
    }
  }, [token, initialCaseNum, selectedCaseNum, pushToast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Selected Case Object
  const currentCase = useMemo(() => {
    return cases.find((c) => c.case_number === selectedCaseNum) || null;
  }, [cases, selectedCaseNum]);

  const currentOverdueInfo = useMemo(() => {
    if (!currentCase) return null;
    return overdueMap[currentCase.case_number] || null;
  }, [currentCase, overdueMap]);

  // Filtered List for Left Selector Rail
  const filteredCases = useMemo(() => {
    return cases.filter((c) => {
      const s = normalizeStatus(c.status);
      const isOverdue = Boolean(overdueMap[c.case_number]);
      const isAssigned = Boolean(c.is_assigned || c.assigned_to);

      if (activeTab === "overdue" && !isOverdue) return false;
      if (activeTab === "assigned" && !isAssigned) return false;
      if (activeTab === "unassigned" && isAssigned) return false;
      if (activeTab === "investigating" && s !== "investigating") return false;
      if (activeTab === "completed" && s !== "investigation completed" && s !== "completed") return false;
      if (activeTab === "resolved" && s !== "resolved" && s !== "closed" && s !== "investigation completed" && s !== "completed") return false;

      // Investigator dropdown filter
      if (selectedInvestigatorFilter === "unassigned" && isAssigned) return false;
      if (selectedInvestigatorFilter !== "all" && selectedInvestigatorFilter !== "unassigned") {
        const matchesInv = c.assigned_to === selectedInvestigatorFilter || c.investigator?.id === selectedInvestigatorFilter;
        if (!matchesInv) return false;
      }

      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        c.case_number.toLowerCase().includes(q) ||
        (c.scam_type_code || "").toLowerCase().includes(q) ||
        (c.city || "").toLowerCase().includes(q) ||
        (c.submitter_name || "").toLowerCase().includes(q) ||
        (c.investigator?.name || "").toLowerCase().includes(q) ||
        (c.assignee_station || "").toLowerCase().includes(q)
      );
    });
  }, [cases, activeTab, search, overdueMap, selectedInvestigatorFilter]);

  const overdueCount = Object.keys(overdueMap).length;
  const assignedCount = useMemo(() => cases.filter((c) => Boolean(c.is_assigned || c.assigned_to)).length, [cases]);
  const unassignedCount = useMemo(() => cases.filter((c) => !c.is_assigned && !c.assigned_to).length, [cases]);
  const completedCount = useMemo(
    () =>
      cases.filter(
        (c) =>
          normalizeStatus(c.status) === "investigation completed" ||
          normalizeStatus(c.status) === "completed"
      ).length,
    [cases]
  );
  const resolvedCount = useMemo(
    () =>
      cases.filter(
        (c) =>
          normalizeStatus(c.status) === "resolved" ||
          normalizeStatus(c.status) === "closed"
      ).length,
    [cases]
  );

  // Handle Admin Case Resolution
  const handleAdminResolve = async (caseNumber: string) => {
    try {
      await axios.post(
        api(`/cases/${caseNumber}/resolve`),
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      pushToast("success", `Case #${caseNumber} approved & marked as RESOLVED by Administrator.`);
      fetchData();
    } catch (err: any) {
      console.error(err);
      pushToast("danger", err.response?.data?.detail || "Failed to resolve case.");
    }
  };

  // Handle Case Reassignment
  const handleReassign = async () => {
    if (!currentCase || !targetInvestigatorId) return;
    setReassigning(true);
    try {
      const formData = new FormData();
      formData.append("investigator_id", targetInvestigatorId);
      await axios.post(api(`/cases/${currentCase.case_number}/assign`), formData, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", `Case #${currentCase.case_number} assigned successfully.`);
      setReassignModalOpen(false);
      fetchData();
    } catch (err: any) {
      pushToast("danger", `Failed to assign case: ${formatApiError(err)}`);
    } finally {
      setReassigning(false);
    }
  };

  // Nudge assigned investigator
  const handleNudge = async () => {
    if (!currentCase) return;
    setNudging(true);
    try {
      await axios.post(
        api(`/cases/${currentCase.case_number}/nudge-investigator`),
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      pushToast("success", `Nudge Reminder Dispatched: Assigned officer has been notified via priority in-app alert.`);
      fetchData();
    } catch (err: any) {
      console.error("Failed to nudge officer:", err);
      pushToast("danger", `Failed to dispatch reminder: ${formatApiError(err)}`);
    } finally {
      setNudging(false);
    }
  };

  // Download Legal FIR Dossier PDF
  const handleDownloadPdf = async () => {
    if (!currentCase) return;
    setDownloadingPdf(true);
    try {
      const res = await axios.get(api(`/assistance-requests/${currentCase.case_number}/dossier-pdf`), {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
        withCredentials: true,
      });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Universal_Dossier_${currentCase.case_number}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
      pushToast("success", "Dossier PDF downloaded.");
    } catch (err: any) {
      pushToast("danger", "Could not generate PDF dossier.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="space-y-6 pt-2 font-sans pb-16">
      <PageHeader
        title="Universal Investigation Tracker & SLA Monitor"
        sub="Platform-wide investigation progression, timeline verification, and officer SLA monitoring."
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={fetchData}
              className="inline-flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Refresh Telemetry</span>
            </Button>
          </div>
        }
      />

      {/* Main Split Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: Case Selector & Filters */}
        <div className="lg:col-span-4 space-y-3">
          <Card className="p-4 space-y-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-4 h-4 text-ink-3 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search case #, type, city, or victim..."
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-surface-2 border border-line text-ink placeholder:text-ink-3 focus:outline-none focus:border-accent"
              />
            </div>

            {/* Investigator Filter Dropdown */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-ink-3">
                <span className="flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3 text-accent" />
                  Investigator Filter
                </span>
                {selectedInvestigatorFilter !== "all" && (
                  <button
                    onClick={() => setSelectedInvestigatorFilter("all")}
                    className="text-accent hover:underline capitalize"
                  >
                    Reset
                  </button>
                )}
              </div>
              <select
                value={selectedInvestigatorFilter}
                onChange={(e) => setSelectedInvestigatorFilter(e.target.value)}
                className="w-full text-xs p-2 rounded-xl bg-surface-2 border border-line text-ink font-medium focus:outline-none focus:border-accent"
              >
                <option value="all">All Officers ({roster.length} registered)</option>
                <option value="unassigned">[Unassigned] Cases ({unassignedCount})</option>
                {roster.map((off) => (
                  <option key={off.id} value={off.id}>
                    Officer: {off.name} ({off.badge_number && off.badge_number !== "N/A" ? `#${off.badge_number}` : off.station}) • {off.active_cases} active
                  </option>
                ))}
              </select>
            </div>

            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-1 border-b border-line pb-2">
              <button
                onClick={() => setActiveTab("all")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === "all" ? "bg-accent text-accent-contrast shadow-xs" : "text-ink-3 hover:text-ink"
                }`}
              >
                All Cases ({cases.length})
              </button>
              <button
                onClick={() => setActiveTab("overdue")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                  activeTab === "overdue"
                    ? "bg-rose-600 text-white shadow-xs"
                    : overdueCount > 0
                    ? "text-rose-500 bg-rose-500/10 hover:bg-rose-500/20"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                <Clock className="w-3 h-3" />
                <span>Overdue ({overdueCount})</span>
              </button>
              <button
                onClick={() => setActiveTab("assigned")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === "assigned" ? "bg-accent text-accent-contrast" : "text-ink-3 hover:text-ink"
                }`}
              >
                Assigned ({assignedCount})
              </button>
              <button
                onClick={() => setActiveTab("unassigned")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === "unassigned" ? "bg-amber-600 text-white shadow-xs" : "text-amber-500/80 hover:text-amber-500"
                }`}
              >
                Unassigned ({unassignedCount})
              </button>
              <button
                onClick={() => setActiveTab("completed")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1 ${
                  activeTab === "completed"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : completedCount > 0
                    ? "text-emerald-500 bg-emerald-500/10 hover:bg-emerald-500/20"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                <CheckCircle2 className="w-3 h-3" />
                <span>Completed ({completedCount})</span>
              </button>
              <button
                onClick={() => setActiveTab("resolved")}
                className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors ${
                  activeTab === "resolved" ? "bg-accent text-accent-contrast" : "text-ink-3 hover:text-ink"
                }`}
              >
                Resolved ({resolvedCount})
              </button>
            </div>

            {/* Scrollable Case List */}
            <div className="max-h-[560px] overflow-y-auto space-y-2 pr-1 divide-y divide-line/40">
              {loading ? (
                <div className="p-8 text-center text-xs text-ink-3 space-y-2">
                  <Loader2 className="w-5 h-5 animate-spin mx-auto text-accent" />
                  <span>Loading universal case register...</span>
                </div>
              ) : filteredCases.length === 0 ? (
                <div className="p-8 text-center text-xs text-ink-3">
                  No cases match the selected filter.
                </div>
              ) : (
                filteredCases.map((c) => {
                  const isSelected = c.case_number === selectedCaseNum;
                  const isOverdue = Boolean(overdueMap[c.case_number]);
                  const isMapClaim = c.assignment_source === "map_radar_claim" || c.is_claimed_recently;

                  return (
                    <div
                      key={c.id}
                      onClick={() => setSelectedCaseNum(c.case_number)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer text-xs space-y-1 ${
                        isSelected
                          ? "bg-accent/10 border-accent text-ink shadow-sm ring-1 ring-accent"
                          : "bg-surface hover:bg-surface-2 border-line text-ink-2"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="font-mono font-bold text-accent truncate">
                            {c.case_number}
                          </span>
                          {isMapClaim && (
                            <span className="inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.2 rounded bg-cyan-500/15 text-accent border border-accent/25 shrink-0">
                              <Compass className="w-2.5 h-2.5" />
                              <span>Map</span>
                            </span>
                          )}
                        </div>
                        <StatusBadge status={c.status} className="text-[10px] scale-90 origin-right" />
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-ink-3">
                        <span className="truncate capitalize font-medium">{c.scam_type_code || "Cyber Incident"}</span>
                        <span>{c.city || "Unknown City"}</span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] pt-1 border-t border-line/30">
                        {c.investigator?.name ? (
                          <span className="inline-flex items-center gap-1 font-semibold text-emerald-600 dark:text-emerald-400 truncate max-w-[170px]" title={`${c.investigator.name} (${c.investigator.station || "Cyber Unit"})`}>
                            <ShieldCheck className="w-3 h-3 shrink-0" />
                            <span className="truncate">{c.investigator.name}</span>
                          </span>
                        ) : c.assigned_to ? (
                          <span className="inline-flex items-center gap-1 font-medium text-emerald-600/80 dark:text-emerald-400/80">
                            <ShieldCheck className="w-3 h-3 shrink-0" />
                            <span>Assigned</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-1.5 py-0.2 rounded border border-amber-500/20">
                            <span className="inline-flex items-center gap-1 text-amber-400 font-medium"><AlertTriangle className="w-3.5 h-3.5 shrink-0" />Unassigned</span>
                          </span>
                        )}
                        {c.investigator?.station && (
                          <span className="text-[10px] text-ink-3 truncate max-w-[110px]" title={c.investigator.station}>
                            {c.investigator.station.replace("Police Station", "PS")}
                          </span>
                        )}
                      </div>

                      {isOverdue && (
                        <div className="flex items-center gap-1 text-[10px] font-bold text-rose-500 pt-0.5">
                          <Clock className="w-3 h-3 shrink-0" />
                          <span>SLA Breached (+{overdueMap[c.case_number].hours_overdue}h)</span>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </Card>
        </div>

        {/* Right Column: Case Deep Tracker Dossier */}
        <div className="lg:col-span-8 space-y-4">
          {!currentCase ? (
            <Card className="p-12 text-center text-ink-3 space-y-3">
              <CheckSquare className="w-10 h-10 mx-auto text-ink-3" />
              <h3 className="font-bold text-sm text-ink">Select a Case to Inspect</h3>
              <p className="text-xs max-w-sm mx-auto">
                Select any incident from the register on the left to review its investigation stepper, activity timeline, and SLA telemetry.
              </p>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Overdue Warning Alert Banner if SLA is breached */}
              {currentOverdueInfo && (
                <div className="p-4 rounded-2xl bg-rose-500/15 border border-rose-500/40 text-ink shadow-sm space-y-2 animate-in fade-in">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <div className="w-9 h-9 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-center justify-center shrink-0 mt-0.5">
                        <Flame className="w-5 h-5 text-rose-500 animate-pulse" />
                      </div>
                      <div>
                        <h4 className="text-sm font-bold text-rose-500 flex items-center gap-1.5">
                          <span>SLA Overdue Investigation Alert</span>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-600 text-white font-black">
                            +{currentOverdueInfo.hours_overdue}h OVERDUE
                          </span>
                        </h4>
                        <p className="text-xs text-ink-2 mt-0.5">
                          Elapsed investigation time: <strong>{currentOverdueInfo.elapsed_hours}h</strong> (Allowed {currentOverdueInfo.sla_limit_hours}h SLA). Officer: <strong>{currentOverdueInfo.investigator?.name || "Assigned Officer"}</strong>.
                        </p>
                      </div>
                    </div>

                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleNudge}
                      disabled={nudging}
                      className="bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs inline-flex items-center gap-1.5 shrink-0 shadow-md"
                    >
                      {nudging ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <BellRing className="w-3.5 h-3.5" />
                      )}
                      <span>Nudge Investigator</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* Top Dossier Card */}
              <Card className="p-6 space-y-6">
                {/* Header Information */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-line">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="font-mono text-base font-black text-ink">{currentCase.case_number}</span>
                      <StatusBadge status={currentCase.status} />
                      <PriorityBadge priority={currentCase.priority} />
                      {currentCase.assignment_source === "map_radar_claim" && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-cyan-500/15 text-accent border border-accent/30">
                          <Compass className="w-3 h-3" />
                          <span>Map Claimed</span>
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-ink-3">
                      Filed on {new Date(currentCase.created_at).toLocaleString("en-IN", { dateStyle: "long", timeStyle: "short" })} • Category: <strong className="text-ink">{currentCase.scam_type_code || "Cyber Fraud"}</strong>
                    </p>
                  </div>

                  {/* Top Action Buttons */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setShowChatPanel(!showChatPanel)}
                      className="inline-flex items-center gap-1.5 border-accent/40 text-accent"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>{showChatPanel ? "Hide Chat" : "Monitor Case Chat"}</span>
                    </Button>

                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleDownloadPdf}
                      disabled={downloadingPdf}
                      className="inline-flex items-center gap-1.5"
                    >
                      {downloadingPdf ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5" />
                      )}
                      <span>FIR Dossier PDF</span>
                    </Button>
                  </div>
                </div>

                {/* Universal Visual Case Stepper */}
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3">
                    Investigation Progression Stepper
                  </span>
                  <CaseStepper status={currentCase.status} />
                </div>

                {/* Official Investigation Report Callout for Admin */}
                {(normalizeStatus(currentCase.status) === "investigation completed" ||
                  normalizeStatus(currentCase.status) === "completed" ||
                  Boolean(currentCase.investigation_findings || currentCase.timeline_events?.some((e: any) => e.action === "Investigation Completed"))) && (
                  <div className="p-4 rounded-2xl border border-emerald-500/40 bg-gradient-to-r from-emerald-500/15 via-emerald-500/10 to-transparent shadow-sm space-y-3 animate-in fade-in">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400">
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-emerald-400 uppercase tracking-wide">
                              Official Investigation Concluded
                            </h4>
                            <span className="text-[10px] font-black px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                              DOCKET FILED
                            </span>
                          </div>
                          <p className="text-[11px] text-ink-3">
                            Investigating officer {currentCase.investigated_by || currentCase.investigator?.name || "in charge"} has submitted formal findings and evidentiary closing notes.
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {normalizeStatus(currentCase.status) !== "resolved" && normalizeStatus(currentCase.status) !== "closed" && (
                          <Button
                            variant="primary"
                            size="sm"
                            className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md"
                            onClick={() => handleAdminResolve(currentCase.case_number)}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                            Approve & Mark Resolved
                          </Button>
                        )}
                      </div>
                    </div>

                    {/* Findings Content */}
                    <div className="p-3.5 rounded-xl bg-surface border border-line space-y-1.5">
                      <p className="text-[10px] font-bold text-ink-3 uppercase tracking-wider flex items-center justify-between">
                        <span>Submitted Evidentiary Remarks & Findings:</span>
                        {currentCase.investigation_completed_at && (
                          <span className="font-mono text-[10px] text-ink-3">
                            {new Date(currentCase.investigation_completed_at).toLocaleString("en-IN")}
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-ink leading-relaxed whitespace-pre-wrap">
                        {currentCase.investigation_findings ||
                          currentCase.timeline_events?.slice().reverse().find((e: any) => e.action === "Investigation Completed")?.remark ||
                          "Officer concluded investigation and submitted findings to central registry."}
                      </p>
                    </div>

                    {/* Attachment if present */}
                    {(currentCase.investigation_attachment ||
                      currentCase.timeline_events?.slice().reverse().find((e: any) => e.action === "Investigation Completed")?.attachment) && (
                      <div className="flex items-center gap-2 pt-1">
                        <a
                          href={currentCase.investigation_attachment || currentCase.timeline_events?.slice().reverse().find((e: any) => e.action === "Investigation Completed")?.attachment}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent-text hover:underline bg-accent/10 px-3 py-1.5 rounded-lg border border-accent/20"
                        >
                          <Download className="w-3.5 h-3.5" />
                          Download Submitted Evidence / Final Report
                        </a>
                      </div>
                    )}
                  </div>
                )}

                {/* Dual Dossier Cards: Citizen vs Officer */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Citizen Complainant */}
                  <Inset className="p-4 space-y-2">
                    <div className="flex items-center justify-between text-xs font-bold text-ink pb-1 border-b border-line">
                      <span className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-accent" />
                        Complainant (Citizen)
                      </span>
                      <span className="text-[10px] text-ink-3 font-mono">Victim</span>
                    </div>
                    <div className="space-y-1 text-xs">
                      <p><span className="text-ink-3">Name:</span> <strong className="text-ink">{currentCase.submitter_name || "Complainant"}</strong></p>
                      <p><span className="text-ink-3">Email:</span> <span className="font-mono text-ink-2">{currentCase.submitter_email || "N/A"}</span></p>
                      <p><span className="text-ink-3">Phone:</span> <span className="font-mono text-ink-2">{currentCase.victim_phone || currentCase.submitter_phone || "Protected under BSA"}</span></p>
                      <p><span className="text-ink-3">Jurisdiction:</span> <span className="text-ink-2">{currentCase.city || "Unknown"}, {currentCase.state || "India"}</span></p>
                    </div>
                  </Inset>

                  {/* Assigned Investigation Officer */}
                  <Inset className="p-4 space-y-3">
                    <div className="flex items-center justify-between text-xs font-bold text-ink pb-1 border-b border-line">
                      <span className="flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                        Assigned Investigation Officer
                      </span>
                      <span className="text-[10px] text-ink-3 font-mono">
                        {currentCase.investigator ? "Active Lead" : currentCase.assigned_to ? "Assigned" : "Unassigned"}
                      </span>
                    </div>

                    {currentCase.investigator ? (
                      <div className="space-y-2 text-xs">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <p className="font-bold text-ink text-sm flex items-center gap-1.5">
                              <span>{currentCase.investigator.name}</span>
                              {currentCase.investigator.badge_number && currentCase.investigator.badge_number !== "N/A" && (
                                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-surface-3 text-ink-2 font-medium">
                                  #{currentCase.investigator.badge_number}
                                </span>
                              )}
                            </p>
                            <p className="text-[11px] text-ink-3">
                              {currentCase.investigator.designation || "Investigating Officer"} • {currentCase.investigator.station || "Cyber Crime Station"}
                            </p>
                          </div>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              setTargetInvestigatorId("");
                              setReassignModalOpen(true);
                            }}
                            className="text-[11px] h-7 px-2 shrink-0 border-accent/40 text-accent hover:bg-accent/10"
                          >
                            Reassign
                          </Button>
                        </div>

                        <div className="pt-1 space-y-1 text-ink-2">
                          <p><span className="text-ink-3">Official Email:</span> <span className="font-mono text-ink">{currentCase.investigator.email || "N/A"}</span></p>
                          <p><span className="text-ink-3">Duty Contact:</span> <span className="font-mono text-ink">{currentCase.investigator.phone || currentCase.assigned_phone || "Station Desk Direct"}</span></p>
                          <p><span className="text-ink-3">Acquisition Origin:</span> <strong className="text-accent">{currentCase.assignment_source === "map_radar_claim" ? "Claimed via Proximity Radar" : "Admin HQ Dispatch"}</strong></p>
                          {currentCase.claimed_at && (
                            <p><span className="text-ink-3">Claimed Timestamp:</span> <span className="font-mono text-[11px] text-ink-2">{new Date(currentCase.claimed_at).toLocaleString("en-IN")}</span></p>
                          )}
                        </div>
                      </div>
                    ) : (
                      <div className="py-2 text-center space-y-2">
                        <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-600 dark:text-amber-400 font-medium">
                          <span className="inline-flex items-center gap-1.5"><AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />No investigator has taken charge of this incident yet.</span>
                        </div>
                        <Button
                          variant="primary"
                          size="sm"
                          onClick={() => {
                            setTargetInvestigatorId("");
                            setReassignModalOpen(true);
                          }}
                          className="w-full text-xs font-bold"
                        >
                          Assign Lead Investigator
                        </Button>
                      </div>
                    )}
                  </Inset>
                </div>

                {/* Victim Incident Statement */}
                {currentCase.scam_text && (
                  <div className="space-y-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3">
                      Original Complainant Incident Statement
                    </span>
                    <p className="text-xs text-ink-2 p-3 rounded-xl bg-surface-2 border border-line leading-relaxed italic">
                      &ldquo;{currentCase.scam_text}&rdquo;
                    </p>
                  </div>
                )}

                {/* Case Activity Timeline */}
                {currentCase.timeline_events && currentCase.timeline_events.length > 0 && (
                  <div className="space-y-2 pt-2 border-t border-line">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-ink-3">
                      Chronological Investigation Activity Log
                    </span>
                    <CaseActivityTimeline events={currentCase.timeline_events} />
                  </div>
                )}
              </Card>

              {/* Embedded Case Chat Panel for Admin Oversight */}
              {showChatPanel && (
                <div className="h-[460px] rounded-2xl overflow-hidden border border-line shadow-2xl animate-in fade-in">
                  <CaseChatPanel
                    caseId={currentCase.id}
                    caseNumber={currentCase.case_number}
                    assignedOfficerName={currentOverdueInfo?.investigator?.name || "Assigned Officer"}
                    onClose={() => setShowChatPanel(false)}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>
      {/* Reassign / Assign Officer Modal */}
      {reassignModalOpen && currentCase && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4 animate-in fade-in">
          <div className="w-full max-w-md p-6 space-y-4 bg-surface border border-line rounded-2xl shadow-2xl text-ink relative z-10">
            <div className="flex items-center justify-between pb-3 border-b border-line">
              <h3 className="font-bold text-sm text-ink flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-accent" />
                <span>{currentCase.investigator ? "Reassign Case to Officer" : "Assign Case to Officer"}</span>
              </h3>
              <button 
                onClick={() => setReassignModalOpen(false)} 
                className="w-7 h-7 rounded-lg flex items-center justify-center text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors font-bold text-sm"
              ><X className="w-4 h-4" /></button>
            </div>

            <p className="text-xs text-ink-2 leading-relaxed">
              Select an authorized investigator from the active cyber crime roster to take charge of Case <strong>{currentCase.case_number}</strong>.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-ink">Select Investigator</label>
              <select
                className="w-full text-xs p-2.5 rounded-xl bg-surface-2 border border-line text-ink font-medium focus:outline-none focus:border-accent"
                value={targetInvestigatorId}
                onChange={(e) => setTargetInvestigatorId(e.target.value)}
              >
                <option value="">-- Choose an Officer from Roster --</option>
                {roster.map((off) => (
                  <option key={off.id} value={off.id}>
                    {off.name} ({off.badge_number && off.badge_number !== "N/A" ? `#${off.badge_number}` : off.email}) — {off.station}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-line">
              <Button variant="secondary" size="sm" onClick={() => setReassignModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!targetInvestigatorId || reassigning}
                onClick={handleReassign}
                className="font-bold text-xs"
              >
                {reassigning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : "Confirm Assignment"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}