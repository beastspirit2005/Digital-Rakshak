"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import axios from "axios";
import { api, formatApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { BrandLogo } from "@/components/brand-logo";
import {
  ShieldCheck,
  Download,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  ArrowRight,
  FileText,
  Lock,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

function InvoiceDownloadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const subId = searchParams.get("subscription_id") || "latest";
  const urlToken = searchParams.get("token");

  const { token: storeToken, login, isAuthenticated, isHydrated } = useAuthStore();
  const [status, setStatus] = useState<"authenticating" | "downloading" | "completed" | "error">("authenticating");
  const [errorMsg, setErrorMsg] = useState("");
  const [countdown, setCountdown] = useState(3);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const hasTriggeredRef = useRef(false);

  useEffect(() => {
    if (hasTriggeredRef.current) return;

    const processInvoiceFlow = async () => {
      hasTriggeredRef.current = true;
      let effectiveToken = urlToken || storeToken;

      // 1. If a token was provided in the URL, hydrate the user session
      if (urlToken) {
        try {
          setStatus("authenticating");
          const meRes = await axios.get(api("/users/me"), {
            headers: { Authorization: `Bearer ${urlToken}` },
          });
          login(urlToken, meRes.data);
          effectiveToken = urlToken;
        } catch (authErr) {
          console.warn("Could not authenticate with URL token:", authErr);
          // If URL token fails, fall back to stored token if available
          effectiveToken = storeToken;
        }
      }

      // 2. Check if user is authenticated
      if (!effectiveToken) {
        setStatus("error");
        setErrorMsg("Authentication required to download your official Tax Invoice.");
        const currentPath = typeof window !== "undefined" ? window.location.pathname + window.location.search : "/billing/invoice";
        setTimeout(() => {
          router.replace(`/auth/login?next=${encodeURIComponent(currentPath)}`);
        }, 1200);
        return;
      }

      // 3. Initiate PDF download via authenticated blob stream
      try {
        setStatus("downloading");
        const pdfRes = await axios.get(api(`/billing/invoice/${subId}/pdf?token=${encodeURIComponent(effectiveToken)}`), {
          headers: { Authorization: `Bearer ${effectiveToken}` },
          responseType: "blob",
        });

        const blob = new Blob([pdfRes.data], { type: "application/pdf" });
        const objectUrl = window.URL.createObjectURL(blob);
        setDownloadUrl(objectUrl);

        // Auto-trigger browser file download
        const link = document.createElement("a");
        link.href = objectUrl;
        link.download = `Digital_Rakshak_Tax_Invoice_${subId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setStatus("completed");
      } catch (err: any) {
        setStatus("error");
        setErrorMsg(
          err.response?.status === 401
            ? "Your session has expired. Please sign in to download your invoice."
            : formatApiError(err, "Could not generate tax invoice PDF. Please try again.")
        );
      }
    };

    processInvoiceFlow();
  }, [subId, urlToken, storeToken, login, router]);

  // Countdown timer to automatically transition to /personal when completed
  useEffect(() => {
    if (status !== "completed") return;

    const interval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(interval);
          router.replace("/personal");
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [status, router]);

  const handleManualDownload = () => {
    if (downloadUrl) {
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `Digital_Rakshak_Tax_Invoice_${subId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else {
      const effectiveToken = urlToken || storeToken;
      if (effectiveToken) {
        window.open(api(`/billing/invoice/${subId}/pdf?token=${encodeURIComponent(effectiveToken)}`), "_blank");
      }
    }
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col justify-between items-center p-4 sm:p-6 relative overflow-hidden font-sans">
      {/* Background radial glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[120px] pointer-events-none" />

      {/* Header */}
      <header className="w-full max-w-xl flex items-center justify-between pt-4 pb-8 z-10">
        <BrandLogo />
        <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-blue-500/20 bg-blue-500/10 text-blue-400 text-xs font-semibold uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-400" />
          <span>GST SAC 998313</span>
        </div>
      </header>

      {/* Main Card */}
      <main className="w-full max-w-lg bg-[#0e1626]/90 border border-slate-800/80 rounded-2xl p-6 sm:p-8 backdrop-blur-xl shadow-2xl z-10 text-center space-y-6">
        {status === "authenticating" && (
          <div className="space-y-4 py-6">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Authenticating Security Token...
            </h1>
            <p className="text-sm text-slate-400 max-w-sm mx-auto">
              Verifying your digital credentials and initializing your authenticated session.
            </p>
          </div>
        )}

        {status === "downloading" && (
          <div className="space-y-4 py-6">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
              <Loader2 className="w-8 h-8 animate-spin" />
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Preparing Your Tax Invoice...
            </h1>
            <p className="text-sm text-slate-400 max-w-sm mx-auto">
              Rendering official Section 31 A4 GST Tax Invoice with SAC 998313 breakdown.
            </p>
          </div>
        )}

        {status === "completed" && (
          <div className="space-y-6 py-2">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <CheckCircle2 className="w-9 h-9" />
            </div>

            <div className="space-y-2">
              <h1 className="text-xl sm:text-2xl font-extrabold text-white">
                Tax Invoice Downloaded!
              </h1>
              <p className="text-sm text-slate-300">
                Your official GST Tax Invoice has been generated and downloaded to your device.
              </p>
            </div>

            <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 text-left space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wide">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Digital Rakshak Pro Active</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Your account is equipped with active Zero-Day threat analysis, deep APK inspection, and optical QR quishing defense.
              </p>
            </div>

            <div className="pt-2 space-y-3">
              <button
                type="button"
                onClick={() => router.replace("/personal")}
                className="w-full h-12 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 transition-all active:scale-[0.99]"
              >
                <span>Launch Pro Protection Portal</span>
                <ArrowRight className="w-4 h-4" />
                <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full ml-1">
                  ({countdown}s)
                </span>
              </button>

              <button
                type="button"
                onClick={handleManualDownload}
                className="w-full h-10 rounded-xl border border-slate-700 bg-slate-800/60 hover:bg-slate-800 text-slate-300 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF Again</span>
              </button>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="space-y-6 py-2">
            <div className="w-16 h-16 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertTriangle className="w-8 h-8" />
            </div>

            <div className="space-y-2">
              <h1 className="text-xl sm:text-2xl font-extrabold text-white">
                Unable to Access Invoice
              </h1>
              <p className="text-sm text-rose-300">
                {errorMsg}
              </p>
            </div>

            <div className="pt-2 space-y-3">
              <Link
                href={`/auth/login?next=${encodeURIComponent(typeof window !== "undefined" ? window.location.pathname + window.location.search : "/personal")}`}
                className="w-full h-12 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-lg shadow-blue-500/20 transition-all"
              >
                <Lock className="w-4 h-4" />
                <span>Sign In to Your Account</span>
              </Link>

              <Link
                href="/personal"
                className="w-full h-10 rounded-xl border border-slate-700 bg-slate-800/60 hover:bg-slate-800 text-slate-300 font-semibold text-xs flex items-center justify-center gap-2 transition-colors"
              >
                <span>Continue to Platform</span>
              </Link>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="w-full max-w-xl text-center py-6 text-xs text-slate-500 space-y-1 z-10">
        <p>Digital Rakshak Cyber Defense &bull; National Threat Intelligence Network</p>
        <p className="text-[11px] text-slate-600">GSTIN: 07AABCD1234E1Z5 &bull; Section 31 CGST Act, 2017</p>
      </footer>
    </div>
  );
}

export default function InvoiceDownloadPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#070b14] flex items-center justify-center text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      }
    >
      <InvoiceDownloadContent />
    </Suspense>
  );
}
