"use client";

import { api } from "@/lib/api";
import React, { useEffect, useState } from "react";
import {
  CheckCircle2,
  ShieldAlert,
  AlertTriangle,
  RefreshCw,
  UserCheck,
  Zap,
  Sliders,
  Bot,
  Cpu,
  Lock,
  ShieldCheck,
  History,
  CornerDownRight,
  UserX,
  Activity
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { Card, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataTable, type Column } from "@/components/ui/data-table";
import { TableSkeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useToast } from "@/components/ui/toast";
import { RAICExecutionMonitor } from "@/components/ui/RAICExecutionMonitor";

interface PendingUser {
  id: string;
  email: string;
  full_name: string;
  created_at?: string;
}

interface VerificationCase {
  case_number: string;
  scam_type: string;
  city: string;
  ai_confidence: number;
  ai_verdict: string;
  flagged_reason: string;
  entities: string[];
  status: "PENDING_REVIEW" | "NTIR_VERIFIED" | "OVERRIDDEN_CLEAN";
}

export default function AdminApprovalsPage() {
  const [activeTab, setActiveTab] = useState<"ntir" | "users">("ntir");
  const [users, setUsers] = useState<PendingUser[]>([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [approvingUserId, setApprovingUserId] = useState<string | null>(null);
  const { token } = useAuthStore();
  const toast = useToast();

 const [casesQueue, setCasesQueue] =
useState<VerificationCase[]>([]);

  const [processingCase, setProcessingCase] = useState<string | null>(null);
  const [overrideModalCase, setOverrideModalCase] = useState<VerificationCase | null>(null);
  const [overrideNotes, setOverrideNotes] = useState<string>("");
  const [qwenWeight, setQwenWeight] = useState<number>(0.35);

  useEffect(() => {
    if (token && activeTab === "users") {
      fetchPendingUsers();
    }
  }, [token, activeTab]);
useEffect(() => {

if (!token) return;

fetchPendingCases();

}, [token]);
const fetchPendingCases = async () => {

try{

const response = await fetch(
api("/cases/pending"),
{
headers:{
Authorization:`Bearer ${token}`
}
}
);

if(!response.ok)
throw new Error();

const data = await response.json();

setCasesQueue(data);

}

catch(err){

console.error(err);

setCasesQueue([]);

}

};
  const fetchPendingUsers = async () => {
    try {
      setLoadingUsers(true);
      const response = await fetch(api("/users/pending"), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (err) {
      console.error("Pending users load error:", err);
setUsers([]);
     } finally {
      setLoadingUsers(false);
    }
  };

  const handleApproveUser = async (userId: string) => {
    try {
      setApprovingUserId(userId);
      const response = await fetch(api(`/users/${userId}/approve`), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        setUsers((prev) => prev.filter((u) => u.id !== userId));
        toast("success", "User approved.");
      }
    } catch (err: any) {
      toast("danger", "Failed to approve user.");
    } finally {
      setApprovingUserId(null);
    }
  };

  const handleVerifyToNTIR = async (caseNum: string) => {
    setProcessingCase(caseNum);
    try {
      const response = await fetch(api(`/cases/${caseNum}/verify-ntir`), {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        setCasesQueue((prev) =>
          prev.map((c) => (c.case_number === caseNum ? { ...c, status: "NTIR_VERIFIED" } : c))
        );
        toast("success", `Case ${caseNum} verified and permanently locked into NTIR & NPCI Grid!`);
      }
    } catch (err) {
      toast("danger", "Failed to verify case.");
    } finally {
      setProcessingCase(null);
    }
  };

  const submitRLHFOverride = async () => {
    if (!overrideModalCase) return;
    setProcessingCase(overrideModalCase.case_number);
    try {
      const response = await fetch(api(`/cases/${overrideModalCase.case_number}/override-decision`), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          verdict: "Overridden by Officer (Clean / Edge Case)",
          notes: overrideNotes,
          adjusted_weights: { qwen_weight: qwenWeight, threat_analysis_weight: 1 - qwenWeight }
        })
      });
      if (response.ok) {
        setCasesQueue((prev) =>
          prev.map((c) => (c.case_number === overrideModalCase.case_number ? { ...c, status: "OVERRIDDEN_CLEAN" } : c))
        );
        toast("success", `RLHF override applied to ${overrideModalCase.case_number}. Weights updated.`);
        setOverrideModalCase(null);
      }
    } catch (err) {
      toast("danger", "Failed to apply override.");
    } finally {
      setProcessingCase(null);
    }
  };

  const userColumns: Column<PendingUser>[] = [
    {
      key: "name",
      header: "Name",
      mobile: "title",
      render: (u) => <span className="font-mono font-bold text-ink">{u.full_name}</span>,
    },
    {
      key: "email",
      header: "Email",
      render: (u) => <span className="font-mono text-ink-2 text-sm">{u.email}</span>,
    },
    {
      key: "registered",
      header: "Registered",
      render: (u) => (
        <span className="font-mono text-ink-3 text-sm">
          {u.created_at ? new Date(u.created_at + "Z").toLocaleDateString("en-IN") : "—"}
        </span>
      ),
    },
    {
      key: "action",
      header: "",
      align: "right",
      render: (u) => (
        <Button
          size="sm"
          onClick={() => handleApproveUser(u.id)}
          disabled={approvingUserId === u.id}
          className="bg-success hover:bg-success/85 text-black font-mono font-bold border-none rounded-control transition-all"
        >
          {approvingUserId === u.id ? <RefreshCw className="w-4 h-4 animate-spin" /> : "Grant Credentials"}
        </Button>
      ),
    },
  ];

  const pendingVerificationCount = casesQueue.filter((c) => c.status === "PENDING_REVIEW").length;

  return (
    <div className="min-h-screen bg-bg text-ink p-4 md:p-6 space-y-6 font-sans transition-colors duration-300">
      
      {/* ================= HEADER ================= */}
    <div
      className="
        rounded-card
        bg-surface
        border
        border-line/10
        shadow-card
        px-6 md:px-8
        py-6 md:py-8
        w-full
        overflow-hidden
      "
    >
        <div className="flex flex-col xl:flex-row xl:items-start gap-6">

          {/* LEFT SECTION: Shield Icon + Text + Badges */}
          <div className="flex items-start gap-5 min-w-0 flex-1">
            {/* Shield Icon */}
            <div className="w-14 h-14 xl:w-16 xl:h-16 rounded-control bg-accent-text/10 border border-accent-text/20 flex items-center justify-center shrink-0">
              <ShieldAlert className="w-7 h-7 xl:w-8 xl:h-8 text-accent-text" />
            </div>

            {/* Title & Subtitle */}
            <div className="min-w-0">
              <h1 className="font-display font-black uppercase leading-[1.15] tracking-tight text-xl md:text-2xl xl:text-[28px] text-ink">
                HUMAN VERIFICATION & NTIR<br />FEEDBACK DESK
              </h1>
              <p className="mt-2 font-mono text-xs text-ink-2 max-w-[420px]">
                National Threat Intelligence Repository (`NTIR`) & RLHF Core
              </p>
              {/* Badges inline under title on smaller screens */}
              <div className="flex flex-wrap items-center gap-2 mt-3">
                <span className="px-3 py-1.5 rounded-control bg-success-tint border border-success/20 font-mono text-[10px] font-bold uppercase whitespace-nowrap">
                  Sprint 7 Human-In-The-Loop
                </span>
                <span className="font-mono text-success font-bold text-xs whitespace-nowrap">
                  Dual Governance Queue
                </span>
              </div>
            </div>
          </div>

          {/* RIGHT SECTION: Segmented Controls */}
          <div className="w-full xl:w-auto xl:min-w-[400px] xl:max-w-[520px] shrink-0">
            <div className="rounded-xl bg-surface-2 border border-line/10 p-1.5 flex gap-1">
              {/* Tab 1 */}
              <button
                onClick={() => setActiveTab("ntir")}
                className={`flex-1 rounded-lg py-2.5 px-3 transition flex items-center justify-center gap-2 ${
                  activeTab === "ntir"
                    ? "bg-success text-black"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                <ShieldAlert className="w-4 h-4 shrink-0" />
                <div className="text-center">
                  <div className="font-bold text-xs sm:text-sm leading-tight">
                    NTIR Threat Verification
                  </div>
                  <div className="font-bold text-[10px] sm:text-xs opacity-90 leading-tight">
                    & RLHF Queue
                  </div>
                </div>
              </button>

              {/* Tab 2 */}
              <button
                onClick={() => setActiveTab("users")}
                className={`flex-1 rounded-lg py-2.5 px-3 transition flex items-center justify-center gap-2 ${
                  activeTab === "users"
                    ? "bg-success text-black"
                    : "text-ink-3 hover:text-ink"
                }`}
              >
                <UserCheck className="w-4 h-4 shrink-0" />
                <div className="text-center">
                  <div className="font-bold text-xs sm:text-sm leading-tight">
                    Nodal Officer
                  </div>
                  <div className="font-bold text-[10px] sm:text-xs opacity-90 leading-tight">
                    Registrations ({users.length})
                  </div>
                </div>
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* Row 2: Compact AI Recommendation Banner */}
      <div className="p-3.5 rounded-card bg-surface-2 border-l-4 border-l-accent border border-line/15 shadow-sm relative overflow-hidden">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-control bg-accent-text/10 text-accent-text shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-sans font-medium text-ink-2 leading-relaxed">
                <span className="font-mono text-[10px] font-black uppercase tracking-wider text-accent-text mr-1">AI Automated Intel:</span>
                Verify borderline RAIC consensus profiles to lock active signatures globally and invoke immediate bank grid preservation rules.
              </p>
            </div>
          </div>
          <div className="px-2.5 py-1 rounded-control bg-surface-3/50 text-ink-2 font-mono text-[10px] font-bold shrink-0 self-start sm:self-center">
            RAIC Core v2.5
          </div>
        </div>
      </div>

      {/* Dynamic Tabs Content */}
      {activeTab === "ntir" ? (
        <div className="space-y-6">
          
          {/* Row 3: 3 Column Threat Verification Grid (Strict Equal Heights) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
            {casesQueue.map((c) => {
              const isPending = c.status === "PENDING_REVIEW";
              const isVerified = c.status === "NTIR_VERIFIED";
              const isOverridden = c.status === "OVERRIDDEN_CLEAN";

              let statusBorder = "border-line/10";
              let statusBg = "bg-surface";
              if (isVerified) {
                statusBorder = "border-success/35";
                statusBg = "bg-gradient-to-b from-surface to-success-tint/10";
              } else if (isOverridden) {
                statusBorder = "border-line/5 opacity-60";
                statusBg = "bg-surface/50";
              }

              return (
                <div
                  key={c.case_number}
                  className={`rounded-card border p-5 flex flex-col justify-between space-y-4 shadow-sm hover:shadow-md transition-all duration-300 relative overflow-hidden ${statusBg} ${statusBorder}`}
                >
                  {/* Subtle top indicator for pending issues */}
                  {isPending && (
                    <div className="absolute top-0 inset-x-0 h-0.5 bg-accent" />
                  )}

                  <div className="space-y-4">
                    {/* Header: Case ID, AI Confidence and Status */}
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <span className="font-mono text-sm font-black text-ink tracking-wider block">
                          {c.case_number}
                        </span>
                        
                        {/* Compact AI Confidence percentage indicator inside each card */}
                        <div className="flex items-center gap-1">
                          <Bot className="w-3.5 h-3.5 text-accent-text" />
                          <span className="text-[10px] font-mono text-ink-3 font-semibold">
                            {(c.ai_confidence * 100).toFixed(0)}% AI Consensus
                          </span>
                        </div>
                      </div>
                      
                      <span
                        className={`px-2 py-0.5 rounded-pill text-[9px] font-mono font-bold uppercase tracking-wider ${
                          isVerified
                            ? "bg-success-tint text-success border border-success/25"
                            : isOverridden
                            ? "bg-surface-2 text-ink-3 border border-line/10"
                            : "bg-warning-tint text-accent-text border border-accent/25"
                        }`}
                      >
                        {c.status.replace("_", " ")}
                      </span>
                    </div>

                    {/* Metadata Grid */}
                    <div className="grid grid-cols-2 gap-3 p-2.5 bg-surface-2 rounded-control border border-line/10 text-xs font-mono">
                      <div>
                        <span className="text-ink-3 text-[9px] uppercase tracking-wider block">Threat Vector</span>
                        <strong className="text-ink text-xs truncate block mt-0.5">{c.scam_type}</strong>
                      </div>
                      <div>
                        <span className="text-ink-3 text-[9px] uppercase tracking-wider block">Jurisdiction</span>
                        <strong className="text-accent-text text-xs truncate block mt-0.5">{c.city}</strong>
                      </div>
                    </div>

                    {/* Flagged Rationale */}
                    <div className="p-3.5 rounded-control bg-surface-2 border border-line/15 space-y-2">
                      <div className="flex items-center gap-1 text-danger font-mono text-[10px] font-bold uppercase">
                        <AlertTriangle className="w-3.5 h-3.5" />
                        <span>Analysis Rationale</span>
                      </div>
                      <p className="text-ink-2 text-xs leading-relaxed font-sans font-medium">
                        {c.flagged_reason}
                      </p>

                      {/* Evidence Chips */}
                      <div className="pt-2.5 border-t border-line/10 space-y-1">
                        <span className="text-[9px] text-ink-3 uppercase font-mono block">Identified Entities</span>
                        <div className="flex flex-wrap gap-1">
                          {c.entities.map((e, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-0.5 rounded-control bg-surface-3/40 border border-line/15 text-ink text-[10px] font-mono flex items-center gap-1"
                            >
                              <CornerDownRight className="w-2.5 h-2.5 text-ink-3" />
                              {e}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* CTAs */}
                  <div className="space-y-2 pt-3 border-t border-line/10">
                    {isPending ? (
                      <div className="space-y-2">
                        <button
                          onClick={() => handleVerifyToNTIR(c.case_number)}
                          disabled={processingCase === c.case_number}
                          className="w-full py-2 rounded-control bg-success hover:bg-success/90 text-black font-mono font-black text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer active:scale-95 disabled:opacity-50"
                        >
                          {processingCase === c.case_number ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          )}
                          Verify & Lock NTIR Grid
                        </button>
                        <button
                          onClick={() => setOverrideModalCase(c)}
                          className="w-full py-1.5 rounded-control bg-surface-2 hover:bg-surface-3/50 text-ink font-mono font-bold text-xs border border-line/20 flex items-center justify-center gap-1.5 transition-all"
                        >
                          <Sliders className="w-3 h-3 text-accent-text" />
                          Override & Fine-tune
                        </button>
                      </div>
                    ) : (
                      <div className="py-1 text-center text-ink-3 font-mono text-[10px]">
                        Closed & immutable threat signature record.
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Row 4: Redesigned Telemetry Panel Container */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-accent-text animate-pulse" />
              <h3 className="font-mono text-xs font-black uppercase text-ink tracking-wider">
                Consensus Stream Feed (`RAICExecutionMonitor`)
              </h3>
            </div>
            
            <div className="rounded-card bg-surface border border-line/10 shadow-sm overflow-hidden">
              <div className="px-4 py-2.5 bg-surface-2 border-b border-line/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-1.5 w-1.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success"></span>
                  </span>
                  <span className="font-mono text-[9px] text-ink-3 uppercase tracking-wider font-extrabold">Active System Broadcast Pipe</span>
                </div>
                <div className="font-mono text-[9px] text-ink-3 font-semibold">Node Pipeline: Synchronized</div>
              </div>
              <div className="p-4 bg-surface-2/30">
                <RAICExecutionMonitor autoConnect={true} className="max-h-52 font-mono text-xs rounded-control border border-line/5 text-ink" />
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Tab 2: Nodal Officer Registrations */
        <div className="space-y-4">
          <Card className="bg-surface border-line/10 rounded-card overflow-hidden shadow-sm">
            <CardHeader 
              title={
                <div className="flex items-center gap-2 font-mono text-ink text-sm">
                  <UserCheck className="w-4 h-4 text-accent-text" />
                  <span>Pending Registrations Verification</span>
                </div>
              } 
              sub={<span className="font-mono text-xs text-ink-3">Validate credentials of operators requesting system entry permissions.</span>} 
            />
            <div className="p-4 bg-surface">
              {loadingUsers ? (
                <TableSkeleton rows={4} />
              ) : users.length === 0 ? (
                <EmptyState icon={UserX} title="No registrations requiring review" body="All registration tickets for nodal officers have been closed." />
              ) : (
                <DataTable columns={userColumns} rows={users} rowKey={(u) => u.id} />
              )}
            </div>
          </Card>
        </div>
      )}

      {/* Row 5: Compact KPI Security Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-3.5 rounded-card bg-surface border border-line/10 flex items-center gap-3 shadow-sm">
          <div className="p-2 rounded-control bg-accent-text/10 text-accent-text border border-accent/15 shrink-0">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] uppercase font-mono tracking-wider text-ink-3 block font-black">RAIC Engine</span>
            <span className="text-[11px] text-ink-2 font-sans font-medium block">6-Factor risk parser</span>
          </div>
        </div>

        <div className="p-3.5 rounded-card bg-surface border border-line/10 flex items-center gap-3 shadow-sm">
          <div className="p-2 rounded-control bg-success-tint text-success border border-success/15 shrink-0">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] uppercase font-mono tracking-wider text-ink-3 block font-black">Secure Verification</span>
            <span className="text-[11px] text-ink-2 font-sans font-medium block">Multi-sig validation logic</span>
          </div>
        </div>

        <div className="p-3.5 rounded-card bg-surface border border-line/10 flex items-center gap-3 shadow-sm">
          <div className="p-2 rounded-control bg-accent/10 text-accent-text border border-accent/15 shrink-0">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] uppercase font-mono tracking-wider text-ink-3 block font-black">Bank Freeze Sync</span>
            <span className="text-[11px] text-ink-2 font-sans font-medium block">Automated NPCI lock interface</span>
          </div>
        </div>

        <div className="p-3.5 rounded-card bg-surface border border-line/15 flex items-center gap-3 shadow-sm">
          <div className="p-2 rounded-control bg-surface-2 text-ink-2 border border-line/15 shrink-0">
            <History className="w-4 h-4" />
          </div>
          <div>
            <span className="text-[9px] uppercase font-mono tracking-wider text-ink-3 block font-black">Audit Trail</span>
            <span className="text-[11px] text-ink-2 font-sans font-medium block">Cryptographically signed logs</span>
          </div>
        </div>
      </div>

      {/* RLHF Override & Weight Tuning Modal */}
      {overrideModalCase && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-line/15 rounded-card max-w-lg w-full p-5 space-y-5 shadow-card font-mono relative overflow-hidden">
            <div className="absolute top-0 right-0 w-24 h-24 bg-accent-text/5 rounded-full blur-xl pointer-events-none" />
            
            <div className="flex items-center justify-between border-b border-line/10 pb-3">
              <div className="flex items-center gap-2">
                <Sliders className="w-4.5 h-4.5 text-accent-text" />
                <h3 className="text-sm font-black text-ink uppercase tracking-tight">RLHF Override Console</h3>
              </div>
              <button
                onClick={() => setOverrideModalCase(null)}
                className="text-ink-3 hover:text-ink bg-surface-2 hover:bg-surface-3 p-1 rounded-control transition-colors text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <p className="text-ink-2 leading-relaxed font-sans">
                Tuning analytical engine biases for case <strong className="text-ink font-mono">{overrideModalCase.case_number}</strong>. Adjust parameters before NTIR storage.
              </p>

              <div className="space-y-1.5">
                <label className="text-ink-3 font-bold block uppercase text-[9px] tracking-wider">Forensic Override Notes:</label>
                <textarea
                  value={overrideNotes}
                  onChange={(e) => setOverrideNotes(e.target.value)}
                  placeholder="e.g. Legitimate gateway routing verified manually via agency coordination..."
                  rows={3}
                  className="w-full p-2.5 rounded-control bg-surface-2 border border-line/10 text-ink focus:outline-none focus:border-accent text-xs transition-colors"
                />
              </div>

              <div className="p-3 rounded-control bg-surface-2 border border-line/10 space-y-3">
                <div className="flex justify-between font-bold text-ink-2 text-[11px]">
                  <span>Qwen LLM Weight: <span className="text-accent-text">{(qwenWeight * 100).toFixed(0)}%</span></span>
                  <span>System Heuristics: <span className="text-accent-text">{((1 - qwenWeight) * 100).toFixed(0)}%</span></span>
                </div>
                
                <input
                  type="range"
                  min="0.10"
                  max="0.90"
                  step="0.05"
                  value={qwenWeight}
                  onChange={(e) => setQwenWeight(parseFloat(e.target.value))}
                  className="w-full accent-accent cursor-pointer bg-line h-1 rounded-control"
                />
                
                <span className="text-[9px] text-ink-3 block text-center font-sans leading-normal">
                  Reduces false-positive ratios by updating consensus model priors.
                </span>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-line/10">
              <button
                onClick={() => setOverrideModalCase(null)}
                className="px-3 py-1.5 rounded-control bg-surface-2 hover:bg-surface-3 text-ink font-bold text-xs border border-line/10 transition-all"
              >
                Cancel
              </button>
              <button
                onClick={submitRLHFOverride}
                disabled={processingCase === overrideModalCase.case_number}
                className="px-4 py-1.5 rounded-control bg-accent hover:bg-accent-hover text-accent-ink font-black text-xs flex items-center gap-1.5 shadow-sm transition-all cursor-pointer disabled:opacity-50"
              >
                {processingCase === overrideModalCase.case_number ? (
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Zap className="w-3.5 h-3.5" />
                )}
                Commit Parameters
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}