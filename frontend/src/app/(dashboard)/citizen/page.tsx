"use client";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import Link from "next/link";
import axios from "axios";
import {
  FileText,
  Plus,
  AlertTriangle,
  PhoneCall,
  CheckCircle2,
  Download,
  MapPin,
  ArrowRight,
  MessageSquare,
  Compass,
  Navigation,
  Loader2,
  Building,
  ExternalLink,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { CaseChatPanel } from "@/components/chat/CaseChatPanel";
import { OfficialLocationItem } from "@/components/map/cyber-cell-map";
import { CaseStepper } from "@/components/case/CaseStepper";

const CyberCellMap = dynamic(
  () => import("@/components/map/cyber-cell-map"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-80 rounded-2xl bg-surface-2 border border-line flex flex-col items-center justify-center gap-2">
        <Loader2 className="w-6 h-6 animate-spin text-warning" />
        <span className="text-xs text-ink-3">Loading Cyber Police Cell Locator Map...</span>
      </div>
    ),
  }
);
import { useAuthStore } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { StatBlock } from "@/components/ui/stat";
import { StatusBadge, PriorityBadge } from "@/components/ui/badge";
import { StatSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";
import { CaseActivityTimeline } from "@/components/case/CaseActivityTimeline";

interface Case {
  id: string | number;
  case_number: string;
  created_at: string;
  scam_type: string;
  scam_type_code?: string;
  priority: string;
  status: string;
  assigned_phone?: string;
  timeline_events?: any[];
  investigation_findings?: string;
  investigation_attachment?: string;
  investigation_completed_at?: string;
  investigated_by?: string;
}

const normalizeStatus = (status: string) => (status || "").toLowerCase().replace(/_/g, " ");

function CitizenDashboardContent() {
  const searchParams = useSearchParams();
  const targetCaseNum = searchParams.get("case");
  const { token, user } = useAuthStore();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChatCase, setActiveChatCase] = useState<Case | null>(null);
  const [downloadingCase, setDownloadingCase] = useState<string | null>(null);
  const [locations, setLocations] = useState<OfficialLocationItem[]>([]);
  const [locationsLoading, setLocationsLoading] = useState(false);
  const [selectedStationId, setSelectedStationId] = useState<string | null>(null);
  const [userCoords, setUserCoords] = useState<{ lat: number; lng: number } | null>(null);
  const pushToast = useToast();

  const fetchCitizenLocations = useCallback(async (lat?: number, lng?: number) => {
    setLocationsLoading(true);
    try {
      const params = new URLSearchParams();
      if (lat !== undefined && lng !== undefined) {
        params.append("lat", lat.toString());
        params.append("lng", lng.toString());
        params.append("radius_km", "150");
      }
      const query = params.toString() ? `?${params.toString()}` : "";
      const res = await axios.get(api(`/official-locations${query}`), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        withCredentials: true,
      });
      if (res.data?.locations) {
        setLocations(res.data.locations);
      }
    } catch (err: any) {
      if (err.response?.status === 402) {
        // Expected for free citizens: Pro subscription tier feature
        setLocations([]);
        return;
      }
      console.error("Failed to load locations for citizen:", err);
    } finally {
      setLocationsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchCitizenLocations();
  }, [fetchCitizenLocations]);

  const handleDetectNearestCell = () => {
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const coords = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          setUserCoords(coords);
          fetchCitizenLocations(coords.lat, coords.lng);
          pushToast("success", "Detected nearest jurisdictional cyber cells to your GPS location.");
        },
        () => {
          fetchCitizenLocations();
          pushToast("info", "Location access unavailable; showing national cyber cell headquarters.");
        }
      );
    } else {
      fetchCitizenLocations();
    }
  };

  const handleDownloadPdf = async (caseNumber: string) => {
    try {
      setDownloadingCase(caseNumber);
      const res = await axios.get(api(`/assistance-requests/${caseNumber}/dossier-pdf`), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        responseType: "blob",
        withCredentials: true,
      });

      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `DigitalRakshak_FIR_Dossier_${caseNumber}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);

      pushToast("success", "FIR Dossier PDF downloaded successfully.");
    } catch (err: any) {
      console.error("PDF download failed:", err);
      // Fallback: open with token query parameter in new tab
      const fallbackUrl = api(`/assistance-requests/${caseNumber}/dossier-pdf${token ? `?token=${token}` : ""}`);
      window.open(fallbackUrl, "_blank");
    } finally {
      setDownloadingCase(null);
    }
  };

  const fetchCases = async () => {
   
if (!token) return;
   
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(api("/cases/my"), {

      });
      setCases(response.data.cases || []);
    } catch (err) {
      console.error("Failed to fetch cases:", err);
      setError("We couldn't load your reports. Try again in a moment.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [token]);

  const handleResolve = async (caseNumber: string) => {
   

    try {
      await axios.post(api(`/cases/${caseNumber}/resolve`), {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Case resolved successfully.");
      fetchCases();
    } catch (err) {
      console.error(err);
      pushToast("danger", "Failed to mark as resolved.");
    }
  };

  const handleReopen = async (caseNumber: string) => {
    const reason = window.prompt("Please provide a reason for reopening this case:");
    if (!reason) return;
    
    try {
      await axios.post(api(`/cases/${caseNumber}/reopen`), { reason }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      pushToast("success", "Follow-up requested. Case reopened.");
      fetchCases();
    } catch (err) {
      console.error(err);
      pushToast("danger", "Failed to reopen case.");
    }
  };

  useEffect(() => {
    if (!targetCaseNum || cases.length === 0) return;
    setTimeout(() => {
      const el = document.getElementById(`case-card-${targetCaseNum}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }, 350);
  }, [targetCaseNum, cases]);

  const totalReports = cases.length;
  const underReview = cases.filter((c) =>
    ["under review", "pending", "submitted", "analyzing", "assigned", "investigating"].includes(normalizeStatus(c.status))
  ).length;
  const resolved = cases.filter((c) =>
    ["resolved", "closed", "completed", "investigation completed"].includes(normalizeStatus(c.status))
  ).length;

  const firstName = (user?.full_name || "").split(" ")[0];

  return (
    <div className="space-y-6 pt-2 max-w-4xl mx-auto">
      <Rise>
        <PageHeader
          title={firstName ? `Hello, ${firstName}` : "Your reports"}
          sub="Track what you've filed, monitor ongoing investigations, and safeguard your digital assets."
          actions={
            <div className="flex items-center gap-2">
              <Link href="/personal">
                <Button variant="secondary" size="lg" className="inline-flex items-center gap-1.5 border border-amber-500/30 text-amber-300 bg-amber-500/10 hover:bg-amber-500/20">
                  <Sparkles className="w-4 h-4 text-amber-400" />
                  Pro Shield
                </Button>
              </Link>
              <Link href="/report">
                <Button variant="primary" size="lg">
                  <Plus className="w-4 h-4" />
                  Report a scam
                </Button>
              </Link>
            </div>
          }
        />
      </Rise>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {loading ? (
          <>
            <StatSkeleton />
            <StatSkeleton />
            <StatSkeleton />
          </>
        ) : (
          <>
            <Rise index={1}>
              <StatBlock label="Reports filed" value={totalReports} />
            </Rise>
            <Rise index={2}>
              <StatBlock label="Ongoing Cases" value={underReview} />
            </Rise>
            <Rise index={3}>
              <StatBlock label="Resolved" value={resolved} />
            </Rise>
          </>
        )}
      </div>

      <Rise index={4}>
        {/* Embedded Interactive Jurisdictional Cyber Cell Locator */}
        <div className="rounded-card bg-surface-2 border border-line p-5 mb-8 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-line">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-ink">
                    Official Cyber Police Cell Locator
                  </h3>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    INTERACTIVE RADAR
                  </span>
                </div>
                <p className="text-xs text-ink-2 mt-0.5">
                  Find verified local cyber police stations, official landlines, and nodal officers for in-person FIR filing or evidence handoff.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleDetectNearestCell}
                className="inline-flex items-center gap-1.5 text-xs font-semibold"
              >
                <Compass className="w-3.5 h-3.5 text-amber-400" />
                <span>Locate Near Me</span>
              </Button>
              <Link
                href="/locator"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-control bg-accent hover:bg-accent-hover text-white text-xs font-semibold transition shrink-0"
              >
                <span>Full Directory</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Interactive Map & Nearest Stations Split Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
            <div className="lg:col-span-8 h-80 sm:h-96 rounded-xl overflow-hidden border border-line bg-surface">
              <CyberCellMap
                locations={locations}
                selectedStationId={selectedStationId}
                onStationSelect={(st) => setSelectedStationId(st.id)}
                userLocation={userCoords}
              />
            </div>

            <div className="lg:col-span-4 space-y-2.5 h-80 sm:h-96 overflow-y-auto pr-1">
              <div className="text-xs font-semibold text-ink-3 px-1 flex items-center justify-between">
                <span>Verified Stations ({locations.length})</span>
                <span className="font-mono text-[10px]">100% Gov Verified</span>
              </div>

              {locationsLoading ? (
                <div className="h-64 flex flex-col items-center justify-center gap-2 text-ink-3">
                  <Loader2 className="w-5 h-5 animate-spin text-amber-400" />
                  <span className="text-xs">Locating jurisdictional cells...</span>
                </div>
              ) : locations.length === 0 ? (
                <div className="p-6 text-center text-xs text-ink-3 bg-surface rounded-xl border border-line">
                  No verified stations loaded yet.
                </div>
              ) : (
                locations.map((loc) => {
                  const isSelected = selectedStationId === loc.id;
                  const phone = loc.landline_number || loc.helpline_number;
                  return (
                    <div
                      key={loc.id}
                      onClick={() => setSelectedStationId(loc.id)}
                      className={`p-3 rounded-xl border transition-all cursor-pointer text-xs ${
                        isSelected
                          ? "bg-surface-3 border-accent ring-1 ring-accent text-ink"
                          : "bg-surface hover:bg-surface-3/50 border-line text-ink-2"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-1 mb-1">
                        <h4 className="font-semibold text-xs text-ink line-clamp-1">
                          {loc.name}
                        </h4>
                        {loc.distance_km !== undefined && (
                          <span className="text-[10px] font-mono text-emerald-400 font-bold shrink-0">
                            {loc.distance_km} km
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-ink-3 line-clamp-1 mb-2">
                        {loc.district}, {loc.state}
                      </p>

                      <div className="flex items-center gap-2 pt-1 border-t border-line/40">
                        {phone && (
                          <a
                            href={`tel:${phone.replace(/\s+/g, "")}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-400 hover:text-amber-300"
                          >
                            <PhoneCall className="w-3 h-3" />
                            <span>{phone}</span>
                          </a>
                        )}
                        <a
                          href={`https://www.google.com/maps/search/?api=1&query=${loc.latitude},${loc.longitude}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="ml-auto inline-flex items-center gap-1 text-[11px] text-ink-3 hover:text-ink"
                        >
                          <span>Directions</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        <h2 className="font-display font-semibold text-lg tracking-tight text-ink mb-4 mt-8">My Cases</h2>
        {loading ? (
          <div className="space-y-4">
            <StatSkeleton />
            <StatSkeleton />
          </div>
        ) : error ? (
          <EmptyState
            icon={AlertTriangle}
            title="Something went wrong"
            body={error}
          />
        ) : cases.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports yet"
            body="If you've been targeted by a scam or spotted something suspicious, filing a report takes about two minutes."
            action={
              <Link href="/report">
                <Button variant="secondary">File your first report</Button>
              </Link>
            }
          />
        ) : (
          <div className="space-y-6">
            {cases.map((c) => {
              const isResolved = normalizeStatus(c.status) === "resolved" || normalizeStatus(c.status) === "closed";
              const isInvestigating = normalizeStatus(c.status) === "investigating";
              const isCompleted = normalizeStatus(c.status) === "investigation_completed" || normalizeStatus(c.status) === "investigation completed" || normalizeStatus(c.status) === "completed";
              const isTargeted = Boolean(targetCaseNum && c.case_number === targetCaseNum);
              const latestCompletedEvent = c.timeline_events?.slice().reverse().find((e: any) => e.action === "Investigation Completed");
              const hasCompletedFindings = isCompleted || Boolean(c.investigation_findings || latestCompletedEvent);
              
              return (
                <Card
                  key={c.id}
                  id={`case-card-${c.case_number}`}
                  className={cn(
                    "p-6 transition-all hover:border-[#253540] hover:shadow-card",
                    isTargeted && "ring-2 ring-emerald-500 bg-emerald-500/5 shadow-[0_0_24px_rgba(16,185,129,0.25)]"
                  )}
                >
                  <div className="flex flex-col sm:flex-row justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2 flex-wrap">
                        <span className="font-semibold text-ink tabular">{c.case_number}</span>
                        <StatusBadge status={c.status} />
                        <PriorityBadge priority={c.priority} />
                        {isTargeted && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                            Selected
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-ink-2 capitalize">
                        {(c.scam_type_code || c.scam_type || "Unknown").replace(/_/g, " ")} • Filed on {new Date(c.created_at.endsWith("Z") || c.created_at.includes("+") ? c.created_at : c.created_at + "Z").toLocaleDateString("en-IN", {
                          year: "numeric", month: "short", day: "numeric"
                        })}
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-3 self-start flex-wrap">
                      {isCompleted && !isResolved && (
                        <>
                          <Button variant="secondary" size="sm" onClick={() => handleReopen(c.case_number)}>
                            Request Follow-up
                          </Button>
                          <Button variant="primary" size="sm" className="bg-success hover:bg-success/90 text-white font-bold" onClick={() => handleResolve(c.case_number)}>
                            <CheckCircle2 className="w-4 h-4 mr-1.5" />
                            Accept & Resolve
                          </Button>
                        </>
                      )}
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setActiveChatCase(c)}
                        className="inline-flex items-center gap-1.5 border-accent/40 text-accent-text hover:bg-accent/10"
                      >
                        <MessageSquare className="w-3.5 h-3.5" />
                        Direct Officer Chat
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        disabled={downloadingCase === c.case_number}
                        onClick={() => handleDownloadPdf(c.case_number)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-surface-2 hover:bg-surface-3 text-ink text-xs font-medium border border-line transition"
                      >
                        {downloadingCase === c.case_number ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin text-warning" />
                            <span>Generating PDF...</span>
                          </>
                        ) : (
                          <>
                            <Download className="w-3.5 h-3.5 text-warning" />
                            <span>FIR Dossier PDF</span>
                          </>
                        )}
                      </Button>
                      {!isCompleted && !isResolved && (
                        <Button variant="secondary" size="sm" onClick={() => handleResolve(c.case_number)}>
                          <CheckCircle2 className="w-4 h-4 mr-1.5 text-success" />
                          Mark as Resolved
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  <CaseStepper status={c.status} />

                  {/* Official Police Investigation Findings & Action Report Card */}
                  {hasCompletedFindings && (
                    <div className="mt-5 p-4 rounded-xl border border-emerald-500/40 bg-gradient-to-r from-emerald-500/15 via-emerald-500/10 to-transparent shadow-sm space-y-3 animate-in fade-in">
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400">
                            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                          </div>
                          <div>
                            <h4 className="text-sm font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wide">
                              Official Investigation Concluded
                            </h4>
                            <p className="text-[11px] text-ink-3">
                              Investigating officer {c.investigated_by || latestCompletedEvent?.author || "in charge"} has submitted formal findings and action docket.
                            </p>
                          </div>
                        </div>
                        <span className="text-[10px] font-black px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 uppercase">
                          {isResolved ? "Case Resolved" : "Awaiting Acceptance"}
                        </span>
                      </div>

                      {/* Submitted Findings & Action Notes */}
                      <div className="p-3.5 rounded-lg bg-surface border border-line space-y-1.5">
                        <p className="text-[10px] font-bold text-ink-3 uppercase tracking-wider flex items-center justify-between">
                          <span>Officer Investigation Findings & Action Report</span>
                          {(c.investigation_completed_at || latestCompletedEvent?.timestamp) && (
                            <span className="font-mono text-[10px] text-ink-3">
                              {new Date(c.investigation_completed_at || latestCompletedEvent?.timestamp).toLocaleString("en-IN")}
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-ink leading-relaxed whitespace-pre-wrap">
                          {c.investigation_findings ||
                            latestCompletedEvent?.remark ||
                            "The investigating officer has completed formal evidentiary verification and recorded case resolution details on file."}
                        </p>
                      </div>

                      {/* Official Attachment if present */}
                      {(c.investigation_attachment || latestCompletedEvent?.attachment) && (
                        <div className="flex items-center gap-2">
                          <a
                            href={c.investigation_attachment || latestCompletedEvent?.attachment}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-accent-text hover:underline bg-accent/10 px-3 py-1.5 rounded-lg border border-accent/20"
                          >
                            <Download className="w-3.5 h-3.5" />
                            Download Evidentiary Attachment / Closing Report
                          </a>
                        </div>
                      )}

                      {!isResolved && (
                        <div className="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-emerald-500/20">
                          <p className="text-xs text-ink-2">
                            Please review the findings above to confirm resolution of your incident.
                          </p>
                          <div className="flex items-center gap-2">
                            <Button variant="secondary" size="sm" onClick={() => handleReopen(c.case_number)} className="text-xs">
                              Request Follow-up
                            </Button>
                            <Button variant="primary" size="sm" className="bg-success hover:bg-success/90 text-white text-xs font-bold" onClick={() => handleResolve(c.case_number)}>
                              <CheckCircle2 className="w-4 h-4 mr-1.5" />
                              Accept & Resolve Case
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {isInvestigating && c.assigned_phone && (
                    <div className="mt-6 p-4 rounded-card bg-surface-2 border border-line flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-ink flex items-center gap-2">
                          <PhoneCall className="w-4 h-4 text-ink-3" /> Police Contact
                        </p>
                        <p className="text-xs text-ink-2 mt-1">
                          You can reach out to the assigned police station for updates regarding your case.
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-ink">{c.assigned_phone}</p>
                      </div>
                    </div>
                  )}

                  {c.timeline_events && c.timeline_events.length > 0 && (
                    <div className="mt-8 border-t border-line pt-6">
                      <h3 className="text-sm font-medium text-ink mb-4">Case Activity</h3>
                      <CaseActivityTimeline events={c.timeline_events} />
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </Rise>

      {/* Direct Monitored Investigator Chat Modal */}
      {activeChatCase && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200">
          <div className="w-full max-w-2xl h-[640px] max-h-[90vh]">
            <CaseChatPanel
              caseId={String(activeChatCase.id)}
              caseNumber={activeChatCase.case_number}
              assignedOfficerName={activeChatCase.assigned_phone ? `Station (${activeChatCase.assigned_phone})` : undefined}
              onClose={() => setActiveChatCase(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default function CitizenDashboard() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-sm font-mono text-ink-3">Loading Citizen Portal...</div>}>
      <CitizenDashboardContent />
    </Suspense>
  );
}