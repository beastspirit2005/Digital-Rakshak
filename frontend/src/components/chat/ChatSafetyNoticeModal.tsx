"use client";

import { useState } from "react";
import {
  ShieldAlert,
  Lock,
  AlertTriangle,
  FileCheck2,
  CheckCircle2,
  ShieldCheck,
  Scale
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";

interface ChatSafetyNoticeModalProps {
  isOpen: boolean;
  onConsentGiven: () => void;
  onCancel?: () => void;
}

export function ChatSafetyNoticeModal({
  isOpen,
  onConsentGiven,
  onCancel,
}: ChatSafetyNoticeModalProps) {
  const { token } = useAuthStore();
  const [agreed, setAgreed] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConsent = async () => {
    if (!agreed) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await fetch(
        api("/chat/acknowledge-policy"),
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ policy_version: "v1.0" }),
        }
      );

      if (!res.ok) {
        throw new Error("Failed to record policy consent.");
      }

      onConsentGiven();
    } catch (err: any) {
      setError(err.message || "Failed to record consent.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/70 backdrop-blur-sm">
      <div className="bg-surface border border-amber-500/40 rounded-2xl max-w-xl w-full p-6 sm:p-7 space-y-5 shadow-2xl relative text-ink">
        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center shrink-0">
            <ShieldAlert className="w-6 h-6 text-amber-500" />
          </div>
          <div>
            <h2 className="text-lg sm:text-xl font-extrabold text-ink">
              Chat Safety & Evidence Monitoring Notice
            </h2>
            <p className="text-xs text-amber-600 dark:text-amber-300 font-semibold">
              Mandatory transparency disclosure before messaging
            </p>
          </div>
        </div>

        {/* Core Transparency Points */}
        <div className="space-y-3 text-xs text-ink-2 bg-surface-2 p-4 rounded-xl border border-line">
          <div className="flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <strong className="text-ink block">Hard Credential Protection</strong>
              Never share passwords, OTPs, UPI PINs, or card CVVs. Delivery of any authentication secret is automatically blocked.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <strong className="text-ink block">No Recovery Fees or Demands</strong>
              Official police and verified investigators NEVER demand registration fees, advance charges, or bribes. Any fee request will be flagged as a fraud attempt.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <Scale className="w-4 h-4 text-sky-500 shrink-0 mt-0.5" />
            <div>
              <strong className="text-ink block">Equal Accountability & Contextual Preservation</strong>
              Both citizens and investigators can report misconduct. When reported, surrounding messages are snapshot into an immutable evidence package locked with SHA-256 digests.
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <FileCheck2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
            <div>
              <strong className="text-ink block">Evidentiary Compliance (BSA 2023)</strong>
              Preserved digital records adhere to Sections 61–63 of the Bharatiya Sakshya Adhiniyam, 2023 for legal and judicial proceedings.
            </div>
          </div>
        </div>

        {/* Checkbox Acknowledgment */}
        <label className="flex items-start gap-3 cursor-pointer pt-1 select-none">
          <input
            type="checkbox"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
            className="mt-0.5 w-4 h-4 rounded border-line text-amber-500 focus:ring-amber-500 bg-surface-2"
          />
          <span className="text-xs text-ink-2 leading-relaxed">
            I have read and agree to the Chat Transparency Terms. I understand that messages are scanned for security, and misconduct evidence is cryptographically preserved.
          </span>
        </label>

        {error && (
          <p className="text-xs text-rose-500 font-semibold">{error}</p>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          {onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 rounded-lg bg-surface-2 hover:bg-surface-3 text-ink-2 text-xs font-semibold transition"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleConsent}
            disabled={!agreed || submitting}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:cursor-not-allowed text-black font-bold text-xs transition shadow-lg shadow-amber-500/20"
          >
            {submitting ? "Recording Consent..." : "I Understand & Agree"}
          </button>
        </div>
      </div>
    </div>
  );
}
