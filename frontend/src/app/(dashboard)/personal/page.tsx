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
  Users
} from "lucide-react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Rise } from "@/components/ui/motion";
import { useToast } from "@/components/ui/toast";

interface ScanRecord {
  id: string;
  type: string;
  input: string;
  is_safe: boolean;
  risk_level: string;
  reasons: string[];
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

  const [activeTab, setActiveTab] = useState<"url" | "text" | "upi" | "qr">("url");
  const [inputValue, setInputValue] = useState("");
  const [qrFile, setQrFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentResult, setCurrentResult] = useState<ScanRecord | null>(null);
  const [scanHistory, setScanHistory] = useState<ScanRecord[]>([]);

  // Upgrade Modal State
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<"b2c_pro_149" | "b2c_pro_249">("b2c_pro_149");
  const [upgrading, setUpgrading] = useState(false);

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
    // Load user-specific scan history from backend if logged in, fallback to local storage
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
        setShowUpgradeModal(false);
        pushToast("success", "Welcome to Digital Rakshak Pro! Zero-day AI and Attack DNA are now active.");
        return;
      }

      // 2. Open Real Razorpay Checkout Modal
      const options: any = {
        key: razorpay_key_id,
        name: "Digital Rakshak",
        description: selectedPlan === "b2c_pro_149" ? "Personal Pro (₹149/mo)" : "Pro Family Shield (₹249/mo)",
        amount: amount_paise || (selectedPlan === "b2c_pro_149" ? 14900 : 24900),
        currency: "INR",
        handler: async function (response: any) {
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
            setShowUpgradeModal(false);
            pushToast("success", "Welcome to Digital Rakshak Pro! Zero-day AI and Attack DNA are now active.");
          } catch (verErr: any) {
            pushToast("danger", "Payment verification failed. Please contact support.");
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

        {!isPro && !isOfficialRole && (
          <Button 
            onClick={() => setShowUpgradeModal(true)}
            className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white font-medium shadow-md shadow-orange-500/20"
          >
            <Zap className="w-4 h-4 mr-2" /> Upgrade to Pro
          </Button>
        )}
      </div>

      {/* Main Scanner Section */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-6">
          <Card className="p-6 border-border/60 shadow-sm bg-card/60 backdrop-blur-sm">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                Zero-Day Threat Scanner
              </span>
              <span className="text-xs text-muted-foreground">
                {isOfficialRole ? "Institutional Officer Shield Active" : isPro ? "Unlimited Scans Active" : "5 Free Daily Guest Scans"}
              </span>
            </div>

            {/* Input Mode Selector */}
            <div className="grid grid-cols-4 gap-2 mb-6">
              {[
                { id: "url", label: "Web Link", icon: LinkIcon },
                { id: "text", label: "Message / SMS", icon: FileText },
                { id: "upi", label: "UPI ID", icon: HandCoins },
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
          {currentResult && (
            <Rise>
              <Card className={`p-6 border-2 transition-all shadow-md ${
                currentResult.is_safe 
                  ? "border-emerald-500/40 bg-emerald-500/5" 
                  : currentResult.risk_level === "CRITICAL"
                  ? "border-rose-500/50 bg-rose-500/5"
                  : "border-amber-500/50 bg-amber-500/5"
              }`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3">
                    {currentResult.is_safe ? (
                      <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                        <CheckCircle2 className="w-7 h-7" />
                      </div>
                    ) : (
                      <div className="w-12 h-12 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-500">
                        <ShieldAlert className="w-7 h-7" />
                      </div>
                    )}
                    <div>
                      <h3 className="text-lg font-bold">
                        {currentResult.is_safe ? "No Threats Found — Looks Safe" : `${currentResult.risk_level} Risk Detected!`}
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Analyzed payload: <span className="font-mono text-foreground">{currentResult.input.substring(0, 40)}...</span>
                      </p>
                    </div>
                  </div>

                  <span className={`px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider ${
                    currentResult.is_safe 
                      ? "bg-emerald-500/10 text-emerald-500" 
                      : "bg-rose-500/10 text-rose-500"
                  }`}>
                    {currentResult.risk_level}
                  </span>
                </div>

                {/* Key Findings List */}
                <div className="mt-4 pt-4 border-t border-border/40 space-y-2">
                  <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                    Analysis Findings & Advice:
                  </h4>
                  <ul className="space-y-1.5 text-sm">
                    {currentResult.reasons.map((r, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-muted-foreground">•</span>
                        <span>{r}</span>
                      </li>
                    ))}
                  </ul>

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
          )}

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
              <span className="text-xs text-muted-foreground">{scanHistory.length} recorded</span>
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
          <div className="bg-card border border-border/80 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-foreground">Select Digital Rakshak Pro Plan</h3>
                <p className="text-xs text-muted-foreground">Secure recurring billing powered by Razorpay UPI AutoPay & Cards</p>
              </div>
              <button 
                onClick={() => setShowUpgradeModal(false)}
                className="text-muted-foreground hover:text-foreground text-sm font-semibold p-1"
              >
                ✕
              </button>
            </div>

            {/* Plan Options */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div 
                onClick={() => setSelectedPlan("b2c_pro_149")}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  selectedPlan === "b2c_pro_149" 
                    ? "border-primary bg-primary/5 shadow-sm" 
                    : "border-border/60 hover:border-border"
                }`}
              >
                <div className="font-bold text-sm">Personal Pro</div>
                <div className="text-2xl font-black mt-1">₹149<span className="text-xs font-normal text-muted-foreground">/mo</span></div>
                <p className="text-xs text-muted-foreground mt-2">
                  Complete single-device protection, zero-day threat analyzer & scam alerts.
                </p>
              </div>

              <div 
                onClick={() => setSelectedPlan("b2c_pro_249")}
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  selectedPlan === "b2c_pro_249" 
                    ? "border-primary bg-primary/5 shadow-sm" 
                    : "border-border/60 hover:border-border"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm">Family Shield</span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] bg-orange-500/10 text-orange-500 font-bold">BEST VALUE</span>
                </div>
                <div className="text-2xl font-black mt-1">₹249<span className="text-xs font-normal text-muted-foreground">/mo</span></div>
                <p className="text-xs text-muted-foreground mt-2">
                  Protects up to 4 family members, priority analysis, and personal cyber concierge.
                </p>
              </div>
            </div>

            {/* Safety guarantee */}
            <div className="text-[11px] text-muted-foreground bg-muted/40 p-3 rounded-lg flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>Cancel anytime with 1-click in your settings. Backed by Razorpay e-mandate guidelines.</span>
            </div>

            <Button 
              onClick={handleInitiateRazorpayUpgrade}
              disabled={upgrading}
              className="w-full h-11 text-sm font-semibold bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white"
            >
              {upgrading ? "Contacting Payment Gateway..." : `Proceed to Subscribe (${selectedPlan === "b2c_pro_149" ? "₹149/mo" : "₹249/mo"})`}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
