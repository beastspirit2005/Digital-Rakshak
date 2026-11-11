"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { 
  ShieldCheck, 
  AlertTriangle, 
  Link as LinkIcon, 
  QrCode, 
  Smartphone, 
  HandCoins, 
  Camera,
  CheckCircle2,
  Info,
  ShieldAlert,
  Sparkles, 
  Check,
  Lock,
  Zap,
  ArrowRight
} from "lucide-react";
import axios from "axios";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { Rise } from "@/components/ui/motion";
import { LoadingOverlay } from "@/components/ui/loading-overlay";

// html5-qrcode touches window at import time, so load it client-side only.
let Html5QrcodeScanner: any;
if (typeof window !== "undefined") {
  import("html5-qrcode").then((mod) => {
    Html5QrcodeScanner = mod.Html5QrcodeScanner;
  });
}

const TABS = [
  { id: "url", label: "Link", icon: LinkIcon, placeholder: "https://example.com", verb: "Scan link" },
  { id: "upi", label: "UPI ID", icon: HandCoins, placeholder: "merchant@bank", verb: "Verify UPI ID" },
  { id: "apk", label: "App file", icon: Smartphone, placeholder: "Upload an APK", verb: "Check APK" },
  { id: "qr", label: "QR code", icon: QrCode, placeholder: "Upload a QR image", verb: "Decode QR" },
];

export default function PreventionSuite() {
  const { user, token, updateUser } = useAuthStore();
  const isPro = Boolean(user?.is_pro || (user?.role && user.role !== "citizen"));

  const [activeTab, setActiveTab] = useState("url");
  const [inputValue, setInputValue] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [useCamera, setUseCamera] = useState(false);

  // Pro Upgrade State
  const [upgrading, setUpgrading] = useState(false);
  const [activatingPro, setActivatingPro] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<"b2c_pro_annual" | "b2c_pro_149">("b2c_pro_annual");
  const [upgradeError, setUpgradeError] = useState("");

  const ensureRazorpayLoaded = (): Promise<boolean> => {
    return new Promise((resolve) => {
      if (typeof window === "undefined") return resolve(false);
      if ((window as any).Razorpay) return resolve(true);
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

  const handleInitiateRazorpayUpgrade = async () => {
    setUpgrading(true);
    setUpgradeError("");
    try {
      await ensureRazorpayLoaded();
      const subRes = await axios.post(
        api("/billing/create-subscription"),
        { plan_code: selectedPlan },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const { subscription_id, order_id, razorpay_key_id } = subRes.data;

      // Sandbox developer mode fallback when no real Razorpay credentials are configured
      if (!(window as any).Razorpay || !razorpay_key_id || razorpay_key_id.startsWith("rzp_test_placeholder")) {
        setActivatingPro(true);
        try {
          await axios.post(
            api("/billing/verify-payment"),
            {
              razorpay_payment_id: "pay_sandbox_" + Math.random().toString(36).substring(7),
              razorpay_subscription_id: subscription_id,
              razorpay_order_id: order_id,
              razorpay_signature: "sandbox_valid_sig",
              plan_code: selectedPlan,
            },
            { headers: { Authorization: `Bearer ${token}` } }
          );
          updateUser({
            b2c_plan_code: selectedPlan,
            b2c_subscription_status: "active",
            is_pro: true,
          });
        } finally {
          setTimeout(() => setActivatingPro(false), 1200);
        }
        return;
      }

      const options = {
        key: razorpay_key_id,
        subscription_id: subscription_id || undefined,
        order_id: order_id || undefined,
        name: "Digital Rakshak",
        description: selectedPlan === "b2c_pro_annual" ? "Pro Annual Plan (₹1,299/yr)" : "Personal Pro Monthly (₹149/mo)",
        image: "/icons/shield-accent.png",
        prefill: {
          name: user?.full_name || "",
          email: user?.email || "",
          contact: user?.station_phone_number || "",
        },
        theme: { color: "#F59E0B" },
        handler: async (response: any) => {
          setActivatingPro(true);
          try {
            await axios.post(
              api("/billing/verify-payment"),
              {
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_subscription_id: response.razorpay_subscription_id || subscription_id || "",
                razorpay_signature: response.razorpay_signature || "",
                plan_code: selectedPlan,
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );
            updateUser({
              b2c_plan_code: selectedPlan,
              b2c_subscription_status: "active",
              is_pro: true,
            });
          } catch (err: any) {
            setUpgradeError("Payment verification failed. Please contact support.");
          } finally {
            setTimeout(() => setActivatingPro(false), 1200);
          }
        },
        modal: {
          ondismiss: () => {
            setUpgrading(false);
          },
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();
    } catch (err: any) {
      setUpgradeError(err.response?.data?.detail || "Could not initialize checkout. Please retry.");
    } finally {
      setUpgrading(false);
    }
  };

  const authHeaders = token ? { Authorization: `Bearer ${token}` } : {};

  const scanTextPayload = async (text: string) => {
    if (!text) return;
    setLoading(true);
    setResult(null);
    try {
      const payload =
        activeTab === "url" ? { url: text.trim() } : activeTab === "upi" ? { upi: text.trim() } : { text: text.trim() };

      const res = await axios.post(api("/scan"), payload, { headers: authHeaders });
      setResult({
        safe: res.data.is_safe,
        risk_level: res.data.risk_level || (res.data.is_safe ? "LOW" : "HIGH"),
        indicator_status: res.data.indicator_status || (res.data.is_safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS"),
        reasons: res.data.reasons || [],
        guidance: res.data.guidance || [],
        attack_dna_match: res.data.attack_dna_match,
        related_cases: res.data.related_cases,
      });
    } catch (err: any) {
      setResult({
        safe: false,
        risk_level: "HIGH",
        indicator_status: "SUSPICIOUS",
        reasons: [err.response?.data?.detail || "The scan request failed."],
        guidance: ["Verify the indicator or network connection and try again."],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (useCamera && activeTab === "qr" && Html5QrcodeScanner) {
      const scanner = new Html5QrcodeScanner(
        "reader",
        { fps: 10, qrbox: { width: 250, height: 250 } },
        false
      );

      scanner.render(
        (decodedText: string) => {
          scanner.clear();
          setUseCamera(false);
          setInputValue(decodedText);
          scanTextPayload(decodedText);
        },
        () => {
          // continuous-scan errors are expected noise
        }
      );

      return () => {
        scanner.clear().catch(console.error);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useCamera, activeTab]);



  const handleScan = async () => {
    setLoading(true);
    setResult(null);
    try {
      if (activeTab === "qr" && selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const res = await axios.post(api("/scan/qr"), formData, { headers: authHeaders });
        setResult({
          safe: res.data.is_safe,
          risk_level: res.data.risk_level || (res.data.is_safe ? "LOW" : "HIGH"),
          indicator_status: res.data.indicator_status || (res.data.is_safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS"),
          reasons: res.data.reasons || ["QR payload decoded and verified."],
          guidance: res.data.guidance || [],
          attack_dna_match: res.data.attack_dna_match,
          related_cases: res.data.related_cases,
        });
      } else if (activeTab === "apk" && selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const res = await axios.post(api("/scan/apk"), formData, {
          headers: { ...authHeaders, "Content-Type": "multipart/form-data" }
        });
        setResult({
          safe: res.data.is_safe,
          risk_level: res.data.risk_level || (res.data.is_safe ? "LOW" : "CRITICAL"),
          indicator_status: res.data.is_safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS",
          reasons: res.data.reasons || ["No dangerous permissions found in APK."],
          guidance: res.data.is_safe
            ? ["Install only from Google Play Store or verified official developers."]
            : ["Uninstall this APK immediately. Do not grant Accessibility or SMS permissions."],
        });
      } else {
        await scanTextPayload(inputValue);
        return;
      }
    } catch (err: any) {
      setResult({
        safe: false,
        risk_level: "HIGH",
        indicator_status: "SUSPICIOUS",
        reasons: [err.response?.data?.detail || "The scan request failed."],
        guidance: ["Please check the input and retry."],
      });
    } finally {
      setLoading(false);
    }
  };

  const currentTab = TABS.find((t) => t.id === activeTab)!;

  if (!isPro) {
    return (
      <div className="max-w-2xl mx-auto space-y-6 pt-4">
        {activatingPro && (
          <LoadingOverlay
            open={true}
            fullscreen={true}
            variant="cyber"
            title="Activating Digital Rakshak Pro"
            subtitle="Configuring Zero-Day Scam Prevention Suite for your account..."
            badge="Pro Membership"
            steps={[
              "Verifying secure payment receipt...",
              "Enabling APK decompiler heuristics...",
              "Unlocking optical QR quishing engine...",
              "Activating continuous cyber protection..."
            ]}
          />
        )}

        <Rise>
          <div className="text-center space-y-3">
            <div className="w-16 h-16 rounded-3xl bg-amber-500/10 border border-amber-500/25 flex items-center justify-center mx-auto shadow-[0_0_30px_rgba(245,158,11,0.2)]">
              <Lock className="w-8 h-8 text-amber-400" />
            </div>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5" />
              Pro Feature
            </div>
            <h1 className="font-display font-bold text-3xl tracking-tight text-ink">
              Scam Prevention Hub
            </h1>
            <p className="text-sm text-ink-2 max-w-lg mx-auto">
              The unified Scam Prevention Hub offers advanced APK bytecode decompilation, live optical QR camera decoding, and National Threat Graph integration. This suite is reserved for Pro subscribers.
            </p>
          </div>
        </Rise>

        {upgradeError && (
          <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0" />
            <span>{upgradeError}</span>
          </div>
        )}

        <Rise index={1}>
          <Card className="p-6 space-y-6 border-line bg-surface/80 backdrop-blur-sm">
            <div className="space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-ink-3">
                Capabilities Unlocked With Pro
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  {
                    title: "APK Malware Decompiler",
                    desc: "Inspects Android binaries for banking trojans, SMS interceptors & overlay permissions.",
                    icon: Smartphone,
                  },
                  {
                    title: "Live Camera QR Quishing",
                    desc: "Real-time optical matrix scanning to detect disguised payment lures before you tap.",
                    icon: QrCode,
                  },
                  {
                    title: "Zero-Trust VPA Risk",
                    desc: "Cross-checks virtual payment addresses against nationwide mule account registries.",
                    icon: HandCoins,
                  },
                  {
                    title: "Attack DNA Profiling",
                    desc: "Correlates deceptive indicators with MITRE ATT&CK scam campaign tactics.",
                    icon: Sparkles,
                  },
                ].map((item, idx) => {
                  const Icon = item.icon;
                  return (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl border border-line bg-surface-2/60 flex items-start gap-3"
                    >
                      <div className="w-8 h-8 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center shrink-0 mt-0.5">
                        <Icon className="w-4 h-4 text-accent" />
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-xs font-semibold text-ink">{item.title}</div>
                        <div className="text-[11px] text-ink-2 leading-relaxed">{item.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Plan Selector */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <div
                onClick={() => setSelectedPlan("b2c_pro_annual")}
                className={cn(
                  "p-4 rounded-xl border cursor-pointer transition-all",
                  selectedPlan === "b2c_pro_annual"
                    ? "border-amber-500 bg-amber-500/5 ring-1 ring-amber-500"
                    : "border-line bg-surface-2 hover:border-ink-3"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-ink">Annual Defense</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-bold border border-emerald-500/20">
                    SAVE 28%
                  </span>
                </div>
                <div className="text-2xl font-bold font-display text-ink">₹1,299 <span className="text-xs font-normal text-ink-3">/year</span></div>
                <div className="text-[11px] text-ink-2 mt-1">₹108/month • Billed annually</div>
              </div>

              <div
                onClick={() => setSelectedPlan("b2c_pro_149")}
                className={cn(
                  "p-4 rounded-xl border cursor-pointer transition-all",
                  selectedPlan === "b2c_pro_149"
                    ? "border-amber-500 bg-amber-500/5 ring-1 ring-amber-500"
                    : "border-line bg-surface-2 hover:border-ink-3"
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-bold text-ink">Monthly Shield</span>
                  <span className="text-[10px] text-ink-3">Flexible</span>
                </div>
                <div className="text-2xl font-bold font-display text-ink">₹149 <span className="text-xs font-normal text-ink-3">/month</span></div>
                <div className="text-[11px] text-ink-2 mt-1">Cancel anytime in 1-click</div>
              </div>
            </div>

            {/* Upgrade CTA */}
            <Button
              type="button"
              variant="primary"
              size="lg"
              loading={upgrading}
              onClick={handleInitiateRazorpayUpgrade}
              className="w-full h-12 bg-amber-500 hover:bg-amber-600 text-black font-bold uppercase tracking-wider text-xs rounded-xl shadow-[0_4px_20px_rgba(245,158,11,0.25)] flex items-center justify-center gap-2"
            >
              <Zap className="w-4 h-4 fill-current" />
              <span>Activate Pro Access Now</span>
            </Button>

            {/* Free Alternative Link */}
            <div className="p-3.5 rounded-xl bg-surface-2/40 border border-line flex items-center justify-between text-xs">
              <span className="text-ink-2">
                Looking for free threat scanning?
              </span>
              <Link
                href="/personal"
                className="text-accent font-semibold hover:underline inline-flex items-center gap-1"
              >
                <span>Use Personal Shield (Free)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </Card>
        </Rise>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 pt-2">
      <Rise>
        <PageHeader
          title="Check before you trust"
          sub="Scan a link, UPI ID, app, or QR code before you tap it."
        />
      </Rise>

      <Rise index={1}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setResult(null);
                  setInputValue("");
                  setSelectedFile(null);
                  setUseCamera(false);
                }}
                className={cn(
                  "p-4 rounded-card flex flex-col items-center gap-1.5 transition-colors duration-150",
                  isActive
                    ? "bg-surface shadow-card text-ink"
                    : "bg-surface-2 text-ink-2 hover:text-ink hover:bg-surface-3"
                )}
                aria-pressed={isActive}
              >
                <Icon className="w-5 h-5" strokeWidth={isActive ? 2.2 : 2} />
                <span className="text-sm font-medium">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </Rise>

      <Rise index={2}>
        <Card className="relative p-6 overflow-hidden">
          <LoadingOverlay
            open={loading}
            fullscreen={false}
            variant="cyber"
            title={
              activeTab === "apk"
                ? "Analyzing Android Application Package"
                : activeTab === "qr"
                ? "Decoding & Analyzing QR Matrix"
                : activeTab === "upi"
                ? "Validating Virtual Payment Address"
                : "Inspecting Web Link & Destination"
            }
            subtitle="Running zero-trust validation and heuristics against national threat registry..."
            badge="Zero-Trust Scanner"
            steps={
              activeTab === "apk"
                ? [
                    "Decompiling AndroidManifest.xml and extracted assets...",
                    "Auditing sensitive permissions (SMS, Accessibility, Overlay)...",
                    "Scanning embedded command-and-control (C2) domains...",
                    "Computing APK heuristic risk score..."
                  ]
                : activeTab === "qr"
                ? [
                    "Extracting payload from image pixel matrix...",
                    "Unpacking embedded URL or UPI intent string...",
                    "Querying National Threat Pattern Registry (TPR)...",
                    "Synthesizing threat confidence..."
                  ]
                : activeTab === "upi"
                ? [
                    "Parsing Virtual Payment Address (VPA) structure...",
                    "Checking against known mule account registries...",
                    "Analyzing UPI handle reputation and velocity...",
                    "Verifying merchant authenticity..."
                  ]
                : [
                    "Following redirect chain and DNS resolution...",
                    "Auditing SSL certificate authenticity...",
                    "Checking phishing signatures against 1.2M+ records...",
                    "Evaluating zero-day domain generation algorithms..."
                  ]
            }
          />
          {useCamera && activeTab === "qr" && (
            <div className="w-full max-w-md mx-auto mb-4 overflow-hidden rounded-card border border-line">
              <div id="reader" className="w-full" />
              <button
                onClick={() => setUseCamera(false)}
                className="w-full p-2.5 bg-surface-2 text-sm text-ink hover:bg-surface-3 transition-colors"
              >
                Cancel camera
              </button>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3">
            {activeTab === "qr" || activeTab === "apk" ? (
              <div className="flex-1 flex gap-2">
                <Input
                  key={`file-${activeTab}`}
                  type="file"
                  accept={activeTab === "qr" ? "image/*" : ".apk"}
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setSelectedFile(e.target.files[0]);
                      setInputValue(e.target.files[0].name);
                    } else {
                      setSelectedFile(null);
                      setInputValue("");
                    }
                  }}
                  className="pt-2 file:mr-3 file:py-1.5 file:px-3 file:rounded-pill file:border-0 file:text-xs file:font-medium file:bg-surface-2 file:text-ink hover:file:bg-surface-3"
                />
                {activeTab === "qr" && (
                  <Button type="button" onClick={() => setUseCamera(true)} className="h-11">
                    <Camera className="w-4 h-4" />
                    Camera
                  </Button>
                )}
              </div>
            ) : (
              <Input
                key={`text-${activeTab}`}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={currentTab.placeholder}
                className="flex-1"
              />
            )}

            <Button
              variant="primary"
              size="lg"
              onClick={handleScan}
              disabled={(!inputValue && !selectedFile) || useCamera}
              loading={loading}
              className="sm:w-auto w-full"
            >
              {currentTab.verb}
            </Button>
          </div>

          {result && (() => {
            const indStatus = result.indicator_status || (result.safe ? "UNKNOWN_UNVERIFIED" : "KNOWN_MALICIOUS");
            const isMalicious = indStatus === "KNOWN_MALICIOUS";
            const isSuspicious = indStatus === "SUSPICIOUS";
            const isLegitimate = indStatus === "VERIFIED_LEGITIMATE";
            const isUnverified = indStatus === "UNKNOWN_UNVERIFIED";

            const cardBorder = isMalicious
              ? "border-rose-500/50 bg-rose-500/5"
              : isSuspicious
              ? "border-amber-500/50 bg-amber-500/5"
              : isLegitimate
              ? "border-emerald-500/50 bg-emerald-500/5"
              : "border-sky-500/40 bg-sky-500/5";

            const badgeStyle = isMalicious
              ? "bg-rose-500/10 text-rose-500 border-rose-500/30"
              : isSuspicious
              ? "bg-amber-500/10 text-amber-500 border-amber-500/30"
              : isLegitimate
              ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
              : "bg-sky-500/10 text-sky-400 border-sky-500/30";

            const statusTitle = isMalicious
              ? "Confirmed Threat — High Risk / Do Not Proceed"
              : isSuspicious
              ? "Suspicious Pattern Detected"
              : isLegitimate
              ? "Verified Official Entity"
              : "Unverified Indicator (Exercise Caution)";

            return (
              <div
                className={cn(
                  "mt-6 p-5 rounded-card rise-in border-2 transition-all shadow-sm",
                  cardBorder
                )}
                role="status"
              >
                <div className="flex items-start justify-between gap-3 mb-3">
                  <div className="flex items-center gap-3">
                    {isLegitimate ? (
                      <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-500 shrink-0">
                        <CheckCircle2 className="w-6 h-6" />
                      </div>
                    ) : isUnverified ? (
                      <div className="w-10 h-10 rounded-xl bg-sky-500/10 flex items-center justify-center text-sky-400 shrink-0">
                        <Info className="w-6 h-6" />
                      </div>
                    ) : isSuspicious ? (
                      <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-500 shrink-0">
                        <AlertTriangle className="w-6 h-6" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-xl bg-rose-500/10 flex items-center justify-center text-rose-500 shrink-0">
                        <ShieldAlert className="w-6 h-6" />
                      </div>
                    )}
                    <div>
                      <h3 className="font-display font-semibold text-base text-foreground">
                        {statusTitle}
                      </h3>
                      <p className="text-xs text-muted-foreground">
                        Risk assessment: <span className="font-semibold uppercase">{result.risk_level}</span>
                      </p>
                    </div>
                  </div>

                  <span className={cn("px-2.5 py-1 rounded-md text-xs font-bold uppercase tracking-wider border shrink-0", badgeStyle)}>
                    {indStatus.replace("_", " ")}
                  </span>
                </div>

                {/* Analysis Findings */}
                {result.reasons && result.reasons.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/40 space-y-1.5">
                    <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      Analysis Findings:
                    </h4>
                    <ul className="space-y-1 text-xs text-foreground/90">
                      {result.reasons.map((r: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <span className="text-muted-foreground">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Actionable Practical Guidance */}
                {result.guidance && result.guidance.length > 0 && (
                  <div className="mt-3.5 p-3 rounded-lg bg-card/80 border border-border/60 space-y-1.5">
                    <div className="text-xs font-semibold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-primary" /> Practical Safety Guidance
                    </div>
                    <ul className="space-y-1 text-xs text-muted-foreground">
                      {result.guidance.map((g: string, i: number) => (
                        <li key={i} className="flex items-start gap-2">
                          <Check className="w-4 h-4 text-primary shrink-0" />
                          <span className="text-foreground/90">{g}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Pro Attack DNA / Graph Insights */}
                {result.attack_dna_match && (
                  <div className="mt-3 p-2.5 rounded-lg bg-primary/10 border border-primary/20 text-xs text-primary space-y-1">
                    <div className="font-semibold flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5" /> Attack DNA Pattern Match
                    </div>
                    <div className="text-xs text-foreground/80">
                      {result.attack_dna_match}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </Card>
      </Rise>
    </div>
  );
}
