"use client";

import { useState } from "react";
import {
  AlertOctagon,
  ShieldCheck,
  FileLock2,
  X,
  AlertTriangle
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

interface ReportMisconductModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId?: string;
  reportedMessageId?: string;
  reportedUserId: string;
  reportedUserName?: string;
  onReportSuccess?: (sha256: string) => void;
}

const CATEGORIES = [
  { value: "payment_demand", label: "Demand for Payment, Bribe, or Advance Fee" },
  { value: "credential_harvesting", label: "Asking for Password, OTP, PIN, or CVV" },
  { value: "recovery_scam", label: "Guaranteed Fund Recovery Claim / Cyber Agency Fee" },
  { value: "impersonation", label: "Falsely Claiming Official Police / Judicial Authority" },
  { value: "harassment", label: "Harassment, Abusive Language, or Extortion Threats" },
];

export function ReportMisconductModal({
  isOpen,
  onClose,
  caseId,
  reportedMessageId,
  reportedUserId,
  reportedUserName = "User",
  onReportSuccess,
}: ReportMisconductModalProps) {
  const { token } = useAuthStore();
  const [category, setCategory] = useState("payment_demand");
  const [narrative, setNarrative] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successDigest, setSuccessDigest] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (narrative.trim().length < 10) {
      setError("Please provide at least 10 characters explaining what occurred.");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(
        api("/chat/safety-reports"),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            case_id: caseId,
            reported_message_id: reportedMessageId,
            reported_user_id: reportedUserId,
            category,
            reason_narrative: narrative.trim(),
          }),
        }
      );

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Failed to submit misconduct report.");
      }

      const data = await res.json();
      setSuccessDigest(data.evidence_package_sha256);
      if (onReportSuccess) {
        onReportSuccess(data.evidence_package_sha256);
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit report.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0e1320] border border-red-500/30 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative text-gray-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        {!successDigest ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-500/15 border border-red-500/40 flex items-center justify-center shrink-0">
                <AlertOctagon className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Report Misconduct</h3>
                <p className="text-xs text-gray-400">
                  Preserve evidence & trigger administrative dispute review
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-white/5 border border-white/5 text-xs text-gray-300">
              Reporting: <span className="font-semibold text-white">{reportedUserName}</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                Violation Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#161c2e] border border-white/10 text-white text-xs focus:outline-none focus:border-red-500"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                Description of Violation
              </label>
              <textarea
                value={narrative}
                onChange={(e) => setNarrative(e.target.value)}
                placeholder="Explain precisely what occurred, any demands made, or suspicious links provided..."
                rows={4}
                className="w-full p-3 rounded-lg bg-[#161c2e] border border-white/10 text-white placeholder-gray-500 text-xs focus:outline-none focus:border-red-500 leading-relaxed"
              />
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 flex items-start gap-2">
              <FileLock2 className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
              <span>
                Evidence Preservation: Submitting this report automatically locks the reported message and surrounding conversation context with a cryptographic SHA-256 seal for impartial admin review.
              </span>
            </div>

            {error && (
              <p className="text-xs text-red-400 font-semibold">{error}</p>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-bold text-xs transition shadow-lg shadow-red-600/25"
              >
                {submitting ? "Preserving Evidence..." : "Submit & Preserve Evidence"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4 py-2 text-center">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/40 flex items-center justify-center mx-auto">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-base font-bold text-white">
              Misconduct Evidence Preserved
            </h3>
            <p className="text-xs text-gray-300 max-w-sm mx-auto leading-relaxed">
              Your report has been submitted to the Admin Misconduct Review Queue. The conversation context has been sealed.
            </p>
            <div className="p-3 rounded-xl bg-black/40 border border-white/10 text-left space-y-1">
              <span className="text-[10px] uppercase font-bold text-gray-500 block">
                Evidence SHA-256 Digest (BSA Sec. 63)
              </span>
              <span className="font-mono text-emerald-400 text-[11px] break-all select-all block">
                {successDigest}
              </span>
            </div>
            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold text-xs transition"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
