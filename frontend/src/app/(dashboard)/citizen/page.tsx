"use client";

import { api } from "@/lib/api";

import { useEffect, useState } from "react";
import Link from "next/link";
import axios from "axios";
import { FileText, Plus, AlertTriangle, PhoneCall, CheckCircle2 } from "lucide-react";
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
}

const normalizeStatus = (status: string) => (status || "").toLowerCase().replace(/_/g, " ");

function CaseStepper({ status }: { status: string }) {
  const s = normalizeStatus(status);
  const steps = ["submitted", "assigned", "investigating", "investigation completed", "resolved"];
  const currentIndex = steps.indexOf(s);
  
  return (
    <div className="flex items-center gap-2 mt-4 text-xs font-medium">
      {steps.map((step, idx) => {
        const isActive = idx <= currentIndex;
        const isResolvedStep = step === "resolved" && isActive;
        
        return (
          <div key={step} className="flex items-center gap-2 flex-1">
            <div className={`flex items-center gap-1.5 ${isActive ? 'text-ink' : 'text-ink-3'}`}>
              <div className={`w-4 h-4 rounded-full flex items-center justify-center border ${
                isActive 
                  ? isResolvedStep 
                    ? 'border-success bg-success-tint text-success' 
                    : 'border-warning bg-warning-tint text-warning'
                  : 'border-line bg-surface-2'
              }`}>
                {isActive && (
                  <div className={`w-1.5 h-1.5 rounded-full ${
                    isResolvedStep ? 'bg-success' : 'bg-warning'
                  }`} />
                )}
              </div>
              <span className="capitalize">{step}</span>
            </div>
            {idx < steps.length - 1 && (
              <div className={`h-px flex-1 ${
                idx < currentIndex 
                  ? steps[idx + 1] === "resolved" && s === "resolved"
                    ? 'bg-success' 
                    : 'bg-warning'
                  : 'bg-line'
              }`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function CitizenDashboard() {
  const { token, user } = useAuthStore();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pushToast = useToast();

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

  const totalReports = cases.length;
  const underReview = cases.filter((c) =>
    ["under review", "pending", "submitted", "analyzing", "assigned", "investigating", "investigation_completed"].includes(normalizeStatus(c.status))
  ).length;
  const resolved = cases.filter((c) =>
    ["resolved", "closed", "completed"].includes(normalizeStatus(c.status))
  ).length;

  const firstName = (user?.full_name || "").split(" ")[0];

  return (
    <div className="space-y-6 pt-2 max-w-4xl mx-auto">
      <Rise>
        <PageHeader
          title={firstName ? `Hello, ${firstName}` : "Your reports"}
          sub="Track what you've filed and where each case stands."
          actions={
            <Link href="/report">
              <Button variant="primary" size="lg">
                <Plus className="w-4 h-4" />
                Report a scam
              </Button>
            </Link>
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
              const isResolved = normalizeStatus(c.status) === "resolved";
              const isInvestigating = normalizeStatus(c.status) === "investigating";
              const isCompleted = normalizeStatus(c.status) === "investigation_completed" || normalizeStatus(c.status) === "investigation completed";
              
              return (
                <Card key={c.id} className="p-6 transition-all hover:border-[#253540] hover:shadow-card">
                  <div className="flex flex-col sm:flex-row justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-3 mb-2">
                        <span className="font-semibold text-ink tabular">{c.case_number}</span>
                        <StatusBadge status={c.status} />
                        <PriorityBadge priority={c.priority} />
                      </div>
                      <p className="text-sm text-ink-2 capitalize">
                        {(c.scam_type_code || c.scam_type || "Unknown").replace(/_/g, " ")} • Filed on {new Date(c.created_at + "Z").toLocaleDateString("en-IN", {
                          year: "numeric", month: "short", day: "numeric"
                        })}
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-3 self-start">
                      {isCompleted && (
                        <>
                          <Button variant="secondary" size="sm" onClick={() => handleReopen(c.case_number)}>
                            Request Follow-up
                          </Button>
                          <Button variant="primary" size="sm" className="bg-success hover:bg-success/90 text-white" onClick={() => handleResolve(c.case_number)}>
                            <CheckCircle2 className="w-4 h-4 mr-1.5" />
                            Accept & Resolve
                          </Button>
                        </>
                      )}
                      {!isCompleted && !isResolved && (
                        <Button variant="secondary" size="sm" onClick={() => handleResolve(c.case_number)}>
                          <CheckCircle2 className="w-4 h-4 mr-1.5 text-success" />
                          Mark as Resolved
                        </Button>
                      )}
                    </div>
                  </div>
                  
                  <CaseStepper status={c.status} />
                  
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
    </div>
  );
}