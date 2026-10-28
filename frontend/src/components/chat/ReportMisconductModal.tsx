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
  reportedUserId?: string;
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
  reportedUserName = "Assigned Counterpart",
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
      const payload: Record<string, any> = {
        case_id: caseId,
        category,
        reason_narrative: narrative.trim(),
      };
      if (reportedMessageId) {
        payload.reported_message_id = reportedMessageId;
      }
      if (reportedUserId) {
        payload.reported_user_id = reportedUserId;
      }

      const res = await fetch(
        api("/chat/safety-reports"),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm">
      <div className="bg-surface border border-rose-500/40 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative text-ink">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-ink-3 hover:text-ink p-1 rounded-lg hover:bg-surface-2 transition-colors"
          aria-label="Close modal"
        >
          <X className="w-5 h-5" />
        </button>

        {!successDigest ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center shrink-0">
                <AlertOctagon className="w-5 h-5 text-rose-500" />
              </div>
              <div>
                <h3 className="text-base font-bold text-ink">Report Misconduct</h3>
                <p className="text-xs text-ink-3">
                  Preserve cryptographic evidence & trigger administrative review
                </p>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface-2 border border-line text-xs text-ink-2">
              Reporting: <span className="font-semibold text-ink">{reportedUserName}</span>
            </div>

            <div>
              <label className="text-xs font-semibold text-ink-2 block mb-1">
                Violation Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-surface-2 border border-line text-ink text-xs focus:outline-none focus:border-rose-500"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value} className="bg-surface text-ink">
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-ink-2 block mb-1">
                Description of Violation
              </label>
              <textarea
                value={narrative}
                onChange={(e) => setNarrative(e.target.value)}
                placeholder="Explain precisely what occurred, any demands made, or suspicious links provided..."
                rows={4}
                className="w-full p-3 rounded-lg bg-surface-2 border border-line text-ink placeholder:text-ink-3 text-xs focus:outline-none focus:border-rose-500 leading-relaxed"
              />
            </div>

            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-[11px] text-amber-600 dark:text-amber-300 flex items-start gap-2">
              <FileLock2 className="w-4 h-4 shrink-0 text-amber-500 mt-0.5" />
              <span>
                Evidence Preservation: Submitting this report automatically locks the conversation context with a cryptographic SHA-256 seal for impartial admin review.
              </span>
            </div>

            {error && (
              <p className="text-xs text-rose-500 font-semibold">{error}</p>
            )}

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-lg bg-surface-2 hover:bg-surface-3 text-ink-2 text-xs font-semibold transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-50 text-white font-bold text-xs transition shadow-lg shadow-rose-600/25"
              >
                {submitting ? "Preserving Evidence..." : "Submit & Preserve Evidence"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4 py-2 text-center">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center mx-auto">
              <ShieldCheck className="w-6 h-6 text-emerald-500" />
            </div>
            <h3 className="text-base font-bold text-ink">
              Misconduct Evidence Preserved
            </h3>
            <p className="text-xs text-ink-3 max-w-sm mx-auto leading-relaxed">
              Your report has been submitted to the Admin Misconduct Review Queue. The conversation context has been sealed.
            </p>
            <div className="p-3 rounded-xl bg-surface-2 border border-line text-left space-y-1">
              <span className="text-[10px] uppercase font-bold text-ink-3 block">
                Evidence SHA-256 Digest (BSA Sec. 63)
              </span>
              <span className="font-mono text-emerald-600 dark:text-emerald-400 text-[11px] break-all select-all block">
                {successDigest}
              </span>
            </div>
            <button
              onClick={onClose}
              className="w-full py-2.5 rounded-lg bg-surface-2 hover:bg-surface-3 text-ink font-semibold text-xs transition border border-line"
            >
              Done
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
