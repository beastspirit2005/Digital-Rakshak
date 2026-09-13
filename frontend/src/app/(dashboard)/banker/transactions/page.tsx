"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import axios from "axios";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatBlock } from "@/components/ui/stat";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";
import {
  Activity,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Search,
  ExternalLink,
  Zap,
  Filter,
  CheckCircle2,
  XCircle,
  Clock,
  Smartphone,
  Layers,
  ArrowUpRight,
  Wifi,
  WifiOff,
  Plus,
  CreditCard,
  UploadCloud,
  Code2
} from "lucide-react";
import { useTransactionStream, TransactionStreamItem, ReviewStreamItem } from "@/hooks/use-transaction-stream";
import { IngestTransactionModal } from "@/components/transactions/ingest-transaction-modal";

interface RiskFeedItem {
  id: string;
  transaction_id: string;
  account_id: string;
  beneficiary_id: string;
  amount: number;
  transaction_type: string;
  timestamp: string;
  risk_score: number;
  confidence: number;
  risk_band: "LOW" | "GUARDED" | "ELEVATED" | "HIGH" | "CRITICAL";
  decision: string;
  top_reason_code?: string;
}

interface CampaignWave {
  dna_id: string;
  dna_name: string;
  description: string;
  severity: number;
  transaction_count: number;
  total_amount_at_risk: number;
  unique_accounts_count: number;
  unique_beneficiaries_count: number;
  first_detected: string;
  last_detected: string;
}

export default function TransactionMonitoringPage() {
  const { token } = useAuthStore();
  const pushToast = useToast();

  const [feed, setFeed] = useState<RiskFeedItem[]>([]);
  const [campaigns, setCampaigns] = useState<CampaignWave[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBand, setSelectedBand] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  // Real Transaction Ingestion Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalTab, setModalTab] = useState<"manual" | "csv" | "webhook">("manual");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simType, setSimType] = useState<"normal" | "fraud">("fraud");

  const [highlightedTxnId, setHighlightedTxnId] = useState<string | null>(null);

  const handleStreamTransaction = useCallback((newTxn: TransactionStreamItem) => {
    setFeed((prev) => {
      if (prev.some((item) => item.transaction_id === newTxn.transaction_id)) {
        return prev;
      }
      return [
        {
          id: newTxn.id,
          transaction_id: newTxn.transaction_id,
          account_id: newTxn.account_id,
          beneficiary_id: newTxn.beneficiary_id,
          amount: newTxn.amount,
          transaction_type: newTxn.transaction_type,
          timestamp: newTxn.timestamp,
          risk_score: newTxn.risk_score,
          confidence: newTxn.confidence,
          risk_band: newTxn.risk_band,
          decision: newTxn.decision,
          top_reason_code: newTxn.top_reason_code
        },
        ...prev.slice(0, 49)
      ];
    });
    setTotalCount((prev) => prev + 1);
    setHighlightedTxnId(newTxn.transaction_id);

    setTimeout(() => {
      setHighlightedTxnId((curr) => (curr === newTxn.transaction_id ? null : curr));
    }, 4000);

    if (newTxn.risk_band === "CRITICAL" || newTxn.risk_band === "HIGH") {
      pushToast(
        "danger",
        `🚨 High Risk Alert: ${newTxn.transaction_id} (₹${newTxn.amount.toLocaleString("en-IN")}) flagged as ${newTxn.decision}`
      );
    }
  }, [pushToast]);

  const handleStreamReview = useCallback((review: ReviewStreamItem) => {
    setFeed((prev) =>
      prev.map((item) =>
        item.transaction_id === review.transaction_id
          ? { ...item, decision: review.new_status }
          : item
      )
    );
    pushToast("info", `Review recorded for ${review.transaction_id}: ${review.human_decision}`);
  }, [pushToast]);

  const { isConnected, status: streamStatus, reconnect: reconnectStream } = useTransactionStream({
    onTransaction: handleStreamTransaction,
    onReview: handleStreamReview,
    enabled: autoRefresh,
  });

  const fetchData = useCallback(async () => {
    try {
      let url = api("/transactions/risk-feed?limit=50");
      if (selectedBand !== "ALL") url += `&risk_band=${selectedBand}`;
      if (selectedStatus !== "ALL") url += `&status=${selectedStatus}`;

      const [feedRes, campRes] = await Promise.all([
        axios.get(url),
        axios.get(api("/transactions/campaigns"))
      ]);

      setFeed(feedRes.data.items || []);
      setTotalCount(feedRes.data.total || 0);
      setCampaigns(campRes.data.campaigns || []);
    } catch (err: any) {
      console.error("Failed to load transaction risk feed:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedBand, selectedStatus]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Adaptive polling: 30s when live WebSocket is connected, 6s when offline fallback
  useEffect(() => {
    if (!autoRefresh) return;
    const intervalMs = isConnected ? 30000 : 6000;
    const interval = setInterval(() => {
      fetchData();
    }, intervalMs);
    return () => clearInterval(interval);
  }, [autoRefresh, isConnected, fetchData]);

  // Quick Ingestion Simulation
  const handleSimulate = async () => {
    setIsSimulating(true);
    try {
      const now = new Date();
      let payload;

      if (simType === "fraud") {
        now.setHours(3, 15, 0, 0); // 3:15 AM off-hours
        payload = {
          account_id: "ACC-VICTIM-" + Math.floor(1000 + Math.random() * 9000),
          beneficiary_id: "syndicate_mule_" + Math.floor(10 + Math.random() * 90) + "@ybl",
          device_id: "DEV-EMULATOR-" + Math.floor(100 + Math.random() * 900),
          amount: 87500.0,
          channel: "UPI",
          timestamp: now.toISOString(),
          raw_metadata: {
            device_profile: {
              is_emulator: true,
              risk_score: 0.92,
              associated_accounts: ["ACC-1", "ACC-2", "ACC-3"]
            },
            beneficiary_profile: {
              is_flagged: true,
              risk_score: 0.95
            },
            graph_risk: 0.88
          }
        };
      } else {
        payload = {
          account_id: "ACC-USER-" + Math.floor(1000 + Math.random() * 9000),
          beneficiary_id: "local_merchant@upi",
          device_id: "DEV-PHONE-" + Math.floor(100 + Math.random() * 900),
          amount: 420.0,
          channel: "UPI",
          timestamp: now.toISOString()
        };
      }

      const res = await axios.post(api("/transactions/"), payload);
      pushToast(
        simType === "fraud" ? "warning" : "success",
        `Transaction ${res.data.transaction_id} ingested: Decision = ${res.data.decision}`
      );
      fetchData();
    } catch (err: any) {
      pushToast("danger", "Simulation failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setIsSimulating(false);
    }
  };

  const filteredFeed = feed.filter((item) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      item.transaction_id.toLowerCase().includes(q) ||
      item.account_id.toLowerCase().includes(q) ||
      item.beneficiary_id.toLowerCase().includes(q) ||
      (item.top_reason_code && item.top_reason_code.toLowerCase().includes(q))
    );
  });

  const getBandBadge = (band: string) => {
    switch (band) {
      case "CRITICAL":
        return <Badge tone="danger" className="font-bold animate-pulse">CRITICAL</Badge>;
      case "HIGH":
        return <Badge tone="peach" className="font-bold">HIGH</Badge>;
      case "ELEVATED":
        return <Badge tone="warning">ELEVATED</Badge>;
      case "GUARDED":
        return <Badge tone="lilac">GUARDED</Badge>;
      default:
        return <Badge tone="success">LOW RISK</Badge>;
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case "APPROVE":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-success">
            <CheckCircle2 className="w-3.5 h-3.5" /> Approved
          </span>
        );
      case "APPROVE_AND_MONITOR":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-lilac-text">
            <Activity className="w-3.5 h-3.5" /> Monitored
          </span>
        );
      case "STEP_UP_VERIFICATION":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-warning">
            <AlertTriangle className="w-3.5 h-3.5" /> Step-Up OTP
          </span>
        );
      case "TEMPORARY_HOLD":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-peach-text">
            <Clock className="w-3.5 h-3.5" /> Temp Hold
          </span>
        );
      case "HOLD_AND_INVESTIGATE":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-danger">
            <ShieldAlert className="w-3.5 h-3.5" /> Full Hold
          </span>
        );
      default:
        return <span className="text-xs text-ink-3">{decision}</span>;
    }
  };

  // KPI Calculations
  const heldCount = feed.filter((t) => t.decision.includes("HOLD") || t.decision.includes("STEP_UP")).length;
  const approvedCount = feed.filter((t) => t.decision.includes("APPROVE")).length;

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <PageHeader
        title="Transaction Fraud Intelligence"
        sub="Real-time autonomous AI monitoring, velocity anomaly telemetry & adaptive friction decisioning."
        actions={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-surface-2 border border-line/15 text-xs text-ink-2">
              {isConnected ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-xs shadow-emerald-500" />
                  <span className="font-semibold text-emerald-400 flex items-center gap-1">
                    <Wifi className="w-3 h-3" /> Live Stream (WebSocket)
                  </span>
                </>
              ) : streamStatus === "CONNECTING" ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                  <span className="font-medium text-amber-400">Connecting Stream...</span>
                </>
              ) : (
                <>
                  <span className="w-2 h-2 rounded-full bg-ink-4" />
                  <span className="font-medium text-ink-3 flex items-center gap-1">
                    <WifiOff className="w-3 h-3" /> {autoRefresh ? "Polling Mode" : "Stream Paused"}
                  </span>
                </>
              )}
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="text-xs"
            >
              {autoRefresh ? "Pause" : "Resume"}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => fetchData()}
              disabled={loading}
              className="text-xs gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>

            {/* Real Transaction Ingestion & Bank Switch Hooks */}
            <div className="flex items-center gap-1.5 ml-2 pl-2 border-l border-line/15">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setModalTab("csv");
                  setModalOpen(true);
                }}
                className="text-xs gap-1.5 font-medium"
              >
                <UploadCloud className="w-3.5 h-3.5 text-accent" />
                Bulk Statement CSV
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setModalTab("manual");
                  setModalOpen(true);
                }}
                className="text-xs gap-1.5 font-bold shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                Ingest Transaction
              </Button>
              <button
                type="button"
                onClick={() => {
                  setModalTab("webhook");
                  setModalOpen(true);
                }}
                title="View Bank & UPI Switch Webhook Integration Guide"
                className="p-1.5 rounded-md text-ink-3 hover:text-accent hover:bg-surface-2 transition-colors border border-line/15"
              >
                <Code2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        }
      />

      {/* KPI Stats Grid */}
      <Rise index={1}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatBlock
            label="Monitored Transactions"
            value={totalCount}
            hint="Live ledger ingestion stream"
          />
          <StatBlock
            label="Automated Pass-Through"
            value={approvedCount}
            hint={`${totalCount ? Math.round((approvedCount / totalCount) * 100) : 0}% clearance`}
            delta="PASS"
            deltaPositive={true}
          />
          <StatBlock
            label="Elevated Risk & Step-Up"
            value={heldCount}
            hint="Adaptive challenge"
            delta="ACTIVE"
            deltaPositive={false}
          />
          <StatBlock
            label="Active Attack Waves"
            value={campaigns.length}
            hint="Coordinated DNA clusters"
          />
        </div>
      </Rise>

      {/* Active Attack DNA Wave Campaigns */}
      {campaigns.length > 0 && (
        <Rise index={2}>
          <Card className="p-5 border-danger/30 bg-surface-1">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-control bg-danger-tint text-danger">
                  <ShieldAlert className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-ink flex items-center gap-2">
                    Active Coordinated Attack DNA Waves
                    <Badge tone="danger" className="text-xs">
                      {campaigns.length} Detected
                    </Badge>
                  </h3>
                  <p className="text-xs text-ink-3">
                    Multi-account syndicate signatures identified across real-time transaction velocity
                  </p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {campaigns.map((camp) => (
                <div
                  key={camp.dna_id}
                  className="p-3.5 rounded-control bg-surface-2 border border-line/20 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-danger">
                        {camp.dna_id}
                      </span>
                      <Badge tone="danger" className="text-[10px]">
                        SEV {Math.round(camp.severity * 100)}%
                      </Badge>
                    </div>
                    <h4 className="text-sm font-semibold text-ink mt-1">{camp.dna_name}</h4>
                    <p className="text-xs text-ink-3 mt-1 line-clamp-2">{camp.description}</p>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-line/10 grid grid-cols-2 gap-2 text-xs font-mono">
                    <div>
                      <span className="text-ink-4 text-[10px] block">Transactions</span>
                      <span className="font-semibold text-ink">{camp.transaction_count}</span>
                    </div>
                    <div>
                      <span className="text-ink-4 text-[10px] block">At Risk</span>
                      <span className="font-semibold text-danger">
                        ₹{camp.total_amount_at_risk.toLocaleString("en-IN")}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </Rise>
      )}

      {/* Filter Controls & Search */}
      <Rise index={3}>
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-card bg-surface-1 border border-line/15">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-ink-3 mr-1 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" /> Risk Band:
            </span>
            {["ALL", "LOW", "GUARDED", "ELEVATED", "HIGH", "CRITICAL"].map((band) => (
              <button
                key={band}
                onClick={() => setSelectedBand(band)}
                className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-colors ${
                  selectedBand === band
                    ? "bg-ink text-surface"
                    : "bg-surface-2 text-ink-2 hover:bg-surface-3"
                }`}
              >
                {band}
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-ink-4" />
            <input
              type="text"
              placeholder="Search account, payee, ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-control bg-surface-2 border border-line/20 text-xs text-ink placeholder:text-ink-4 focus:outline-hidden focus:border-accent"
            />
          </div>
        </div>
      </Rise>

      {/* Transactions Table */}
      <Rise index={4}>
        <Card className="overflow-hidden border border-line/15">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-surface-2 border-b border-line/15 text-ink-3 font-mono uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-4 font-bold">Transaction ID</th>
                  <th className="py-3 px-4 font-bold">Time / Rail</th>
                  <th className="py-3 px-4 font-bold">Source Account</th>
                  <th className="py-3 px-4 font-bold">Beneficiary VPA</th>
                  <th className="py-3 px-4 font-bold text-right">Amount (₹)</th>
                  <th className="py-3 px-4 font-bold">Risk Assessment</th>
                  <th className="py-3 px-4 font-bold">Adaptive Action</th>
                  <th className="py-3 px-4 font-bold">Primary Reason</th>
                  <th className="py-3 px-4 font-bold text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line/10">
                {loading && feed.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-12 text-ink-3">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="w-4 h-4 animate-spin text-accent" />
                        <span>Connecting to transaction feed...</span>
                      </div>
                    </td>
                  </tr>
                ) : filteredFeed.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-12 text-ink-3">
                      No transactions match the selected criteria.
                    </td>
                  </tr>
                ) : (
                  filteredFeed.map((item) => {
                    const isNewStreamItem = highlightedTxnId === item.transaction_id;
                    return (
                      <tr
                        key={item.id}
                        className={`transition-all duration-700 ${
                          isNewStreamItem
                            ? "bg-accent/15 border-l-4 border-accent shadow-xs"
                            : "hover:bg-surface-2/60"
                        } group`}
                      >
                        {/* ID */}
                        <td className="py-3 px-4 font-mono font-bold text-accent-text">
                          <Link
                            href={`/banker/transactions/${item.transaction_id}`}
                            className="hover:underline flex items-center gap-1.5"
                          >
                            {item.transaction_id}
                            {isNewStreamItem && (
                              <span className="px-1.5 py-0.5 rounded-full text-[9px] bg-accent text-white uppercase font-sans animate-bounce font-bold tracking-wider">
                                LIVE
                              </span>
                            )}
                          </Link>
                        </td>

                      {/* Timestamp & Rail */}
                      <td className="py-3 px-4 text-ink-2 whitespace-nowrap">
                        <div>{new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</div>
                        <div className="text-[10px] font-mono text-ink-4">{item.transaction_type}</div>
                      </td>

                      {/* Account */}
                      <td className="py-3 px-4 font-mono text-ink">
                        {item.account_id}
                      </td>

                      {/* Beneficiary */}
                      <td className="py-3 px-4 font-mono text-ink-2">
                        {item.beneficiary_id}
                      </td>

                      {/* Amount */}
                      <td className="py-3 px-4 font-mono font-bold text-right text-ink">
                        ₹{item.amount.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                      </td>

                      {/* Risk */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getBandBadge(item.risk_band)}
                          <span className="font-mono text-ink-3 font-semibold text-[11px]">
                            {(item.risk_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>

                      {/* Action Decision */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        {getDecisionBadge(item.decision)}
                      </td>

                      {/* Reason */}
                      <td className="py-3 px-4 font-mono text-[11px] text-ink-3">
                        {item.top_reason_code ? (
                          <span className="px-1.5 py-0.5 rounded bg-surface-3/50 text-ink-2 border border-line/10">
                            {item.top_reason_code}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>

                      {/* Cockpit Link */}
                      <td className="py-3 px-4 text-center">
                        <Link
                          href={`/banker/transactions/${item.transaction_id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-semibold bg-surface-3 hover:bg-accent hover:text-white transition-colors text-ink-2 border border-line/15"
                        >
                          <span>Cockpit</span>
                          <ArrowUpRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
              </tbody>
            </table>
          </div>
        </Card>
      </Rise>

      {/* In-Line Hook & Bulk Statement Ingestion Modal */}
      <IngestTransactionModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        defaultTab={modalTab}
        onSuccess={fetchData}
      />
    </div>
  );
}
