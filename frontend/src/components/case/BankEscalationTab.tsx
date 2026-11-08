"use client";

import React, { useState, useEffect } from "react";
import axios from "axios";
import { API_BASE_URL } from "@/lib/api";
import {
  Building2,
  Send,
  CheckCircle2,
  Clock,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
  ExternalLink,
  ChevronRight,
  Landmark,
  FileText,
  GitBranch,
  X,
  Radio
} from "lucide-react";

interface BankEscalationTabProps {
  caseNumber: string;
  token?: string | null;
  onRefreshCase?: () => void;
}

interface TargetBank {
  id: string;
  code: string;
  name: string;
  integration_type?: string;
}

interface EscalationRecord {
  id: string;
  alert_reference: string;
  escalation_role: string;
  status: string;
  approval_tier: string;
  priority: string;
  target_bank: TargetBank;
  alert_payload: any;
  approved_by?: string;
  approved_at?: string;
  created_at?: string;
  delivery_attempts_count: number;
  latest_response?: string;
}

export default function BankEscalationTab({ caseNumber, token, onRefreshCase }: BankEscalationTabProps) {
  const [escalations, setEscalations] = useState<EscalationRecord[]>([]);
  const [correlations, setCorrelations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Delivery Timeline Modal State
  const [timelineModalOpen, setTimelineModalOpen] = useState(false);
  const [timelineData, setTimelineData] = useState<any>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  const apiUrl = API_BASE_URL;

  const fetchEscalations = async () => {
    try {
      setLoading(true);
      setError(null);

      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const [escRes, corrRes] = await Promise.all([
        axios.get(`${apiUrl}/bank-escalations/case/${caseNumber}`, { headers }).catch((err) => {
          if (err.response?.status === 404) return { data: { escalations: [] } };
          throw err;
        }),
        axios.get(`${apiUrl}/fraud/correlations/${caseNumber}`, { headers }).catch(() => ({ data: null }))
      ]);

      setEscalations(escRes.data.escalations || []);
      setCorrelations(corrRes.data || null);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load institutional escalations.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseNumber) {
      fetchEscalations();
    }
  }, [caseNumber, token]);

  const handleTriggerRouting = async () => {
    try {
      setActionLoading("routing");
      setError(null);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      await axios.post(`${apiUrl}/bank-escalations/case/${caseNumber}/route`, {}, { headers });
      await fetchEscalations();
      if (onRefreshCase) onRefreshCase();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to trigger automated bank routing.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleApproveAndDispatch = async (escalationId: string) => {
    try {
      setActionLoading(escalationId);
      setError(null);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      await axios.post(
        `${apiUrl}/bank-escalations/${escalationId}/approve?dispatch_now=true`,
        {},
        { headers }
      );
      await fetchEscalations();
      if (onRefreshCase) onRefreshCase();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to approve and dispatch alert.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewTimeline = async (escalationId: string) => {
    try {
      setTimelineLoading(true);
      setTimelineModalOpen(true);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const res = await axios.get(`${apiUrl}/bank-escalations/${escalationId}/timeline`, { headers });
      setTimelineData(res.data);
    } catch (err: any) {
      setError("Failed to fetch delivery audit history.");
    } finally {
      setTimelineLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-center gap-3 text-slate-300">
        <RefreshCw className="w-5 h-5 animate-spin text-emerald-400" />
        <span className="font-mono text-xs">Loading Institutional Fraud Escalations...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Banner */}
      <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Landmark className="w-5 h-5 text-emerald-400" />
            <h3 className="font-mono text-base font-bold text-white tracking-wide">
              Bank-Specific Financial Fraud Escalation Gateway
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Direct inter-bank intelligence bridge connecting Victim Remitter Banks, Suspect Beneficiary Banks,
            and Law Enforcement under Bharatiya Sakshya Adhiniyam (BSA) 2023 Sec 63.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleTriggerRouting}
            disabled={actionLoading === "routing"}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-bold font-mono bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white shadow-lg transition-all"
          >
            {actionLoading === "routing" ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Radio className="w-4 h-4" />
            )}
            {escalations.length === 0 ? "Trigger Bank Routing & Extraction" : "Re-Evaluate Routing"}
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-rose-950/30 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Cross-Institution Graph Syndicate Warning */}
      {correlations?.has_cross_institution_matches && (
        <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-2 font-mono text-xs font-bold uppercase tracking-wider text-amber-400">
              <AlertTriangle className="w-4 h-4" /> Neo4j Cross-Institution Syndicate Correlation Detected
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 border border-amber-500/30 font-mono">
              Confidence: {((correlations.syndicate_confidence ?? 0.85) * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-xs leading-relaxed text-amber-200/90">
            Beneficiary accounts or VPAs from this case also appear in {correlations.total_correlated_cases_count} other independent case reports:
            <span className="font-mono text-white font-bold ml-1">
              {correlations.correlated_case_numbers?.join(", ")}
            </span>.
            {correlations.is_suspected_mule_ring && " Flagged as a coordinated Mule Fan-In Network."}
          </p>
        </div>
      )}

      {/* Escalation Cards Grid */}
      {escalations.length === 0 ? (
        <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 border-dashed space-y-3">
          <Building2 className="w-10 h-10 text-slate-500 mx-auto" />
          <h4 className="font-mono text-sm font-bold text-slate-300">No Institutional Alerts Generated Yet</h4>
          <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
            Click &quot;Trigger Bank Routing &amp; Extraction&quot; above to automatically parse UTR, IFSC prefixes, and beneficiary
            VPAs from the citizen narrative and generate coordinated dual-bank alerts.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {escalations.map((esc) => {
            const isVictim = esc.escalation_role === "VICTIM_BANK";
            const payload = esc.alert_payload || {};
            const txn = payload.transaction_details || {};
            const isAck = esc.status === "ACKNOWLEDGED";
            const isPending = esc.status === "PENDING_APPROVAL";

            return (
              <div
                key={esc.id}
                className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div className="space-y-3">
                  {/* Header Row */}
                  <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono uppercase tracking-wider ${
                            isVictim
                              ? "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                              : "bg-purple-500/15 text-purple-400 border border-purple-500/30"
                          }`}
                        >
                          {isVictim ? "Originating / Victim Bank" : "Destination / Beneficiary Bank"}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {esc.target_bank.integration_type || "SANDBOX_API"}
                        </span>
                      </div>
                      <h4 className="text-base font-bold text-white mt-1.5 flex items-center gap-1.5">
                        <Building2 className="w-4 h-4 text-emerald-400" />
                        {esc.target_bank.name}
                      </h4>
                      <p className="font-mono text-[11px] text-slate-400">
                        IFSC Prefix: <span className="text-slate-200 font-bold">{esc.target_bank.code}</span>
                      </p>
                    </div>

                    <div className="text-right shrink-0">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold font-mono uppercase ${
                          isAck
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : isPending
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : "bg-slate-800 text-slate-300"
                        }`}
                      >
                        {isAck && <CheckCircle2 className="w-3 h-3" />}
                        {isPending && <Clock className="w-3 h-3" />}
                        {esc.status}
                      </span>
                      <p className="text-[10px] font-mono text-slate-500 mt-1">Tier: {esc.approval_tier}</p>
                    </div>
                  </div>

                  {/* Transaction Artifacts */}
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 space-y-1.5 text-xs font-mono">
                    <div className="flex justify-between text-slate-300">
                      <span className="text-slate-500">Alert Ref:</span>
                      <span className="text-emerald-400 font-bold">{esc.alert_reference}</span>
                    </div>
                    {txn.reference_utr && (
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">UTR / RRN:</span>
                        <span className="text-white">{txn.reference_utr}</span>
                      </div>
                    )}
                    {txn.reported_loss_inr > 0 && (
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Reported Exposure:</span>
                        <span className="text-rose-400 font-bold">₹{txn.reported_loss_inr.toLocaleString("en-IN")}</span>
                      </div>
                    )}
                    {txn.beneficiary_vpa && (
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Suspect VPA:</span>
                        <span className="text-amber-400 truncate max-w-[200px]">{txn.beneficiary_vpa}</span>
                      </div>
                    )}
                    {txn.beneficiary_account && (
                      <div className="flex justify-between text-slate-300">
                        <span className="text-slate-500">Target Account:</span>
                        <span className="text-white">{txn.beneficiary_account}</span>
                      </div>
                    )}
                  </div>

                  {/* Requested Mandate */}
                  <div className="text-xs text-slate-400">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500 block mb-0.5">
                      Statutory Directive / Requested Action
                    </span>
                    <p className="leading-relaxed text-slate-300 bg-slate-900/90 p-2.5 rounded border border-slate-800 text-[11px]">
                      {payload.requested_action || "Account surveillance, debit hold, and statement correlation."}
                    </p>
                  </div>
                </div>

                {/* Actions Bar */}
                <div className="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                  <button
                    onClick={() => handleViewTimeline(esc.id)}
                    className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-emerald-400 transition-colors font-mono"
                  >
                    <FileText className="w-3.5 h-3.5" /> View Delivery Audit ({esc.delivery_attempts_count})
                  </button>

                  {isPending && (
                    <button
                      onClick={() => handleApproveAndDispatch(esc.id)}
                      disabled={actionLoading === esc.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold font-mono bg-emerald-600 hover:bg-emerald-500 text-white shadow transition-all disabled:opacity-50"
                    >
                      {actionLoading === esc.id ? (
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Send className="w-3.5 h-3.5" />
                      )}
                      Approve &amp; Dispatch Alert
                    </button>
                  )}

                  {isAck && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 font-bold">
                      <ShieldCheck className="w-3.5 h-3.5" /> Nodal Acknowledged
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Delivery Timeline Audit Modal */}
      {timelineModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <h3 className="font-mono text-sm font-bold text-white flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-400" /> Institutional Delivery Audit Trail
                </h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">
                  Ref: {timelineData?.alert_reference || "Loading..."}
                </p>
              </div>
              <button
                onClick={() => setTimelineModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {timelineLoading ? (
              <div className="p-8 text-center text-slate-400 font-mono text-xs flex items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" /> Loading Audit Ledger...
              </div>
            ) : (
              <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
                {/* Responses */}
                <div className="space-y-2">
                  <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                    Bank Institutional Responses ({timelineData?.responses?.length || 0})
                  </h4>
                  {timelineData?.responses?.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No formal response recorded yet.</p>
                  ) : (
                    timelineData.responses.map((resp: any, idx: number) => (
                      <div key={idx} className="p-3 rounded bg-slate-950 border border-slate-800 space-y-1 text-xs">
                        <div className="flex justify-between items-center text-slate-300">
                          <span className="font-mono font-bold text-emerald-400">{resp.response_type}</span>
                          <span className="font-mono text-[10px] text-slate-500">{resp.received_at}</span>
                        </div>
                        <p className="text-white font-medium">{resp.status_summary}</p>
                        {resp.bank_reference && (
                          <p className="font-mono text-[11px] text-slate-400">
                            Bank Reference: <span className="text-slate-200">{resp.bank_reference}</span>
                          </p>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {/* Delivery Attempts */}
                <div className="space-y-2 pt-2 border-t border-slate-800">
                  <h4 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                    Outbox Transmission Log ({timelineData?.delivery_attempts?.length || 0})
                  </h4>
                  {timelineData?.delivery_attempts?.map((att: any, idx: number) => (
                    <div key={idx} className="p-3 rounded bg-slate-950 border border-slate-800/80 text-xs font-mono space-y-1">
                      <div className="flex justify-between text-slate-400">
                        <span>Attempt #{att.attempt_number} via {att.channel}</span>
                        <span className="text-emerald-400 font-bold">HTTP {att.http_status_code}</span>
                      </div>
                      <div className="text-[11px] text-slate-500">{att.attempted_at}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
