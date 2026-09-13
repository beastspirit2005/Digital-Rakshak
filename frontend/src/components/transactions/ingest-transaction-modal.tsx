"use client";

import { useState, useRef } from "react";
import Link from "next/link";
import axios from "axios";
import { api } from "@/lib/api";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import {
  CreditCard,
  UploadCloud,
  FileSpreadsheet,
  Code2,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ShieldAlert,
  ShieldCheck,
  ArrowRight,
  Download,
  RefreshCw,
  Copy,
  Check,
  ExternalLink,
  Zap,
  Building2,
  Smartphone,
  MapPin,
  Sliders,
  CheckCircle,
  Clock,
  Fingerprint
} from "lucide-react";

interface IngestTransactionModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
  defaultTab?: "manual" | "csv" | "webhook";
}

export function IngestTransactionModal({
  open,
  onClose,
  onSuccess,
  defaultTab = "manual"
}: IngestTransactionModalProps) {
  const pushToast = useToast();
  const [activeTab, setActiveTab] = useState<"manual" | "csv" | "webhook">(defaultTab);

  // --------------------------------------------------------------------------
  // Tab 1: Manual In-Line Transaction Form
  // --------------------------------------------------------------------------
  const [accountId, setAccountId] = useState("ACC-" + Math.floor(1000000 + Math.random() * 9000000));
  const [beneficiaryId, setBeneficiaryId] = useState("merchant_payee@okaxis");
  const [amount, setAmount] = useState("450.00");
  const [channel, setChannel] = useState("UPI");
  const [transactionType, setTransactionType] = useState("TRANSFER");
  const [city, setCity] = useState("Bengaluru");
  const [stateVal, setStateVal] = useState("Karnataka");
  const [deviceId, setDeviceId] = useState("DEV-ANDR-" + Math.floor(1000 + Math.random() * 9000));

  // Simulation / Threat flags
  const [isEmulator, setIsEmulator] = useState(false);
  const [isFlaggedMule, setIsFlaggedMule] = useState(false);
  const [isOffHours, setIsOffHours] = useState(false);

  // Execution state
  const [evaluating, setEvaluating] = useState(false);
  const [decisionResult, setDecisionResult] = useState<any | null>(null);

  // Quick Presets
  const applyPreset = (type: "normal" | "step_up" | "hold" | "quarantine") => {
    setDecisionResult(null);
    if (type === "normal") {
      setAccountId("ACC-SALARY-" + Math.floor(1000 + Math.random() * 9000));
      setBeneficiaryId("local_kirana_store@upi");
      setAmount("250.00");
      setChannel("UPI");
      setCity("Bengaluru");
      setStateVal("Karnataka");
      setDeviceId("DEV-SAMSUNG-" + Math.floor(1000 + Math.random() * 9000));
      setIsEmulator(false);
      setIsFlaggedMule(false);
      setIsOffHours(false);
    } else if (type === "step_up") {
      setAccountId("ACC-SAVINGS-" + Math.floor(1000 + Math.random() * 9000));
      setBeneficiaryId("electronics_mart@ybl");
      setAmount("19500.00");
      setChannel("UPI");
      setCity("Hyderabad");
      setStateVal("Telangana");
      setDeviceId("DEV-NEW-DEVICE-" + Math.floor(1000 + Math.random() * 9000));
      setIsEmulator(false);
      setIsFlaggedMule(false);
      setIsOffHours(false);
    } else if (type === "hold") {
      setAccountId("ACC-CHECKING-" + Math.floor(1000 + Math.random() * 9000));
      setBeneficiaryId("instant_cashback_promo@ibl");
      setAmount("48000.00");
      setChannel("IMPS");
      setCity("Jamtara");
      setStateVal("Jharkhand");
      setDeviceId("DEV-TEMP-PHONE-" + Math.floor(1000 + Math.random() * 9000));
      setIsEmulator(true);
      setIsFlaggedMule(false);
      setIsOffHours(true);
    } else if (type === "quarantine") {
      setAccountId("ACC-CORP-DRAIN-" + Math.floor(1000 + Math.random() * 9000));
      setBeneficiaryId("crypto_mule_laundering_pool@ybl");
      setAmount("198000.00");
      setChannel("UPI");
      setCity("Mewat");
      setStateVal("Haryana");
      setDeviceId("DEV-EMU-ROOT-991");
      setIsEmulator(true);
      setIsFlaggedMule(true);
      setIsOffHours(true);
    }
  };

  const handleAuthorize = async (e: React.FormEvent) => {
    e.preventDefault();
    setEvaluating(true);
    setDecisionResult(null);

    try {
      const now = new Date();
      if (isOffHours) {
        now.setHours(3, 15, 0, 0); // 3:15 AM
      }

      const rawMetadata: any = {};
      if (isEmulator) {
        rawMetadata.device_profile = {
          is_emulator: true,
          risk_score: 0.94,
          associated_accounts: ["ACC-VICTIM-1", "ACC-VICTIM-2"]
        };
      }
      if (isFlaggedMule) {
        rawMetadata.beneficiary_profile = {
          is_flagged: true,
          risk_score: 0.98
        };
        rawMetadata.graph_risk = 0.91;
      }

      const payload = {
        account_id: accountId.trim(),
        beneficiary_id: beneficiaryId.trim(),
        amount: parseFloat(amount) || 100.0,
        currency: "INR",
        channel: channel,
        transaction_type: transactionType,
        city: city.trim(),
        state: stateVal.trim(),
        device_id: deviceId.trim() || undefined,
        timestamp: now.toISOString(),
        raw_metadata: Object.keys(rawMetadata).length ? rawMetadata : undefined
      };

      const res = await axios.post(api("/transactions/switch/authorize"), payload);
      setDecisionResult(res.data);
      pushToast("info", `Evaluated: Action Code ${res.data.action_code} - ${res.data.action_status}`);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error("Authorization hook failed:", err);
      pushToast("danger", err.response?.data?.detail || "Failed to execute bank switch authorization");
    } finally {
      setEvaluating(false);
    }
  };

  // --------------------------------------------------------------------------
  // Tab 2: Bulk Statement CSV Upload
  // --------------------------------------------------------------------------
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingCsv, setUploadingCsv] = useState(false);
  const [csvSummary, setCsvSummary] = useState<any | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.endsWith(".csv")) {
        pushToast("danger", "Please select a valid .csv file");
        return;
      }
      setSelectedFile(file);
      setCsvSummary(null);
    }
  };

  const handleUploadCsv = async () => {
    if (!selectedFile) return;
    setUploadingCsv(true);
    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const res = await axios.post(api("/transactions/upload-csv"), formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      setCsvSummary(res.data);
      pushToast("success", `Bulk statement processed: ${res.data.total_processed} transactions evaluated.`);
      if (onSuccess) onSuccess();
    } catch (err: any) {
      console.error("CSV upload failed:", err);
      pushToast("danger", err.response?.data?.detail || "CSV bulk ingestion failed");
    } finally {
      setUploadingCsv(false);
    }
  };

  const handleDownloadSampleCsv = () => {
    window.open(api("/transactions/sample-csv"), "_blank");
  };

  // --------------------------------------------------------------------------
  // Tab 3: Switch Webhook / Code Snippets
  // --------------------------------------------------------------------------
  const [copied, setCopied] = useState(false);
  const curlCode = `curl -X POST "${typeof window !== "undefined" ? window.location.origin : "https://rakshak-backend.vercel.app"}/api/v1/transactions/switch/authorize" \\
  -H "Content-Type: application/json" \\
  -d '{
    "account_id": "ACC-7819230",
    "beneficiary_id": "payee_merchant@upi",
    "amount": 14500.00,
    "currency": "INR",
    "channel": "UPI",
    "city": "Bengaluru",
    "state": "Karnataka",
    "device_id": "DEV-ANDR-8821"
  }'`;

  const copySnippet = () => {
    navigator.clipboard.writeText(curlCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    pushToast("success", "cURL integration snippet copied to clipboard.");
  };

  const getActionBadge = (code: string, statusText: string) => {
    switch (code) {
      case "00":
        return (
          <Badge tone="success" className="font-mono font-bold text-xs py-1 px-2.5">
            00 • {statusText}
          </Badge>
        );
      case "75":
        return (
          <Badge tone="warning" className="font-mono font-bold text-xs py-1 px-2.5">
            75 • {statusText}
          </Badge>
        );
      case "05":
        return (
          <Badge tone="peach" className="font-mono font-bold text-xs py-1 px-2.5">
            05 • {statusText}
          </Badge>
        );
      default:
        return (
          <Badge tone="danger" className="font-mono font-bold text-xs py-1 px-2.5 animate-pulse">
            43 • {statusText}
          </Badge>
        );
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-accent/15 text-accent">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-base text-ink">Bank & Switch In-Line Hook</h2>
            <p className="text-xs text-ink-3 font-normal">
              Direct Core Banking System & UPI Switch Pre-Debit Fraud Defense
            </p>
          </div>
        </div>
      }
      className="sm:max-w-3xl"
    >
      {/* Tab Switcher */}
      <div className="flex items-center border-b border-line/15 mt-2 mb-5">
        <button
          onClick={() => setActiveTab("manual")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "manual"
              ? "border-accent text-accent"
              : "border-transparent text-ink-3 hover:text-ink"
          }`}
        >
          <CreditCard className="w-4 h-4" />
          Real Transaction Entry
        </button>
        <button
          onClick={() => setActiveTab("csv")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "csv"
              ? "border-accent text-accent"
              : "border-transparent text-ink-3 hover:text-ink"
          }`}
        >
          <UploadCloud className="w-4 h-4" />
          Bulk Statement CSV
        </button>
        <button
          onClick={() => setActiveTab("webhook")}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === "webhook"
              ? "border-accent text-accent"
              : "border-transparent text-ink-3 hover:text-ink"
          }`}
        >
          <Code2 className="w-4 h-4" />
          Switch API Hook Guide
        </button>
      </div>

      {/* TAB 1: REAL TRANSACTION MANUAL INGESTION */}
      {activeTab === "manual" && (
        <div className="space-y-4">
          {/* Quick Presets */}
          <div className="bg-surface-2 p-3 rounded-control border border-line/15">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-ink-3 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-accent" />
                Quick Scenario Presets:
              </span>
              <span className="text-[10px] text-ink-4">Click to auto-populate</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => applyPreset("normal")}
                className="px-2.5 py-1 text-[11px] rounded-pill bg-surface-1 border border-line/20 hover:border-success/40 text-ink hover:text-success transition-all"
              >
                ✅ Kirana UPI (₹250 - Pass)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("step_up")}
                className="px-2.5 py-1 text-[11px] rounded-pill bg-surface-1 border border-line/20 hover:border-warning/40 text-ink hover:text-warning transition-all"
              >
                ⚠️ New Device Spike (₹19.5k - Step-Up)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("hold")}
                className="px-2.5 py-1 text-[11px] rounded-pill bg-surface-1 border border-line/20 hover:border-peach/40 text-ink hover:text-peach transition-all"
              >
                🛑 Off-Hours Hopping (₹48k - Hold)
              </button>
              <button
                type="button"
                onClick={() => applyPreset("quarantine")}
                className="px-2.5 py-1 text-[11px] rounded-pill bg-surface-1 border border-line/20 hover:border-danger/40 text-ink hover:text-danger transition-all"
              >
                🚨 Syndicate Mule Drain (₹198k - Quarantine)
              </button>
            </div>
          </div>

          <form onSubmit={handleAuthorize} className="space-y-3.5">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">
                  Remitter Account / Card ID <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={accountId}
                  onChange={(e) => setAccountId(e.target.value)}
                  placeholder="e.g. ACC-4910284"
                  className="w-full text-xs font-mono px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">
                  Beneficiary VPA / Account <span className="text-danger">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={beneficiaryId}
                  onChange={(e) => setBeneficiaryId(e.target.value)}
                  placeholder="e.g. merchant@okaxis"
                  className="w-full text-xs font-mono px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">
                  Amount (₹ INR) <span className="text-danger">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2 text-xs font-bold text-ink-3">₹</span>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    className="w-full text-xs font-mono pl-7 pr-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">Channel</label>
                <select
                  value={channel}
                  onChange={(e) => setChannel(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                >
                  <option value="UPI">UPI (NPCI)</option>
                  <option value="IMPS">IMPS (Instant)</option>
                  <option value="NEFT">NEFT</option>
                  <option value="RTGS">RTGS</option>
                  <option value="CARD">Debit / Credit Card</option>
                  <option value="NETBANKING">NetBanking</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">Transaction Type</label>
                <select
                  value={transactionType}
                  onChange={(e) => setTransactionType(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                >
                  <option value="TRANSFER">P2P / P2M Transfer</option>
                  <option value="PAYMENT">Merchant Checkout</option>
                  <option value="WITHDRAWAL">ATM / Cash Out</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">City</label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">State</label>
                <input
                  type="text"
                  value={stateVal}
                  onChange={(e) => setStateVal(e.target.value)}
                  className="w-full text-xs px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-ink-2 block mb-1">Device Telemetry ID</label>
                <input
                  type="text"
                  value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                  placeholder="e.g. DEV-PIXEL-7"
                  className="w-full text-xs font-mono px-3 py-2 rounded-control bg-surface-2 border border-line/25 text-ink focus:border-accent outline-none"
                />
              </div>
            </div>

            {/* Simulated Telemetry Options */}
            <div className="pt-2 border-t border-line/10 flex flex-wrap items-center gap-4 text-xs text-ink-3">
              <span className="font-semibold text-ink-2 text-[11px]">Threat Telemetry:</span>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isEmulator}
                  onChange={(e) => setIsEmulator(e.target.checked)}
                  className="rounded text-accent focus:ring-0"
                />
                <span>Rooted / Emulator Device</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isFlaggedMule}
                  onChange={(e) => setIsFlaggedMule(e.target.checked)}
                  className="rounded text-accent focus:ring-0"
                />
                <span>Known Mule Beneficiary</span>
              </label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isOffHours}
                  onChange={(e) => setIsOffHours(e.target.checked)}
                  className="rounded text-accent focus:ring-0"
                />
                <span>Off-Hours (3:15 AM)</span>
              </label>
            </div>

            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                disabled={evaluating}
                className="w-full py-2.5 text-xs font-bold gap-2 justify-center shadow-md"
              >
                {evaluating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Executing In-Line Switch Authorization (&lt;50ms)...
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4 text-amber-300" />
                    Authorize & Evaluate Transaction
                  </>
                )}
              </Button>
            </div>
          </form>

          {/* Real-Time Decision Card Result */}
          {decisionResult && (
            <Card className="p-4 bg-surface-2 border-line/30 space-y-3 mt-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-ink-3">SWITCH ACTION:</span>
                  {getActionBadge(decisionResult.action_code, decisionResult.action_status)}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-ink-4">Risk Score:</span>
                  <span className="font-mono font-bold text-ink">
                    {Math.round(decisionResult.risk_score * 100)}%
                  </span>
                  <Badge tone={decisionResult.risk_band === "CRITICAL" ? "danger" : "warning"} className="text-[10px]">
                    {decisionResult.risk_band}
                  </Badge>
                </div>
              </div>

              <div className="p-3 rounded-control bg-surface-1 border border-line/15 text-xs space-y-1">
                <div className="flex items-center justify-between text-[11px] text-ink-3">
                  <span className="font-mono font-bold text-ink">
                    Txn ID: {decisionResult.transaction_id}
                  </span>
                  <span className="text-success font-semibold">Latency: ~28ms</span>
                </div>
                <p className="text-ink font-medium mt-1">{decisionResult.action_message}</p>
                <p className="text-ink-3 text-[11px] italic">{decisionResult.explanation}</p>
              </div>

              {decisionResult.reason_codes && decisionResult.reason_codes.length > 0 && (
                <div className="flex flex-wrap gap-1 items-center">
                  <span className="text-[10px] text-ink-4 mr-1">Triggers:</span>
                  {decisionResult.reason_codes.map((rc: string) => (
                    <span key={rc} className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-1 border border-line/20 text-ink-2">
                      {rc}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between pt-1">
                <Link
                  href={`/banker/transactions/${decisionResult.id || decisionResult.transaction_id}`}
                  className="text-xs text-accent hover:underline flex items-center gap-1 font-semibold"
                  onClick={onClose}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  Inspect in Forensic Cockpit
                </Link>
                <Button variant="secondary" size="sm" onClick={() => setDecisionResult(null)} className="text-xs">
                  Clear
                </Button>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* TAB 2: BULK STATEMENT CSV UPLOAD */}
      {activeTab === "csv" && (
        <div className="space-y-4">
          <div className="p-3.5 rounded-control bg-surface-2 border border-line/15 flex items-center justify-between">
            <div>
              <h4 className="text-xs font-bold text-ink">CSV Statement Format</h4>
              <p className="text-[11px] text-ink-3">
                Headers: account_id, beneficiary_id, amount, channel, transaction_type, city, state, device_id
              </p>
            </div>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownloadSampleCsv}
              className="gap-1.5 text-xs shrink-0"
            >
              <Download className="w-3.5 h-3.5" />
              Download Template
            </Button>
          </div>

          {/* Drag and Drop Zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-line/30 hover:border-accent/50 rounded-card p-6 flex flex-col items-center justify-center gap-2.5 cursor-pointer bg-surface-2/40 hover:bg-surface-2 transition-all text-center"
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".csv"
              className="hidden"
            />
            <div className="p-3 rounded-full bg-surface-1 border border-line/20 text-accent">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <p className="text-xs font-semibold text-ink">
                {selectedFile ? selectedFile.name : "Click to select or drop your transaction statement (.csv)"}
              </p>
              <p className="text-[11px] text-ink-4 mt-0.5">
                {selectedFile
                  ? `${(selectedFile.size / 1024).toFixed(1)} KB ready for ingestion`
                  : "Supports standard core banking transaction export formats"}
              </p>
            </div>
          </div>

          {selectedFile && (
            <div className="flex justify-end gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setSelectedFile(null);
                  setCsvSummary(null);
                }}
                disabled={uploadingCsv}
                className="text-xs"
              >
                Remove
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleUploadCsv}
                disabled={uploadingCsv}
                className="gap-1.5 text-xs font-semibold"
              >
                {uploadingCsv ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Ingesting & Evaluating Batch...
                  </>
                ) : (
                  <>
                    <UploadCloud className="w-3.5 h-3.5" />
                    Upload & Ingest Statement
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Bulk Ingestion Results Summary */}
          {csvSummary && (
            <Card className="p-4 bg-surface-2 border-success/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-success" />
                  <span className="text-xs font-bold text-ink">Statement Ingestion Complete</span>
                </div>
                <span className="text-[11px] font-mono text-ink-3">
                  {csvSummary.filename}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                <div className="p-2.5 rounded-control bg-surface-1 border border-line/15">
                  <span className="text-[10px] text-ink-4 block">Evaluated</span>
                  <span className="text-sm font-bold text-ink">{csvSummary.total_processed} Txns</span>
                </div>
                <div className="p-2.5 rounded-control bg-surface-1 border border-line/15">
                  <span className="text-[10px] text-ink-4 block">Pass-Through (00)</span>
                  <span className="text-sm font-bold text-success">{csvSummary.approved_count}</span>
                </div>
                <div className="p-2.5 rounded-control bg-surface-1 border border-line/15">
                  <span className="text-[10px] text-ink-4 block">Step-Up (75)</span>
                  <span className="text-sm font-bold text-warning">{csvSummary.flagged_count}</span>
                </div>
                <div className="p-2.5 rounded-control bg-surface-1 border border-line/15">
                  <span className="text-[10px] text-ink-4 block">Quarantined (43/05)</span>
                  <span className="text-sm font-bold text-danger">{csvSummary.quarantined_count}</span>
                </div>
              </div>

              <div className="p-2.5 rounded-control bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between text-xs">
                <span className="font-semibold text-emerald-400">Prevented Fraud Loss:</span>
                <span className="font-mono font-bold text-emerald-300 text-sm">
                  ₹{Number(csvSummary.prevented_loss_amount).toLocaleString("en-IN")}
                </span>
              </div>

              {/* Sample Table */}
              {csvSummary.processed_sample && csvSummary.processed_sample.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[11px] font-bold text-ink-3 block">Evaluated Rows Preview:</span>
                  <div className="max-h-36 overflow-y-auto rounded border border-line/15">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-surface-1 text-ink-3 sticky top-0 font-mono text-[10px]">
                        <tr>
                          <th className="p-1.5">TXN ID</th>
                          <th className="p-1.5">Account</th>
                          <th className="p-1.5">Amount</th>
                          <th className="p-1.5">Action Code</th>
                          <th className="p-1.5">Decision</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-line/10 font-mono">
                        {csvSummary.processed_sample.map((s: any) => (
                          <tr key={s.transaction_id} className="hover:bg-surface-1/50">
                            <td className="p-1.5 text-ink font-semibold">{s.transaction_id}</td>
                            <td className="p-1.5 text-ink-3">{s.account_id}</td>
                            <td className="p-1.5 text-ink">₹{s.amount}</td>
                            <td className="p-1.5 font-bold">
                              <span className={s.action_code === "00" ? "text-success" : s.action_code === "75" ? "text-warning" : "text-danger"}>
                                {s.action_code}
                              </span>
                            </td>
                            <td className="p-1.5 text-ink-2">{s.decision}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* TAB 3: API & BANK SWITCH INTEGRATION GUIDE */}
      {activeTab === "webhook" && (
        <div className="space-y-4 text-xs">
          <div className="p-3.5 rounded-control bg-surface-2 border border-line/15 space-y-2">
            <h4 className="font-bold text-ink text-sm flex items-center gap-2">
              <Building2 className="w-4 h-4 text-accent" />
              NPCI & Bank Switch Integration Architecture
            </h4>
            <p className="text-ink-3 leading-relaxed text-[11px]">
              Digital Rakshak sits between customer payment apps (PhonePe, Google Pay, Paytm) and the Bank Core Banking System (CBS). During the pre-debit authorization lifecycle, the switch dispatches an HTTP POST hook before committing ledger balance.
            </p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] font-bold text-ink-2">
                Pre-Debit Switch Hook Endpoint
              </span>
              <button
                onClick={copySnippet}
                className="flex items-center gap-1 text-[11px] text-accent hover:underline font-mono"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? "Copied" : "Copy cURL"}
              </button>
            </div>
            <pre className="p-3 rounded-control bg-ink/90 text-emerald-300 font-mono text-[11px] overflow-x-auto border border-line/20">
              {curlCode}
            </pre>
          </div>

          <div className="space-y-1.5">
            <span className="font-bold text-ink text-xs block">ISO 8583 / NPCI Banking Action Codes:</span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 font-mono text-[11px]">
              <div className="p-2 rounded bg-surface-2 border border-line/15">
                <span className="font-bold text-success">00 - APPROVED</span>
                <p className="text-[10px] text-ink-3 font-sans mt-0.5">Instant debit clearance without friction.</p>
              </div>
              <div className="p-2 rounded bg-surface-2 border border-line/15">
                <span className="font-bold text-warning">75 - STEP_UP_REQUIRED</span>
                <p className="text-[10px] text-ink-3 font-sans mt-0.5">Trigger biometric/OTP challenge on mobile device.</p>
              </div>
              <div className="p-2 rounded bg-surface-2 border border-line/15">
                <span className="font-bold text-peach">05 - TEMPORARY_HOLD</span>
                <p className="text-[10px] text-ink-3 font-sans mt-0.5">Do Not Honor; 15-minute escrow hold for velocity throttling.</p>
              </div>
              <div className="p-2 rounded bg-surface-2 border border-line/15">
                <span className="font-bold text-danger">43 - DECLINED_FRAUD_HOLD</span>
                <p className="text-[10px] text-ink-3 font-sans mt-0.5">Quarantine immediate debit & trigger LEA case creation.</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}
