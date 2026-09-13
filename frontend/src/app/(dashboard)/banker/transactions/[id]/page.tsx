"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useToast } from "@/components/ui/toast";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Rise } from "@/components/ui/motion";
import { TransactionRiskGraph } from "@/components/graph/transaction-risk-graph";
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Bot,
  Zap,
  Activity,
  CreditCard,
  Layers,
  Clock,
  Smartphone,
  MapPin,
  RefreshCw,
  UserCheck,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Send,
  Network,
  Share2,
  FileText
} from "lucide-react";

interface SubScores {
  amount?: number;
  velocity?: number;
  device?: number;
  beneficiary?: number;
  behaviour?: number;
  graph?: number;
  campaign?: number;
  [key: string]: number | undefined;
}

interface AttackDNA {
  matched?: boolean;
  dna_id?: string;
  dna_name?: string;
  description?: string;
  severity?: number;
  sequence?: string[];
  [key: string]: any;
}

interface FeedbackRecord {
  id: string;
  investigator_id?: string;
  ai_risk_score: number;
  ai_decision: string;
  human_decision: string;
  notes?: string;
  created_at?: string;
}

interface TransactionDetail {
  id: string;
  transaction_id: string;
  account_id: string;
  beneficiary_id: string;
  device_id?: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string;
  status: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  state?: string;
  channel: string;
  created_at: string;
  risk_score: number;
  confidence: number;
  risk_band: "LOW" | "GUARDED" | "ELEVATED" | "HIGH" | "CRITICAL";
  sub_scores: SubScores;
  model_version: string;
  decision: string;
  reason_codes: string[];
  explanation: string;
  features: Record<string, number>;
  raw_metadata: {
    attack_dna?: AttackDNA;
    graph_risk?: any;
    signals?: any[];
    [key: string]: any;
  };
  feedbacks: FeedbackRecord[];
}

export default function TransactionCockpitPage() {
  const params = useParams();
  const router = useRouter();
  const { token, user } = useAuthStore();
  const pushToast = useToast();

  const id = params?.id as string;

  const [transaction, setTransaction] = useState<TransactionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Graph state
  const [networkNodes, setNetworkNodes] = useState<any[]>([]);
  const [networkEdges, setNetworkEdges] = useState<any[]>([]);
  const [graphLoading, setGraphLoading] = useState(true);

  // Human Review Form state
  const [reviewDecision, setReviewDecision] = useState<string>("CONFIRMED_FRAUD");
  const [reviewNotes, setReviewNotes] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  const fetchTransaction = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      const res = await axios.get(api(`/transactions/${id}`));
      setTransaction(res.data);

      // Fetch network graph for source account
      if (res.data.account_id) {
        try {
          setGraphLoading(true);
          const netRes = await axios.get(api(`/transactions/accounts/${res.data.account_id}/risk-network`));
          setNetworkNodes(netRes.data.nodes || []);
          setNetworkEdges(netRes.data.edges || []);
        } catch (netErr) {
          console.error("Failed to load risk network graph:", netErr);
        } finally {
          setGraphLoading(false);
        }
      }
    } catch (err: any) {
      console.error("Failed to fetch transaction detail:", err);
      pushToast("danger", "Unable to load transaction details. Check identifier.");
    } finally {
      setLoading(false);
    }
  }, [id, pushToast]);

  useEffect(() => {
    fetchTransaction();
  }, [fetchTransaction]);

  const handleRunForensicAnalysis = async () => {
    if (!id) return;
    try {
      setAnalyzing(true);
      const res = await axios.post(api(`/transactions/${id}/analyze`));
      if (transaction) {
        setTransaction({
          ...transaction,
          explanation: res.data.explanation,
          risk_score: res.data.risk_score,
          risk_band: res.data.risk_band,
          confidence: res.data.confidence,
          decision: res.data.decision,
          reason_codes: res.data.reason_codes,
          sub_scores: res.data.sub_scores || transaction.sub_scores,
        });
      }
      pushToast("success", "AI Forensic Brief generated successfully.");
    } catch (err: any) {
      console.error("Failed to generate forensic analysis:", err);
      pushToast("danger", "Failed to enrich narrative. Local AI offline.");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSubmitReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;
    try {
      setSubmittingReview(true);
      const investigatorId = user?.email || user?.full_name || "banker-operator";
      await axios.post(
        api(`/transactions/${id}/review`),
        {
          human_decision: reviewDecision,
          notes: reviewNotes,
          investigator_id: investigatorId
        },
        token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
      );

      pushToast("success", `Human review recorded as ${reviewDecision.replace("_", " ")}.`);
      setReviewNotes("");
      await fetchTransaction();
    } catch (err: any) {
      console.error("Failed to submit review:", err);
      pushToast("danger", err.response?.data?.detail || "Failed to record human review.");
    } finally {
      setSubmittingReview(false);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-3">
        <RefreshCw className="w-7 h-7 text-accent animate-spin" />
        <p className="text-ink-3 text-sm font-mono">Loading transaction intelligence dossier...</p>
      </div>
    );
  }

  if (!transaction) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle className="w-10 h-10 text-warning" />
        <h2 className="text-xl font-bold text-ink">Transaction Not Found</h2>
        <p className="text-ink-3 text-sm">Could not find record for identifier &quot;{id}&quot;.</p>
        <Link href="/banker/transactions">
          <Button variant="secondary" className="gap-2">
            <ArrowLeft className="w-4 h-4" /> Back to Risk Feed
          </Button>
        </Link>
      </div>
    );
  }

  const riskPct = Math.round(transaction.risk_score * 100);
  const confPct = Math.round(transaction.confidence * 100);
  const attackDNA = transaction.raw_metadata?.attack_dna;

  const bandTone = (band: string) => {
    switch (band) {
      case "CRITICAL":
        return "danger";
      case "HIGH":
        return "peach";
      case "ELEVATED":
        return "warning";
      case "GUARDED":
        return "accent";
      default:
        return "success";
    }
  };

  const decisionBadgeConfig = (decision: string) => {
    switch (decision) {
      case "APPROVE":
        return {
          label: "Instant Pass",
          tone: "success" as const,
          desc: "Transaction clears deterministic velocity, device, and behavioral bounds. No user friction applied."
        };
      case "APPROVE_AND_MONITOR":
        return {
          label: "Approve & Monitor",
          tone: "accent" as const,
          desc: "Passed with non-intrusive background monitoring. Audit ledger flag active."
        };
      case "STEP_UP_VERIFICATION":
        return {
          label: "Step-Up Verification",
          tone: "warning" as const,
          desc: "Elevated anomaly profile. Biometric challenge or in-app 2FA step-up required."
        };
      case "TEMPORARY_HOLD":
        return {
          label: "Temporary Hold",
          tone: "peach" as const,
          desc: "High anomaly detected. 15-minute freeze engaged with push notification to account owner."
        };
      case "HOLD_AND_INVESTIGATE":
        return {
          label: "Hold & Investigate",
          tone: "danger" as const,
          desc: "Critical fraud probability / Attack DNA match. Transaction frozen and escalated for forensic review."
        };
      default:
        return {
          label: decision,
          tone: "neutral" as const,
          desc: "Evaluated according to bank friction policies."
        };
    }
  };

  const decisionInfo = decisionBadgeConfig(transaction.decision);

  const subScoreFactors = [
    { key: "amount", label: "Amount Anomaly", desc: "Z-score deviation vs user baseline", val: transaction.sub_scores.amount ?? 0 },
    { key: "velocity", label: "Velocity Spike", desc: "1m / 5m / 1h transaction frequency", val: transaction.sub_scores.velocity ?? 0 },
    { key: "device", label: "Device Integrity", desc: "New device / emulator / multi-account", val: transaction.sub_scores.device ?? 0 },
    { key: "beneficiary", label: "Beneficiary Risk", desc: "New payee / dormant spike / mule flag", val: transaction.sub_scores.beneficiary ?? 0 },
    { key: "behaviour", label: "Behavioral Deviation", desc: "Geo-impossible travel & off-hour siphon", val: transaction.sub_scores.behaviour ?? 0 },
    { key: "graph", label: "Graph Ring Density", desc: "Neo4j 2-hop shared device & mule cluster", val: transaction.sub_scores.graph ?? 0 },
    { key: "campaign", label: "Attack Campaign Coherence", desc: "Similarity to active coordinated waves", val: transaction.sub_scores.campaign ?? 0 },
  ];

  return (
    <Rise className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Breadcrumb & Navigation Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-line/15 pb-4">
        <div className="flex items-center gap-3">
          <Link href="/banker/transactions">
            <Button variant="ghost" size="sm" className="gap-1.5 text-ink-2 hover:text-ink">
              <ArrowLeft className="w-4 h-4" />
              <span>Risk Feed</span>
            </Button>
          </Link>
          <span className="text-line/60">/</span>
          <span className="font-mono text-xs font-semibold text-ink-3">COCKPIT</span>
          <span className="text-line/60">/</span>
          <h1 className="font-mono text-sm font-bold text-ink">{transaction.transaction_id}</h1>
          <Badge tone="accent" className="font-mono text-[10px] uppercase">
            {transaction.transaction_type}
          </Badge>
          <Badge tone={bandTone(transaction.risk_band)} className="text-[10px]">
            {transaction.risk_band}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={fetchTransaction}
            className="gap-1.5 text-xs"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRunForensicAnalysis}
            disabled={analyzing}
            className="gap-1.5 text-xs shadow-sm"
          >
            <Bot className={`w-3.5 h-3.5 ${analyzing ? "animate-spin" : ""}`} />
            {analyzing ? "Analyzing AI Copilot..." : "Generate AI Forensic Brief"}
          </Button>
        </div>
      </div>

      {/* Attack DNA Signature Alert Banner (Conditional) */}
      {attackDNA && attackDNA.matched && (
        <div className="rounded-card border border-red-500/30 bg-gradient-to-r from-red-950/40 via-red-900/20 to-surface-2 p-4 shadow-md">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-control bg-red-500/20 text-red-400 border border-red-500/30">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-red-400 tracking-wide uppercase">
                    Coordinated Attack DNA Detected
                  </span>
                  <Badge tone="danger" className="text-[10px] font-mono">
                    SEV {Math.round((attackDNA.severity || 0.8) * 100)}%
                  </Badge>
                </div>
                <h3 className="text-base font-bold text-ink mt-0.5">{attackDNA.dna_name || attackDNA.dna_id}</h3>
                <p className="text-xs text-ink-2 max-w-2xl mt-1">{attackDNA.description}</p>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[10px] uppercase tracking-wider text-red-400/80 font-mono font-semibold">
                Attack Signature ID
              </span>
              <p className="font-mono text-xs text-ink font-bold">{attackDNA.dna_id}</p>
            </div>
          </div>

          {/* Sequence Match Flow */}
          {attackDNA.sequence && attackDNA.sequence.length > 0 && (
            <div className="mt-3.5 pt-3 border-t border-red-500/20">
              <p className="text-[11px] font-mono text-red-300 font-semibold mb-2 uppercase">
                Sequential Fingerprint Vectors:
              </p>
              <div className="flex flex-wrap items-center gap-2">
                {attackDNA.sequence.map((step: string, idx: number) => (
                  <div key={idx} className="flex items-center gap-1.5">
                    <span className="px-2 py-1 bg-red-950/60 border border-red-500/30 rounded-control font-mono text-[11px] text-red-200">
                      <span className="text-red-400 font-bold mr-1">#{idx + 1}</span> {step}
                    </span>
                    {idx < (attackDNA.sequence?.length ?? 0) - 1 && (
                      <span className="text-red-400/60 font-mono text-xs">→</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Main KPI Summary Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Transaction Amount & Flow */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-ink-3">
            <span>Transaction Value</span>
            <CreditCard className="w-4 h-4 text-ink-3" />
          </div>
          <div className="my-2">
            <span className="text-2xl font-bold font-mono text-ink tracking-tight">
              ₹{transaction.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </span>
            <span className="text-xs text-ink-3 ml-2">{transaction.currency}</span>
          </div>
          <div className="text-[11px] text-ink-2 flex items-center justify-between border-t border-line/10 pt-2 font-mono">
            <span>Rail: {transaction.transaction_type}</span>
            <span>Channel: {transaction.channel}</span>
          </div>
        </Card>

        {/* Card 2: Risk Score & Band */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-ink-3">
            <span>Composite Risk Score</span>
            <ShieldAlert className="w-4 h-4 text-warning" />
          </div>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold font-mono text-ink">{riskPct}%</span>
            <Badge tone={bandTone(transaction.risk_band)} className="text-xs font-bold">
              {transaction.risk_band}
            </Badge>
          </div>
          <div className="w-full bg-surface-3/40 h-2 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                riskPct >= 88
                  ? "bg-rose-500"
                  : riskPct >= 70
                  ? "bg-orange-500"
                  : riskPct >= 45
                  ? "bg-amber-500"
                  : riskPct >= 20
                  ? "bg-sky-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${riskPct}%` }}
            />
          </div>
        </Card>

        {/* Card 3: Adaptive Friction Action */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-ink-3">
            <span>Adaptive Friction Decision</span>
            <Zap className="w-4 h-4 text-accent" />
          </div>
          <div className="my-2">
            <Badge tone={decisionInfo.tone} className="text-xs px-2.5 py-1 font-bold">
              {decisionInfo.label}
            </Badge>
          </div>
          <p className="text-[11px] text-ink-3 leading-tight line-clamp-2">
            {decisionInfo.desc}
          </p>
        </Card>

        {/* Card 4: Model Confidence & Status */}
        <Card className="p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-ink-3">
            <span>Telemetry Confidence</span>
            <Activity className="w-4 h-4 text-ink-3" />
          </div>
          <div className="my-2 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-ink">{confPct}%</span>
            <span className="font-mono text-xs text-ink-3 font-semibold uppercase">
              STATUS: {transaction.status}
            </span>
          </div>
          <div className="text-[11px] text-ink-3 flex items-center justify-between border-t border-line/10 pt-2 font-mono">
            <span>Engine: {transaction.model_version}</span>
            <span>{new Date(transaction.timestamp).toLocaleTimeString()}</span>
          </div>
        </Card>
      </div>

      {/* Grid: 7-Factor Radar Breakdown + AI Natural Language Forensic Brief */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 7-Factor Risk Radar (5 cols) */}
        <Card className="lg:col-span-5 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-line/15 pb-2.5">
              <div>
                <h2 className="text-sm font-bold text-ink flex items-center gap-2">
                  <Layers className="w-4 h-4 text-accent" /> 7-Factor Risk Decomposition
                </h2>
                <p className="text-xs text-ink-3 mt-0.5">Deterministic multi-vector anomaly breakdown</p>
              </div>
              <Badge tone="neutral" className="text-[10px] font-mono">
                NORMALIZED
              </Badge>
            </div>

            <div className="space-y-3.5 mt-4">
              {subScoreFactors.map((factor) => {
                const score = Math.round(factor.val * 100);
                const scoreColor =
                  score >= 80
                    ? "text-rose-400 bg-rose-500"
                    : score >= 50
                    ? "text-orange-400 bg-orange-500"
                    : score >= 30
                    ? "text-amber-400 bg-amber-500"
                    : "text-emerald-400 bg-emerald-500";

                return (
                  <div key={factor.key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <div>
                        <span className="font-semibold text-ink">{factor.label}</span>
                        <span className="text-[10px] text-ink-3 ml-2 hidden sm:inline">({factor.desc})</span>
                      </div>
                      <span className="font-mono font-bold text-xs">{score}%</span>
                    </div>
                    <div className="w-full bg-surface-3/30 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${scoreColor.split(" ")[1]}`}
                        style={{ width: `${score}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Telemetry & Reason Codes Footer */}
          <div className="mt-6 pt-4 border-t border-line/15">
            <span className="text-xs font-bold text-ink-2 uppercase tracking-wide block mb-2 font-mono">
              Deterministic Reason Codes ({transaction.reason_codes.length})
            </span>
            <div className="flex flex-wrap gap-1.5">
              {transaction.reason_codes.length > 0 ? (
                transaction.reason_codes.map((code) => (
                  <Badge key={code} tone="peach" className="font-mono text-[11px]">
                    {code}
                  </Badge>
                ))
              ) : (
                <span className="text-xs text-ink-3 italic">No anomaly triggers active. Clean baseline.</span>
              )}
            </div>
          </div>
        </Card>

        {/* Right Column: AI Natural Language Forensic Brief (7 cols) */}
        <Card className="lg:col-span-7 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 border-b border-line/15 pb-2.5">
              <div className="flex items-center gap-2.5">
                <div className="p-1.5 rounded-control bg-accent/10 text-accent">
                  <Bot className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-ink">AI Forensic Investigation Brief</h2>
                  <p className="text-xs text-ink-3">Synthesized investigator dossier & actionable recommendation</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-ink-3">Inference:</span>
                <Badge tone="accent" className="font-mono text-[10px]">
                  llama3:8b (Local Ollama)
                </Badge>
              </div>
            </div>

            <div className="prose prose-invert max-w-none text-xs leading-relaxed text-ink-2 bg-surface-2/30 rounded-control p-4 border border-line/15 min-h-[220px] whitespace-pre-line font-sans">
              {transaction.explanation}
            </div>
          </div>

          {/* Key Identifiers Grid */}
          <div className="mt-4 pt-3 border-t border-line/15 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div>
              <span className="text-ink-3 text-[10px] uppercase block">Source Account</span>
              <span className="font-semibold text-ink truncate block" title={transaction.account_id}>
                {transaction.account_id}
              </span>
            </div>
            <div>
              <span className="text-ink-3 text-[10px] uppercase block">Beneficiary (VPA)</span>
              <span className="font-semibold text-ink truncate block" title={transaction.beneficiary_id}>
                {transaction.beneficiary_id}
              </span>
            </div>
            <div>
              <span className="text-ink-3 text-[10px] uppercase block">Device Fingerprint</span>
              <span className="font-semibold text-ink truncate block" title={transaction.device_id || "N/A"}>
                {transaction.device_id || "None Recorded"}
              </span>
            </div>
            <div>
              <span className="text-ink-3 text-[10px] uppercase block">Geo-Location</span>
              <span className="font-semibold text-ink truncate block">
                {transaction.city || "Unknown City"}, {transaction.state || "IN"}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Account 2-Hop Risk Network Graph (Cytoscape) */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-control bg-blue-500/10 text-blue-400">
              <Network className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-ink">Account Risk Network (2-Hop Topology)</h2>
              <p className="text-xs text-ink-3">
                Neo4j graph view linking Account ({transaction.account_id}) to transactions, payees, and shared devices
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-ink-3">
            <span>Nodes: {networkNodes.length}</span>
            <span>•</span>
            <span>Edges: {networkEdges.length}</span>
          </div>
        </div>

        {graphLoading ? (
          <div className="h-[380px] w-full flex items-center justify-center bg-surface-2/20 rounded-card border border-line/15 text-xs text-ink-3">
            <RefreshCw className="w-5 h-5 animate-spin mr-2 text-accent" />
            Querying Neo4j 2-hop neighborhood graph...
          </div>
        ) : networkNodes.length === 0 ? (
          <div className="h-[240px] w-full flex flex-col items-center justify-center bg-surface-2/20 rounded-card border border-line/15 text-xs text-ink-3 gap-2">
            <Share2 className="w-6 h-6 text-ink-3" />
            <p>No interconnected 2-hop graph entities recorded for account {transaction.account_id} yet.</p>
          </div>
        ) : (
          <TransactionRiskGraph nodes={networkNodes} edges={networkEdges} height="400px" />
        )}
      </Card>

      {/* Human Investigator Review & Feedback Loop */}
      <Card className="p-5">
        <div className="flex items-center gap-2.5 mb-4 border-b border-line/15 pb-3">
          <div className="p-1.5 rounded-control bg-purple-500/10 text-purple-400">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-ink">Banker / Investigator Final Verdict (Active Learning Loop)</h2>
            <p className="text-xs text-ink-3">
              Your decision updates transaction status and calibrates beneficiary/device risk profiles in real-time
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Form */}
          <form onSubmit={handleSubmitReview} className="lg:col-span-7 space-y-4">
            <div>
              <label className="text-xs font-semibold text-ink-2 block mb-1.5">
                Investigator Human Verdict
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                <button
                  type="button"
                  onClick={() => setReviewDecision("CONFIRMED_FRAUD")}
                  className={`p-3 rounded-control border text-left transition-all ${
                    reviewDecision === "CONFIRMED_FRAUD"
                      ? "border-rose-500 bg-rose-950/40 text-rose-300 shadow-sm"
                      : "border-line/20 bg-surface-2/40 text-ink-2 hover:border-line/40"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs">
                    <XCircle className="w-3.5 h-3.5 text-rose-400" />
                    <span>Confirmed Fraud</span>
                  </div>
                  <p className="text-[10px] text-ink-3 mt-1 leading-tight">
                    Reject txn, blacklist payee, escalate device threat.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setReviewDecision("FALSE_POSITIVE")}
                  className={`p-3 rounded-control border text-left transition-all ${
                    reviewDecision === "FALSE_POSITIVE"
                      ? "border-emerald-500 bg-emerald-950/40 text-emerald-300 shadow-sm"
                      : "border-line/20 bg-surface-2/40 text-ink-2 hover:border-line/40"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>False Positive</span>
                  </div>
                  <p className="text-[10px] text-ink-3 mt-1 leading-tight">
                    Approve txn, ease beneficiary penalty, tune weights.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setReviewDecision("LEGITIMATE_ANOMALY")}
                  className={`p-3 rounded-control border text-left transition-all ${
                    reviewDecision === "LEGITIMATE_ANOMALY"
                      ? "border-amber-500 bg-amber-950/40 text-amber-300 shadow-sm"
                      : "border-line/20 bg-surface-2/40 text-ink-2 hover:border-line/40"
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-bold text-xs">
                    <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                    <span>Legit Anomaly</span>
                  </div>
                  <p className="text-[10px] text-ink-3 mt-1 leading-tight">
                    Emergency/vacation purchase. Safe to approve.
                  </p>
                </button>
              </div>
            </div>

            <div>
              <label className="text-xs font-semibold text-ink-2 block mb-1.5">
                Reviewer Case Notes & Justification
              </label>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Document verification steps (e.g., user phoned via bank branch, verified transaction OTP, or confirmed mule account ring)..."
                rows={3}
                className="w-full rounded-control bg-surface-2 border border-line/20 p-2.5 text-xs text-ink placeholder:text-ink-3 focus:outline-hidden focus:border-accent"
              />
            </div>

            <Button
              type="submit"
              variant="primary"
              disabled={submittingReview}
              className="gap-2 text-xs"
            >
              <Send className={`w-3.5 h-3.5 ${submittingReview ? "animate-spin" : ""}`} />
              {submittingReview ? "Persisting Human Feedback..." : "Record Human Decision & Update Status"}
            </Button>
          </form>

          {/* Review Audit History */}
          <div className="lg:col-span-5 bg-surface-2/30 rounded-control border border-line/15 p-4 flex flex-col justify-between">
            <div>
              <h3 className="text-xs font-bold text-ink uppercase tracking-wider mb-2 font-mono">
                Feedback Audit Ledger ({transaction.feedbacks?.length || 0})
              </h3>
              {transaction.feedbacks && transaction.feedbacks.length > 0 ? (
                <div className="space-y-2.5 max-h-[190px] overflow-y-auto pr-1">
                  {transaction.feedbacks.map((fb) => (
                    <div
                      key={fb.id}
                      className="p-2.5 rounded-control bg-surface-1 border border-line/15 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <Badge
                          tone={
                            fb.human_decision === "CONFIRMED_FRAUD"
                              ? "danger"
                              : fb.human_decision === "FALSE_POSITIVE"
                              ? "success"
                              : "warning"
                          }
                          className="text-[10px] font-mono"
                        >
                          {fb.human_decision}
                        </Badge>
                        <span className="text-[10px] font-mono text-ink-3">
                          {fb.created_at ? new Date(fb.created_at).toLocaleDateString() : ""}
                        </span>
                      </div>
                      <p className="text-[11px] text-ink-2">{fb.notes || "No notes provided."}</p>
                      <span className="text-[10px] font-mono text-ink-3 block">
                        Analyst: {fb.investigator_id || "Anonymous"}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-32 text-center text-xs text-ink-3">
                  <FileText className="w-5 h-5 text-ink-3 mb-1" />
                  <p>No human reviews recorded yet for this transaction.</p>
                  <p className="text-[11px]">Submit verdict above to initialize the feedback ledger.</p>
                </div>
              )}
            </div>

            <div className="mt-3 pt-2.5 border-t border-line/10 text-[11px] text-ink-3 font-mono">
              Audit log immutable via PostgreSQL `transaction_feedback`
            </div>
          </div>
        </div>
      </Card>
    </Rise>
  );
}
