"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { api, formatApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import {
  Send,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Lock,
  Loader2,
  RefreshCw,
  X,
  FileCheck2,
  Info,
  Scale
} from "lucide-react";
import { ChatSafetyNoticeModal } from "./ChatSafetyNoticeModal";
import { ReportMisconductModal } from "./ReportMisconductModal";
import { useToast } from "@/components/ui/toast";

export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_name: string;
  sender_role: string;
  is_self: boolean;
  content: string;
  moderation_flag?: string | null;
  attachments?: any[];
  created_at: string;
}

interface CaseChatPanelProps {
  caseId: string;
  caseNumber: string;
  assignedOfficerName?: string;
  assignedOfficerRole?: string;
  onClose?: () => void;
  className?: string;
}

export function CaseChatPanel({
  caseId,
  caseNumber,
  assignedOfficerName,
  assignedOfficerRole,
  onClose,
  className = "",
}: CaseChatPanelProps) {
  const { token, user } = useAuthStore();
  const pushToast = useToast();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [policyAccepted, setPolicyAccepted] = useState<boolean | null>(null);
  const [showPolicyModal, setShowPolicyModal] = useState(false);

  // Misconduct Reporting State
  const [reportingMessage, setReportingMessage] = useState<ChatMessage | null>(null);
  const [showReportModal, setShowReportModal] = useState(false);

  // Client-side quick credential warning
  const [credentialWarning, setCredentialWarning] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const isFetchingRef = useRef(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // 1. Check Policy Consent Status
  const checkPolicyStatus = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await axios.get(api("/chat/policy-status"), {
        headers: { Authorization: `Bearer ${token}` },
        withCredentials: true,
        signal,
      });
      const accepted = !!res.data?.is_accepted;
      setPolicyAccepted(accepted);
      if (!accepted) {
        setShowPolicyModal(true);
      }
    } catch (err: any) {
      if (axios.isCancel(err) || err.name === "CanceledError") return;
      console.error("Failed to check chat policy status:", err);
      // Default to asking consent if error
      setShowPolicyModal(true);
    }
  }, [token]);

  // 2. Fetch Messages
  const fetchMessages = useCallback(async (quiet = false, signal?: AbortSignal) => {
    if (isFetchingRef.current) return;
    isFetchingRef.current = true;
    if (!quiet) setLoading(true);
    try {
      const res = await axios.get(api(`/chat/cases/${caseId}/messages`), {
        headers: { Authorization: `Bearer ${token}` },
        withCredentials: true,
        signal,
      });
      if (res.data?.messages) {
        setMessages(res.data.messages);
      }
    } catch (err: any) {
      if (axios.isCancel(err) || err.name === "CanceledError") return;
      console.error("Failed to fetch messages:", err);
      if (!quiet) {
        pushToast("danger", `Could not load messages: ${formatApiError(err, "Please check network or case access.")}`);
      }
    } finally {
      isFetchingRef.current = false;
      if (!quiet) setLoading(false);
    }
  }, [caseId, token, pushToast]);

  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    checkPolicyStatus(controller.signal);
    fetchMessages(false, controller.signal);

    // Auto-poll messages every 6 seconds
    const interval = setInterval(() => {
      if (!controller.signal.aborted) {
        fetchMessages(true, controller.signal);
      }
    }, 6000);

    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, [checkPolicyStatus, fetchMessages]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Client-side real-time credential pattern check
  useEffect(() => {
    const text = inputText.toLowerCase();
    const otpMatch = text.match(/\b(otp|one\s*time\s*password|verification\s*code)\s*[:=is-]*\s*(\d{4,8})\b/i);
    const pinMatch = text.match(/\b(upi\s*pin|mpin|atm\s*pin|card\s*pin)\s*[:=is-]*\s*(\d{4,6})\b/i);
    const cvvMatch = text.match(/\b(cvv|cvc)\s*[:=is-]*\s*(\d{3,4})\b/i);

    if (otpMatch || pinMatch || cvvMatch) {
      setCredentialWarning("Security Alert: Never type or share OTPs, UPI PINs, or CVVs. Digital Rakshak automated safeguards will reject this message.");
    } else {
      setCredentialWarning(null);
    }
  }, [inputText]);

  // Send message
  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputText.trim() || sending) return;

    if (!policyAccepted) {
      setShowPolicyModal(true);
      return;
    }

    const contentToSend = inputText.trim();
    setSending(true);

    try {
      const res = await axios.post(
        api(`/chat/cases/${caseId}/messages`),
        { content: contentToSend },
        {
          headers: { Authorization: `Bearer ${token}` },
          withCredentials: true,
        }
      );

      setInputText("");
      setCredentialWarning(null);

      // Append new message
      if (res.data?.id) {
        const newMsg: ChatMessage = {
          id: res.data.id,
          sender_id: user?.id || "",
          sender_name: user?.full_name || "You",
          sender_role: user?.role || "citizen",
          is_self: true,
          content: res.data.content,
          moderation_flag: res.data.moderation_flag,
          attachments: res.data.attachments || [],
          created_at: res.data.created_at || new Date().toISOString(),
        };
        setMessages((prev) => [...prev, newMsg]);
        scrollToBottom();
      } else {
        await fetchMessages(true);
      }
    } catch (err: any) {
      console.error("Message send failed:", err);
      const errMsg = formatApiError(err, "Failed to deliver message.");
      pushToast("danger", `Message Delivery Blocked: ${errMsg}`);
    } finally {
      setSending(false);
    }
  };

  // Open Misconduct Reporting Modal for a message
  const handleOpenReport = (msg?: ChatMessage) => {
    setReportingMessage(msg || null);
    setShowReportModal(true);
  };

  return (
    <div
      className={`flex flex-col h-full bg-surface border border-line rounded-2xl shadow-2xl overflow-hidden font-sans text-ink ${className}`}
    >
      {/* Top Header */}
      <div className="p-3.5 sm:p-4 bg-surface-2 border-b border-line flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-500 p-[2px] flex items-center justify-center shrink-0">
            <div className="w-full h-full rounded-[10px] bg-surface flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-accent" />
            </div>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-accent truncate">
                {caseNumber}
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 shrink-0">
                OFFICIAL CHANNEL
              </span>
            </div>
            <p className="text-xs text-ink-2 font-medium truncate">
              {assignedOfficerName
                ? `Officer ${assignedOfficerName} (${assignedOfficerRole || "Investigator"})`
                : "Authorized Cyber Cell Duty Desk"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Header Report Misconduct Button */}
          <button
            onClick={() => handleOpenReport()}
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 transition-colors"
            title="Report misconduct or dispute on this case"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Report Misconduct</span>
          </button>

          <button
            onClick={() => fetchMessages(false)}
            className="p-1.5 rounded-lg text-ink-3 hover:text-ink hover:bg-surface-3 transition-colors"
            title="Refresh Messages"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-ink-3 hover:text-ink hover:bg-surface-3 transition-colors"
              title="Close Chat Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Safety Notice Strip */}
      <div className="px-3.5 py-2 bg-amber-500/10 dark:bg-amber-500/5 border-b border-line flex items-center justify-between text-[11px] text-ink-2">
        <div className="flex items-center gap-1.5 min-w-0">
          <Lock className="w-3.5 h-3.5 text-amber-500 shrink-0" />
          <span className="truncate">
            <strong className="text-amber-600 dark:text-amber-300">Zero Tolerance:</strong> Do not share OTPs, PINs, or fees. Monitored under BSA-2023.
          </span>
        </div>
        <span className="hidden md:inline font-mono text-[10px] text-ink-3 shrink-0 ml-2">
          SEC-MONITOR-V1
        </span>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-bg/40">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center space-y-2 text-ink-3">
            <Loader2 className="w-6 h-6 animate-spin text-accent" />
            <span className="text-xs">Connecting to secure case channel...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-3">
            <div className="p-3 rounded-2xl bg-surface-2 border border-line text-accent">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h4 className="font-bold text-sm text-ink">Direct Case Communications Channel</h4>
            <p className="text-xs text-ink-3 max-w-sm leading-relaxed">
              This channel enables direct, monitored coordination between the citizen complainant and assigned duty officers. Ask questions, request updates, or submit additional context.
            </p>
          </div>
        ) : (
          messages.map((m) => {
            const isOfficer = m.sender_role === "police" || m.sender_role === "cyber_cell" || m.sender_role === "admin";
            const isSelf = m.is_self;

            return (
              <div
                key={m.id}
                className={`flex flex-col group ${isSelf ? "items-end" : "items-start"}`}
              >
                {/* Sender Tag */}
                <div className="flex items-center gap-1.5 mb-1 px-1 text-[10px] text-ink-3">
                  <span className="font-semibold text-ink-2">{m.sender_name}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                      isOfficer
                        ? "bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30"
                        : "bg-sky-500/15 text-sky-600 dark:text-sky-300 border border-sky-500/30"
                    }`}
                  >
                    {m.sender_role}
                  </span>
                  <span>•</span>
                  <span>{new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                </div>

                {/* Bubble Container */}
                <div className="relative max-w-[85%] sm:max-w-[75%]">
                  <div
                    className={`px-4 py-2.5 rounded-2xl text-xs leading-relaxed break-words shadow-sm ${
                      isSelf
                        ? "bg-accent text-accent-contrast rounded-br-sm"
                        : "bg-surface-2 text-ink border border-line rounded-bl-sm"
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* Flagged warning badge if system flagged */}
                  {m.moderation_flag && (
                    <div className="flex items-center gap-1 text-[10px] text-amber-600 dark:text-amber-300 mt-1 px-1">
                      <AlertTriangle className="w-3 h-3 text-amber-500" />
                      <span>Security Notice: {m.moderation_flag}</span>
                    </div>
                  )}

                  {/* Inline Report Action on messages from other party - Permanently Visible */}
                  {!isSelf && (
                    <div className="mt-1 flex items-center justify-end">
                      <button
                        onClick={() => handleOpenReport(m)}
                        className="inline-flex items-center gap-1 text-[10px] text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 font-medium px-2 py-0.5 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-colors"
                        title="Report this specific message"
                      >
                        <ShieldAlert className="w-3 h-3" />
                        <span>Report Message</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Real-time Credential Pre-Send Warning */}
      {credentialWarning && (
        <div className="px-4 py-2 bg-rose-500/15 border-t border-rose-500/30 text-rose-600 dark:text-rose-300 text-xs flex items-center gap-2 animate-pulse">
          <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
          <span>{credentialWarning}</span>
        </div>
      )}

      {/* Input Form */}
      <form
        onSubmit={handleSendMessage}
        className="p-3 bg-surface-2 border-t border-line flex items-center gap-2"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type message to investigator... (never share OTP/PIN)"
          disabled={sending}
          className="flex-1 px-3.5 py-2.5 rounded-xl text-xs bg-surface border border-line text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-accent disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={!inputText.trim() || sending}
          className="px-4 py-2.5 rounded-xl font-bold text-xs bg-accent hover:bg-accent/90 text-accent-contrast transition-all flex items-center gap-1.5 shadow-sm active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {sending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <span>Send</span>
              <Send className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </form>

      {/* Policy Consent Modal */}
      <ChatSafetyNoticeModal
        isOpen={showPolicyModal}
        onConsentGiven={() => {
          setShowPolicyModal(false);
          setPolicyAccepted(true);
        }}
        onCancel={() => setShowPolicyModal(false)}
      />

      {/* Report Misconduct Modal */}
      <ReportMisconductModal
        isOpen={showReportModal}
        onClose={() => {
          setShowReportModal(false);
          setReportingMessage(null);
        }}
        caseId={caseId}
        reportedMessageId={reportingMessage?.id}
        reportedUserId={reportingMessage?.sender_id}
        reportedUserName={reportingMessage?.sender_name || (assignedOfficerName ? `Officer ${assignedOfficerName}` : "Case Counterpart")}
        onReportSuccess={(digest) => {
          pushToast("success", `Misconduct Preserved: Evidence snapshot generated. SHA-256: ${digest.substring(0, 16)}...`);
          setShowReportModal(false);
          setReportingMessage(null);
        }}
      />
    </div>
  );
}
