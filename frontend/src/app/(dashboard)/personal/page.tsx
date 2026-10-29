"use client";

import { useState, useEffect } from "react";
import axios from "axios";
import { 
  ShieldCheck, 
  AlertTriangle, 
  ShieldAlert, 
  Link as LinkIcon, 
  QrCode, 
  Smartphone, 
  HandCoins, 
  FileText, 
  CheckCircle2, 
  Lock, 
  Sparkles, 
  Zap, 
  ChevronRight, 
  History, 
  Copy, 
  ExternalLink,
  Users,
  Trash2,
  Info,
  Loader2,
  Mail, Check, X } from "lucide-react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";
import { LoadingOverlay } from "@/components/ui/loading-overlay";

interface ScanRecord {
  id: string;
  type: string;
  input: string;
  is_safe: boolean;
  risk_level: string;
  reasons: string[];
  indicator_status?: "KNOWN_MALICIOUS" | "SUSPICIOUS" | "UNKNOWN_UNVERIFIED" | "VERIFIED_LEGITIMATE" | string;
  guidance?: string[];
  attack_dna_match?: string;
  related_cases?: number;
  timestamp: string;
}

declare global {
  interface Window {
    Razorpay: any;
  }
}

export default function PersonalProtectionPortal() {
  const { user, token, isAuthenticated, updateUser } = useAuthStore();
  const pushToast = useToast();

  const [activeTab, setActiveTab] = useState<"url" | "text" | "upi" | "phone" | "qr">("url");
  const [inputValue, setInputValue] = useState("");
  const [qrFile, setQrFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearingHistory, setClearingHistory] = useState(false);
  const [currentResult, setCurrentResult] = useState<ScanRecord | null>(null);
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);

  // Upgrade Modal State
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<"b2c_pro_149" | "b2c_pro_249" | "b2c_pro_annual">("b2c_pro_149");
  const [upgrading, setUpgrading] = useState(false);
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [downloadingInvoice, setDownloadingInvoice] = useState(false);
  const [resendingInvoice, setResendingInvoice] = useState(false);
  const [activatingPro, setActivatingPro] = useState(false);
  const [showInvoiceEmailModal, setShowInvoiceEmailModal] = useState(false);
  const [invoiceTargetEmail, setInvoiceTargetEmail] = useState("");
  const [cancelNotificationEmail, setCancelNotificationEmail] = useState("");

  // Institutional law enforcement & nodal officer roles have complimentary full-tier access
  const isOfficialRole = ["admin", "police", "cyber_cell", "banker", "bank_employee"].includes(user?.role || "");
  const isPro = isOfficialRole || Boolean(user?.b2c_plan_code && user?.b2c_plan_code !== "b2c_free" && user?.b2c_subscription_status === "active");

  const ensureRazorpayLoaded = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (typeof window === "undefined") return resolve(false);
      if (window.Razorpay) return resolve(true);
      const existing = document.getElementById("razorpay-checkout-script");
      if (existing) {
        existing.addEventListener("load", () => resolve(true));
        return;
      }
      const script = document.createElement("script");
      script.id = "razorpay-checkout-script";
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      script.async = true;
      script.onload = () => resolve(true);
      script.onerror = () => resolve(false);
      document.body.appendChild(script);
    });
  };

  useEffect(() => {
    // 1. Check if returning from Razorpay external redirect (e.g. UPI Intent / Netbanking)
    if (typeof window !== "undefined" && window.location.search) {
      const params = new URLSearchParams(window.location.search);
      const razorpayPaymentId = params.get("razorpay_payment_id");
      const razorpaySubscriptionId = params.get("razorpay_subscription_id");
      const razorpaySignature = params.get("razorpay_signature");

      if (razorpayPaymentId && token) {
        setActivatingPro(true);
        axios
          .post(
            api("/billing/verify-payment"),
            {
              razorpay_payment_id: razorpayPaymentId,
              razorpay_subscription_id: razorpaySubscriptionId || "",
              razorpay_signature: razorpaySignature || "",
              plan_code: selectedPlan,
            },
            { headers: { Authorization: `Bearer ${token}` } }
          )
          .then(() => {
            updateUser({
              b2c_plan_code: selectedPlan,
              b2c_subscription_status: "active",
              is_pro: true,
            });
            pushToast("success", "Welcome to Digital Rakshak Pro! Zero-Day AI Defense is now active.");
          })
          .catch((err) => {
            console.error("Redirect payment verification error:", err);
          })
          .finally(() => {
            window.history.replaceState({}, document.title, window.location.pathname);
            setTimeout(() => setActivatingPro(false), 1200);
          });
      }
    }

    // 2. Sync profile from backend on mount if token is present
    if (token) {
      axios
        .get(api("/users/me"), { headers: { Authorization: `Bearer ${token}` } })
        .then((res) => {
          if (res.data) {
            updateUser({
              b2c_plan_code: res.data.b2c_plan_code,
              b2c_subscription_status: res.data.b2c_subscription_status,
              is_pro: res.data.is_pro,
            });
          }
        })
        .catch(() => {});
    }

    // 3. Load user-specific scan history from backend if logged in, fallback to local storage
    const loadScanHistory = async () => {
      if (token) {
        try {
          const res = await axios.get(api("/scan/history"), {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (Array.isArray(res.data) && res.data.length > 0) {
            setScanHistory(res.data);
            return;
          }
        } catch (e) {
          // fallback to localStorage
        }
      }
      const saved = localStorage.getItem("dr_personal_scan_history");
      if (saved) {
        try {
          setScanHistory(JSON.parse(saved).slice(0, 10));
        } catch (e) {
          // ignore json parse error
        }
      }
    };
    loadScanHistory();
  }, [token]);

  const handleScan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue && !qrFile) return;

    setLoading(true);
    setCurrentResult(null);

    try {
      let res;
      if (activeTab === "qr" && qrFile) {
        const formData = new FormData();
        formData.append("file", qrFile);
        res = await axios.post(api("/scan/qr"), formData, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
      } else {
        const payload: any = {};
        if (activeTab === "url") payload.url = inputValue;
        else if (activeTab === "upi") payload.upi = inputValue;
        else if (activeTab === "phone") payload.phone = inputValue;
        else payload.text = inputValue;

        res = await axios.post(api("/scan"), payload, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
      }

      const record: ScanRecord = {
        id: Math.random().toString(36).substring(7),
        type: activeTab.toUpperCase(),
        input: inputValue || qrFile?.name || "QR Code Image",
        is_safe: res.data.is_safe,
        risk_level: res.data.risk_level,
        reasons: res.data.reasons || [],
        indicator_status: res.data.indicator_status || (res.data.is_safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS"),
        guidance: res.data.guidance || [],
        attack_dna_match: res.data.attack_dna_match,
        related_cases: res.data.related_cases,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setCurrentResult(record);

      const updated = [record, ...scanHistory.slice(0, 9)];
      setScanHistory(updated);
      localStorage.setItem("dr_personal_scan_history", JSON.stringify(updated));

      pushToast(
        record.is_safe ? "success" : "danger",
        record.reasons[0] || (record.is_safe ? "No malicious indicators found." : "Suspicious activity flagged.")
      );

    } catch (err: any) {
      const msg = err.response?.data?.detail || "Scan request could not be completed.";
      pushToast("danger", msg);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (scanHistory.length === 0) return;
    setClearingHistory(true);
    try {
      if (token) {
        await axios.delete(api("/scan/history"), {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
      setScanHistory([]);
      localStorage.removeItem("dr_personal_scan_history");
      pushToast("success", "Personal scan history has been cleared.");
    } catch (err: any) {
      pushToast("danger", "Could not clear scan history.");
    } finally {
      setClearingHistory(false);
    }
  };

  const handleCancelSubscription = async () => {
    setCancelling(true);
    try {
      const targetEmail = cancelNotificationEmail.trim() || user?.email || "";
      const res = await axios.post(
        api("/billing/cancel-subscription"),
        { notification_email: targetEmail },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      updateUser({
        b2c_plan_code: "b2c_free",
        b2c_subscription_status: "canceled",
        is_pro: false,
      });
      setShowCancelModal(false);
      const refundAmt = res.data?.refund_details?.refund_amount;
      const refundMsg = refundAmt !== undefined ? ` ₹${refundAmt.toFixed(2)} base refund initiated to your payment source.` : "";
      const recMsg = res.data?.recipients ? ` Confirmation delivered to ${res.data.recipients.join(", ")}.` : " Confirmation email dispatched.";
      pushToast("success", `Subscription canceled.${refundMsg}${recMsg}`);
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Could not cancel subscription. Please try again.");
    } finally {
      setCancelling(false);
    }
  };

  const handleDownloadInvoice = () => {
    if (!token) {
      pushToast("warning", "Please sign in to download your GST tax invoice.");
      return;
    }
    setDownloadingInvoice(true);
    try {
      const invoiceUrl = api(`/billing/invoice/latest/pdf?token=${encodeURIComponent(token)}`);
      window.open(invoiceUrl, "_blank");
      pushToast("success", "Downloading official GST Tax Invoice PDF...");
    } catch (err: any) {
      pushToast("danger", "Could not download tax invoice. Try again.");
    } finally {
      setTimeout(() => setDownloadingInvoice(false), 800);
    }
  };

  const handleSendInvoiceEmail = async () => {
    if (!token) {
      pushToast("warning", "Please sign in to email your invoice.");
      return;
    }
    const target = invoiceTargetEmail.trim() || user?.email || "";
    setResendingInvoice(true);
    try {
      const res = await axios.post(
        api("/billing/invoice/resend"),
        { target_email: target },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setShowInvoiceEmailModal(false);
      pushToast("success", res.data?.message || `Tax invoice PDF sent to ${target}!`);
    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Could not email invoice. Please try again.");
    } finally {
      setResendingInvoice(false);
    }
  };

  const handleInitiateRazorpayUpgrade = async () => {
    if (!isAuthenticated) {
      pushToast("warning", "Please sign in or create a free account to activate Digital Rakshak Pro.");
      return;
    }

    setUpgrading(true);
    try {
      await ensureRazorpayLoaded();
      // 1. Call backend to create Razorpay subscription
      const subRes = await axios.post(
        api("/billing/create-subscription"),
        { plan_code: selectedPlan },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const { subscription_id, order_id, razorpay_key_id, amount_paise } = subRes.data;

      // Sandbox developer mode fallback when no real Razorpay credentials are configured
      if (!window.Razorpay || !razorpay_key_id || razorpay_key_id.startsWith("rzp_test_placeholder")) {
        setActivatingPro(true);
        setShowUpgradeModal(false);
        try {
          await axios.post(
            api("/billing/verify-payment"),
            {
              razorpay_payment_id: "pay_sandbox_" + Math.random().toString(36).substring(7),
              razorpay_subscription_id: subscription_id,
              razorpay_order_id: order_id,
              razorpay_signature: "sandbox_valid_sig",
              plan_code: selectedPlan
            },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          updateUser({
            b2c_plan_code: selectedPlan,
            b2c_subscription_status: "active",
            is_pro: true,
          });
          pushToast("success", "Welcome to Digital Rakshak Pro! Zero-day AI and Attack DNA are now active.");
        } finally {
          setTimeout(() => setActivatingPro(false), 1200);
        }
        return;
      }

      // 2. Open Real Razorpay Checkout Modal
      const planDescription = 
        selectedPlan === "b2c_pro_annual"
          ? "Digital Rakshak Pro Annual (₹1,299/yr + 18% GST)"
          : selectedPlan === "b2c_pro_249"
          ? "Digital Rakshak Family Shield (₹249/mo + 18% GST)"
          : "Digital Rakshak Personal Pro (₹149/mo + 18% GST)";

      const defaultPaise = 
        selectedPlan === "b2c_pro_annual"
          ? 153282
          : selectedPlan === "b2c_pro_249"
          ? 29382
          : 17582;

      const options: any = {
        key: razorpay_key_id,
        name: "Digital Rakshak",
        description: planDescription,
        amount: amount_paise || defaultPaise,
        currency: "INR",
        handler: async function (response: any) {
          setShowUpgradeModal(false);
          setActivatingPro(true);
          try {
            // 3. Verify payment signature on backend
            await axios.post(
              api("/billing/verify-payment"),
              {
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_subscription_id: response.razorpay_subscription_id || subscription_id,
                razorpay_order_id: response.razorpay_order_id || order_id,
                razorpay_signature: response.razorpay_signature,
                plan_code: selectedPlan
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );

            updateUser({
              b2c_plan_code: selectedPlan,
              b2c_subscription_status: "active",
              is_pro: true,
            });
            pushToast("success", "Welcome to Digital Rakshak Pro! Zero-day AI and Attack DNA are now active.");
          } catch (verErr: any) {
            pushToast("danger", "Payment verification failed. Please contact support.");
          } finally {
            setTimeout(() => setActivatingPro(false), 1200);
          }
        },
        prefill: {
          name: user?.full_name || "Citizen User",
          email: user?.email || "",
          contact: (user as any)?.phone || user?.station_phone_number || "9876543210"
        },
        theme: {
          color: "#0284c7"
        }
      };

      if (subscription_id) {
        options.subscription_id = subscription_id;
      } else if (order_id) {
        options.order_id = order_id;
      }

      const rzp = new window.Razorpay(options);
      rzp.on("payment.failed", function (response: any) {
        pushToast("warning", response.error?.description || "Subscription setup was canceled.");
      });
      rzp.open();

    } catch (err: any) {
      pushToast("danger", err.response?.data?.detail || "Could not initialize checkout. Try again.");
    } finally {
      setUpgrading(false);
    }
  };


  return (
    <div className="max-w-6xl mx-auto space-y-8 p-4 md:p-6 pb-20">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/40 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
              Digital Rakshak Personal
            </h1>
            {isOfficialRole ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <ShieldCheck className="w-3.5 h-3.5" /> INSTITUTIONAL ACCESS ({user?.role?.toUpperCase().replace("_", " ")})
              </span>
            ) : activatingPro ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/20 animate-pulse">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> ACTIVATING PRO...
              </span>
            ) : isPro ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                <Sparkles className="w-3.5 h-3.5" /> PRO ACTIVE
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-500 border border-blue-500/20">
                FREE SHIELD
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1 text-sm md:text-base">
            Instant scam protection for links, messages, UPI IDs, and QR codes before you trust or pay.
          </p>
        </div>

        {!isPro && !isOfficialRole && !activatingPro ? (
          <Button 
            onClick={() => setShowUpgradeModal(true)}
            className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-medium shadow-md shadow-orange-500/20"
          >
            <Zap className="w-4 h-4 mr-2" /> Upgrade to Pro
          </Button>
        ) : activatingPro ? (
          <Button 
            disabled
            className="bg-amber-500/15 text-amber-500 border border-amber-500/30 cursor-wait font-medium"
          >
            <Loader2 className="w-4 h-4 mr-2 animate-spin" /> Provisioning Shield...
          </Button>
        ) : !isOfficialRole ? (
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              onClick={handleDownloadInvoice}
              disabled={downloadingInvoice}
              className="text-xs text-muted-foreground hover:text-foreground border-border/60 flex items-center gap-1.5"
              title="Download official A4 GST Tax Invoice as PDF"
            >
              <FileText className="w-3.5 h-3.5 text-sky-400" />
              {downloadingInvoice ? "Downloading..." : "PDF Invoice"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setInvoiceTargetEmail(user?.email || "");
                setShowInvoiceEmailModal(true);
              }}
              disabled={resendingInvoice}
              className="text-xs text-muted-foreground hover:text-foreground border-border/60 flex items-center gap-1.5"
              title="Resend Tax Invoice PDF to your email"
            >
              <Mail className="w-3.5 h-3.5 text-indigo-400" />
              {resendingInvoice ? "Sending..." : "Email Invoice"}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setCancelNotificationEmail(user?.email || "");
                setShowCancelModal(true);
              }}
              className="text-xs text-muted-foreground hover:text-rose-500 border-border/60 hover:border-rose-500/40"
            >
              Cancel Subscription
            </Button>
          </div>
        ) : null}
      </div>

      {/* Main Scanner Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-6">
          <Card className="relative p-6 border-border/60 shadow-sm bg-card/60 backdrop-blur-sm overflow-hidden">
            <LoadingOverlay
              open={loading}
              fullscreen={false}
              variant="cyber"
              title="Analyzing Security Threat"
              subtitle={`Scanning ${activeTab.toUpperCase()} against 1.2M+ national indicators...`}
              badge="AI Threat Core"
              steps={[
                "Deconstructing payload & extracting cryptographic indicators...",
                "Querying 1.2M+ National Threat Pattern Registry (TPR)...",
                "Running PyTorch Zero-Day AI & Heuristic Models...",
                "Correlating with active Indian cybercrime syndicates..."
              ]}
            />
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                Zero-Day Threat Scanner
              </span>
              <span className="text-xs text-muted-foreground">
                {isOfficialRole ? "Institutional Officer Shield Active" : isPro ? "Unlimited Scans Active" : "5 Free Daily Guest Scans"}
              </span>
            </div>

            {/* Input Mode Selector */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6">
              {[
                { id: "url", label: "Web Link", icon: LinkIcon },
                { id: "text", label: "Message / SMS", icon: FileText },
                { id: "upi", label: "UPI ID", icon: HandCoins },
                { id: "phone", label: "Phone Number", icon: Smartphone },
                { id: "qr", label: "QR Image", icon: QrCode }
              ].map(tab => {
                const Icon = tab.icon;
                const active = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id as any);
                      setInputValue("");
                      setQrFile(null);
                    }}
                    className={`flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-medium transition-all ${
                      active 
                        ? "bg-primary/10 border-primary text-primary shadow-sm" 
                        : "border-border/60 hover:bg-muted/40 text-muted-foreground"
                    }`}
                  >
                    <Icon className="w-5 h-5 mb-1.5" />
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* Input Form */}
            <form onSubmit={handleScan} className="space-y-4">
              {activeTab === "qr" ? (
                <div className="border-2 border-dashed border-border/80 rounded-xl p-8 text-center hover:border-primary/50 transition-colors">
                  <input
                    type="file"
                    accept="image/*"
                    id="qr-upload"
                    className="hidden"
                    onChange={(e) => setQrFile(e.target.files?.[0] || null)}
                  />
                  <label htmlFor="qr-upload" className="cursor-pointer block space-y-2">
                    <QrCode className="w-10 h-10 mx-auto text-muted-foreground" />
                    <div className="text-sm font-medium">
                      {qrFile ? qrFile.name : "Click to select or drop QR code image"}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      PNG, JPG, or screenshot containing payment/login QR
                    </div>
                  </label>
                </div>
              ) : (
                <div className="space-y-2">
                  <Input
                    placeholder={
                      activeTab === "url" 
                        ? "Paste suspicious link (e.g., https://secure-bank-verify.xyz)..." 
                        : activeTab === "upi"
                        ? "Enter recipient UPI ID (e.g., cash.reward@okhdfcbank)..."
                        : activeTab === "phone"
                        ? "Enter phone number or caller ID (e.g., +91 98765 43210 or 1930)..."
                        : "Paste suspicious SMS message text, WhatsApp lottery message, or lottery offer..."
                    }
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    className="h-12 text-sm bg-background/80"
                  />
                </div>
              )}

              <Button 
                type="submit" 
                disabled={loading || (!inputValue && !qrFile)}
                className="w-full h-11 text-sm font-medium"
              >
                {loading ? "Analyzing against 1.2M+ Threat Patterns..." : "Check Safety Instantly"}
              </Button>
            </form>
          </Card>

          {/* Results Presentation */}
          {currentResult && (() => {
            const indStatus = currentResult.indicator_status || (currentResult.is_safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS");
            const isMalicious = indStatus === "KNOWN_MALICIOUS";
            const isSuspicious = indStatus === "SUSPICIOUS";
            const isLegitimate = indStatus === "VERIFIED_LEGITIMATE";
            const isUnverified = indStatus === "UNKNOWN_UNVERIFIED";

            const cardBorder = isMalicious 
              ? "border-rose-500/50 bg-rose-500/5" 
              : isSuspicious 
              ? "border-amber-500/50 bg-amber-500/5" 
              : isLegitimate 
              ? "border-emerald-500/40 bg-emerald-500/5" 
              : "border-sky-500/40 bg-sky-500/5";

            const badgeStyle = isMalicious
              ? "bg-rose-500/10 text-rose-500 border-rose-500/30"
              : isSuspicious
              ? "bg-amber-500/10 text-amber-500 border-amber-500/30"
              : isLegitimate
              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
              : "bg-sky-500/10 text-sky-400 border-sky-500/30";

            const statusTitle = isMalicious
              ? "Confirmed Threat — Blocked"
              : isSuspicious
              ? "Suspicious Pattern Detected"
              : isLegitimate
              ? "Verified Official Entity"
              : "Unverified Indicator (Exercise Caution)";

            return (
              <Rise>
                <Card className={`p-6 border-2 transition-all shadow-md ${cardBorder}`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-3">
                      {isLegitimate ? (
                        <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                          <CheckCircle2 className="w-7 h-7" />
                        </div>
                      ) : isUnverified ? (
                        <div className="w-12 h-12 rounded-xl bg-sky-500/10 flex items-center justify-center text-sky-400">
                          <Info className="w-7 h-7" />
                        </div>
                      ) : isSuspicious ? (
                        <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-500">
                          <AlertTriangle className="w-7 h-7" />
                        </div>
                      ) : (
                        <div className="w-12 h-12 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-500">
                          <ShieldAlert className="w-7 h-7" />
                        </div>
                      )}
                      <div>
                        <h3 className="text-lg font-bold">
                          {statusTitle}
                        </h3>
                        <p className="text-xs text-muted-foreground">
                          Analyzed payload: <span className="font-mono text-foreground">{currentResult.input.substring(0, 40)}...</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-col items-end gap-1.5">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider border ${badgeStyle}`}>
                        {indStatus.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-muted-foreground uppercase font-semibold">
                        Risk: {currentResult.risk_level}
                      </span>
                    </div>
                  </div>

                  {/* Key Findings List */}
                  <div className="mt-4 pt-4 border-t border-border/40 space-y-2">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Analysis Findings:
                    </h4>
                    <ul className="space-y-1.5 text-sm">
                      {currentResult.reasons.map((r, i) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-muted-foreground">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>

                    {/* Actionable Practical Guidance */}
                    {currentResult.guidance && currentResult.guidance.length > 0 && (
                      <div className="mt-4 p-3.5 rounded-xl bg-card/90 border border-border/80 space-y-2">
                        <div className="text-xs font-semibold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                          <ShieldCheck className="w-4 h-4 text-primary" /> Practical Safety Guidance
                        </div>
                        <ul className="space-y-1.5 text-xs text-muted-foreground">
                          {currentResult.guidance.map((g, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <Check className="w-4 h-4 text-primary shrink-0" />
                              <span className="text-foreground/90">{g}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Pro Enrichment Insights */}
                    {isPro && currentResult.attack_dna_match && (
                      <div className="mt-4 p-3 rounded-lg bg-primary/10 border border-primary/20 text-xs space-y-1">
                        <div className="font-semibold text-primary flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5" /> Attack DNA Pattern Match (Pro Intelligence)
                        </div>
                        <div className="text-muted-foreground">
                          Identified tactics: <span className="text-foreground">{currentResult.attack_dna_match}</span>
                        </div>
                        {currentResult.related_cases && (
                          <div className="text-muted-foreground">
                            Correlated to <span className="text-foreground font-semibold">{currentResult.related_cases} reported cases</span> in the National Threat Graph.
                          </div>
                        )}
                      </div>
                    )}

                    {!isPro && !currentResult.is_safe && (
                      <div 
                        onClick={() => setShowUpgradeModal(true)}
                        className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs flex items-center justify-between cursor-pointer hover:bg-amber-500/15 transition-colors"
                      >
                        <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                          <Lock className="w-4 h-4" />
                          <span>Unlock Campaign Correlation & Graph Intelligence with Pro</span>
                        </div>
                        <ChevronRight className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                      </div>
                    )}
                  </div>
                </Card>
              </Rise>
            );
          })()}

          {/* Educational Trust Banner */}
          <div className="p-4 rounded-xl border border-border/60 bg-muted/20 text-xs text-muted-foreground space-y-1">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-primary" /> Privacy First Protection
            </div>
            <p>
              Digital Rakshak never stores your banking PIN, OTPs, or private chat histories. Scanned indicators are matched against cryptographic hashes in the national threat intelligence repository.
            </p>
          </div>
        </div>

        {/* Sidebar: Scan History & Pro Benefits */}
        <div className="lg:col-span-4 space-y-6">
          {/* Pro Benefits Card */}
          <Card className="p-5 border-border/60 bg-gradient-to-br from-card via-card to-primary/5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-500" /> Personal Pro Shield
              </h3>
              {isPro ? (
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                  ACTIVE
                </span>
              ) : (
                <span className="text-xs font-bold text-primary">₹149/mo</span>
              )}
            </div>

            <p className="text-xs text-muted-foreground">
              {isPro
                ? "Your account has unrestricted zero-day scanning, national threat graph correlation, and priority filing."
                : "Real-time continuous safety for yourself and family against emerging UPI frauds and phishing."}
            </p>

            <div className="space-y-2 text-xs">
              {[
                "Unlimited Zero-Day AI Scans",
                "Graph Correlation & Attack DNA",
                "Instant SMS / WhatsApp safety alerts",
                "Priority Cyber Cell filing assistance"
              ].map((feat, i) => (
                <div key={i} className="flex items-center gap-2 text-muted-foreground">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>{feat}</span>
                </div>
              ))}
            </div>

            {!isPro ? (
              <Button 
                onClick={() => setShowUpgradeModal(true)}
                className="w-full text-xs h-9 bg-primary hover:bg-primary/90"
              >
                Choose Subscription Plan
              </Button>
            ) : (
              <div className="pt-2 border-t border-border/40 flex items-center justify-between text-[11px] text-muted-foreground">
                <span>Account Status:</span>
                <span className="font-semibold text-emerald-500 flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Full Protection Active
                </span>
              </div>
            )}
          </Card>

          {/* Recent Scans History */}
          <Card className="p-5 border-border/60 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm flex items-center gap-2">
                <History className="w-4 h-4 text-muted-foreground" /> Recent Personal Scans
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">{scanHistory.length} recorded</span>
                {scanHistory.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearHistory}
                    disabled={clearingHistory}
                    className="h-7 px-2 text-[11px] text-muted-foreground hover:text-rose-400 hover:bg-rose-500/10"
                    title="Delete Personal Scan History"
                  >
                    <Trash2 className="w-3 h-3 mr-1" /> Clear
                  </Button>
                )}
              </div>
            </div>

            {scanHistory.length === 0 ? (
              <div className="text-center py-6 text-xs text-muted-foreground">
                No recent scans. Items you check will appear here.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-[340px] overflow-y-auto pr-1">
                {scanHistory.map((item) => (
                  <div 
                    key={item.id} 
                    className="p-2.5 rounded-lg border border-border/50 bg-background/60 hover:bg-muted/40 transition-colors text-xs flex items-center justify-between"
                  >
                    <div className="min-w-0 pr-2">
                      <div className="font-medium truncate text-foreground">{item.input}</div>
                      <div className="text-[10px] text-muted-foreground flex items-center gap-1.5 mt-0.5">
                        <span>{item.type}</span>
                        <span>•</span>
                        <span>{item.timestamp}</span>
                      </div>
                    </div>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      item.is_safe ? "bg-emerald-500/10 text-emerald-500" : "bg-rose-500/10 text-rose-500"
                    }`}>
                      {item.risk_level}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Upgrade Plan Modal */}
      {showUpgradeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border/80 rounded-2xl max-w-2xl w-full p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">Select Digital Rakshak Pro Plan</h3>
                <p className="text-xs text-muted-foreground">Secure recurring billing powered by Razorpay UPI AutoPay & Cards (18% GST added)</p>
              </div>
              <button 
                onClick={() => setShowUpgradeModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold p-1"
              ><X className="w-4 h-4" /></button>
            </div>

            {/* Plan Options - 3 Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5">
              {/* Card 1: Personal Pro */}
              <div 
                onClick={() => setSelectedPlan("b2c_pro_149")}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex flex-col justify-between ${
                  selectedPlan === "b2c_pro_149" 
                    ? "border-primary bg-primary/5 shadow-sm" 
                    : "border-border/60 hover:border-border"
                }`}
              >
                <div>
                  <div className="font-bold text-sm">Personal Pro</div>
                  <div className="text-2xl font-black mt-1">₹149<span className="text-xs font-normal text-muted-foreground">/mo</span></div>
                  <div className="text-[11px] text-sky-500 font-semibold mt-0.5">+ 18% GST (Total ₹175.82)</div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Complete single-device zero-day defense, threat analyzer & real-time scam alerts.
                  </p>
                </div>
              </div>

              {/* Card 2: Family Shield */}
              <div 
                onClick={() => setSelectedPlan("b2c_pro_249")}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex flex-col justify-between ${
                  selectedPlan === "b2c_pro_249" 
                    ? "border-primary bg-primary/5 shadow-sm" 
                    : "border-border/60 hover:border-border"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm">Family Shield</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-500/10 text-orange-500 font-bold">FAMILY PACK</span>
                  </div>
                  <div className="text-2xl font-black mt-1">₹249<span className="text-xs font-normal text-muted-foreground">/mo</span></div>
                  <div className="text-[11px] text-sky-500 font-semibold mt-0.5">+ 18% GST (Total ₹293.82)</div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Protects up to 4 family members, priority analysis, and personal cyber concierge.
                  </p>
                </div>
              </div>

              {/* Card 3: Annual Pro */}
              <div 
                onClick={() => setSelectedPlan("b2c_pro_annual")}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all flex flex-col justify-between ${
                  selectedPlan === "b2c_pro_annual" 
                    ? "border-emerald-500 bg-emerald-500/5 shadow-sm" 
                    : "border-border/60 hover:border-border"
                }`}
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm">Annual Pro</span>
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/15 text-emerald-400 font-bold">2 MOS FREE</span>
                  </div>
                  <div className="text-2xl font-black mt-1">₹1,299<span className="text-xs font-normal text-muted-foreground">/yr</span></div>
                  <div className="text-[11px] text-emerald-400 font-semibold mt-0.5">+ 18% GST (Total ₹1,532.82)</div>
                  <p className="text-xs text-muted-foreground mt-2">
                    365-day uninterrupted zero-day defense, instant Attack DNA lookups & concierge.
                  </p>
                </div>
              </div>
            </div>

            {/* Safety guarantee */}
            <div className="text-[11px] text-muted-foreground bg-muted/40 p-3 rounded-lg flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>Cancel anytime with 1-click in your settings. Tax invoice attached directly to confirmation email.</span>
            </div>

            <Button 
              onClick={handleInitiateRazorpayUpgrade}
              disabled={upgrading}
              className="w-full h-11 text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
            >
              {upgrading ? "Contacting Payment Gateway..." : (
                selectedPlan === "b2c_pro_annual"
                  ? "Proceed to Subscribe (₹1,532.82/yr incl. 18% GST)"
                  : selectedPlan === "b2c_pro_249"
                  ? "Proceed to Subscribe (₹293.82/mo incl. 18% GST)"
                  : "Proceed to Subscribe (₹175.82/mo incl. 18% GST)"
              )}
            </Button>
          </div>
        </div>
      )}

      {/* Cancel Subscription Confirmation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-rose-500 font-bold">
                <AlertTriangle className="w-5 h-5" />
                <span>Cancel Pro Subscription</span>
              </div>
              <button 
                onClick={() => setShowCancelModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold p-1"
              ><X className="w-4 h-4" /></button>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              Are you sure you want to cancel your <strong>Digital Rakshak Pro</strong> subscription?
            </p>

            <div className="bg-muted/40 p-3.5 rounded-xl text-xs space-y-2 border border-border/40">
              <div className="font-semibold text-foreground">Prorated Refund & Tax Policy:</div>
              <ul className="list-disc list-inside space-y-1.5 text-muted-foreground">
                <li><strong>Base Refund:</strong> A prorated refund for unutilized duration will be calculated exclusively from the base fee and credited back to your original payment method (UPI / Card) in 5–7 business days per RBI guidelines.</li>
                <li><strong>GST Policy:</strong> 18% Government GST remitted under SAC 998313 is statutory and strictly non-refundable.</li>
                <li><strong>No Bill on Cancellation:</strong> You will receive an official cancellation confirmation email itemizing your refund calculation without any bill attached.</li>
                <li><strong>Zero Data Loss:</strong> Your account immediately returns to <strong>Free Shield</strong>. All your past scans, evidence, and reports remain safe forever.</li>
              </ul>
            </div>

            <div className="space-y-1.5 pt-1">
              <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-rose-400" /> Refund Notification Delivery Email:
              </label>
              <Input
                type="email"
                placeholder="Enter email to receive refund confirmation..."
                value={cancelNotificationEmail}
                onChange={(e) => setCancelNotificationEmail(e.target.value)}
                className="h-10 text-xs bg-background/90"
              />
              <p className="text-[11px] text-muted-foreground">
                Your prorated refund settlement and timeline details will be delivered here.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={() => setShowCancelModal(false)}
                className="flex-1 text-sm font-medium"
              >
                Keep Pro Shield
              </Button>
              <Button
                onClick={handleCancelSubscription}
                disabled={cancelling}
                className="flex-1 text-sm font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-md shadow-rose-500/20"
              >
                {cancelling ? "Cancelling..." : "Confirm Cancellation"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Send Tax Invoice to Email Modal */}
      {showInvoiceEmailModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border/80 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-indigo-400 font-bold">
                <Mail className="w-5 h-5" />
                <span>Email Official Tax Invoice (PDF)</span>
              </div>
              <button 
                onClick={() => setShowInvoiceEmailModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold p-1"
              ><X className="w-4 h-4" /></button>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed">
              We will generate your official GST-compliant Tax Invoice as a mobile-compatible PDF and email it directly.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                Destination Email Address:
              </label>
              <Input
                type="email"
                placeholder="Enter recipient email (e.g. harshit2500sharma@gmail.com)..."
                value={invoiceTargetEmail}
                onChange={(e) => setInvoiceTargetEmail(e.target.value)}
                className="h-10 text-xs bg-background/90"
              />
              <p className="text-[11px] text-muted-foreground">
                Pre-filled with your registered account. You can enter your primary Gmail or any email.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-2">
              <Button
                variant="secondary"
                onClick={() => setShowInvoiceEmailModal(false)}
                className="flex-1 text-sm font-medium"
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendInvoiceEmail}
                disabled={resendingInvoice}
                className="flex-1 text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-500/20"
              >
                {resendingInvoice ? "Sending PDF..." : "Send Tax Invoice"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Pro Activation Loading Overlay */}
      <LoadingOverlay
        open={activatingPro}
        variant="payment"
        fullscreen={true}
        title="Activating Digital Rakshak Pro"
        subtitle="Payment confirmed. Securing your device and unlocking National Zero-Day Attack DNA..."
        badge="UPI AutoPay / Card Confirmed"
        steps={[
          "Verifying Razorpay cryptographic payment signature...",
          "Enrolling device in National Zero-Day Defense Grid...",
          "Unlocking Neo4j Attack DNA & Syndicate Graph..."
        ]}
      />
    </div>
  );
}
