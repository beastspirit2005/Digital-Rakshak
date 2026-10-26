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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // 1. Check Policy Consent Status
  const checkPolicyStatus = useCallback(async () => {
    try {
      const res = await axios.get(api("/chat/policy-status"), {
        headers: { Authorization: `Bearer ${token}` },
        withCredentials: true,
      });
      const accepted = !!res.data?.is_accepted;
      setPolicyAccepted(accepted);
      if (!accepted) {
        setShowPolicyModal(true);
      }
    } catch (err) {
      console.error("Failed to check chat policy status:", err);
      // Default to asking consent if error
      setShowPolicyModal(true);
    }
  }, [token]);

  // 2. Fetch Messages
  const fetchMessages = useCallback(async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const res = await axios.get(api(`/chat/cases/${caseId}/messages`), {
        headers: { Authorization: `Bearer ${token}` },
        withCredentials: true,
      });
      if (res.data?.messages) {
        setMessages(res.data.messages);
      }
    } catch (err: any) {
      console.error("Failed to fetch messages:", err);
      if (!quiet) {
        pushToast("danger", `Could not load messages: ${formatApiError(err, "Please check network or case access.")}`);
      }
    } finally {
      if (!quiet) setLoading(false);
    }
  }, [caseId, token, pushToast]);

  useEffect(() => {
    checkPolicyStatus();
    fetchMessages();

    // Auto-poll messages every 6 seconds
    const interval = setInterval(() => {
      fetchMessages(true);
    }, 6000);

    return () => clearInterval(interval);
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
  const handleOpenReport = (msg: ChatMessage) => {
    setReportingMessage(msg);
    setShowReportModal(true);
  };

  return (
    <div
      className={`flex flex-col h-full bg-[#0b101b] border border-white/10 rounded-2xl shadow-2xl overflow-hidden font-sans ${className}`}
    >
      {/* Top Header */}
      <div className="p-3.5 sm:p-4 bg-slate-900/90 border-b border-white/10 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-500 p-[2px] flex items-center justify-center">
            <div className="w-full h-full rounded-[10px] bg-slate-950 flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-sky-400">
                {caseNumber}
              </span>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                OFFICIAL CHANNEL
              </span>
            </div>
            <p className="text-xs text-slate-300 font-medium">
              {assignedOfficerName
                ? `Officer ${assignedOfficerName} (${assignedOfficerRole || "Investigator"})`
                : "Authorized Cyber Cell Duty Desk"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => fetchMessages(false)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh Messages"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="Close Chat Panel"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Safety Notice Strip */}
      <div className="px-3.5 py-2 bg-gradient-to-r from-amber-500/10 via-rose-500/10 to-indigo-500/10 border-b border-white/5 flex items-center justify-between text-[11px] text-slate-300">
        <div className="flex items-center gap-1.5">
          <Lock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>
            <strong className="text-amber-300">Zero Tolerance:</strong> Do not share OTPs, PINs, or transfer fees. All messages are cryptographically logged under BSA-2023.
          </span>
        </div>
        <span className="hidden sm:inline font-mono text-[10px] text-slate-400">
          SEC-MONITOR-V1
        </span>
      </div>

      {/* Message List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {loading ? (
          <div className="h-full flex flex-col items-center justify-center space-y-2 text-slate-400">
            <Loader2 className="w-6 h-6 animate-spin text-cyan-400" />
            <span className="text-xs">Connecting to secure case channel...</span>
          </div>
        ) : messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-3">
            <div className="p-3 rounded-2xl bg-slate-900 border border-white/10 text-cyan-400">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h4 className="font-bold text-sm text-white">Direct Case Communications Channel</h4>
            <p className="text-xs text-slate-400 max-w-sm leading-relaxed">
              This channel enables direct, monitored coordination between the victim and the assigned investigator. Ask case questions, request updates, or submit additional context.
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
                <div className="flex items-center gap-1.5 mb-1 px-1 text-[10px] text-slate-400">
                  <span className="font-semibold text-slate-300">{m.sender_name}</span>
                  <span
                    className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                      isOfficer
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
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
                    className={`px-4 py-2.5 rounded-2xl text-xs leading-relaxed break-words shadow-md ${
                      isSelf
                        ? "bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-sm"
                        : "bg-slate-900/90 text-slate-100 border border-white/10 rounded-bl-sm"
                    }`}
                  >
                    {m.content}
                  </div>

                  {/* Flagged warning badge if system flagged */}
                  {m.moderation_flag && (
                    <div className="flex items-center gap-1 text-[10px] text-amber-300 mt-1 px-1">
                      <AlertTriangle className="w-3 h-3 text-amber-400" />
                      <span>Security Notice: {m.moderation_flag}</span>
                    </div>
                  )}

                  {/* Inline Report Action on messages from other party */}
                  {!isSelf && (
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-1 flex items-center justify-end">
                      <button
                        onClick={() => handleOpenReport(m)}
                        className="inline-flex items-center gap-1 text-[10px] text-rose-400 hover:text-rose-300 font-medium px-1.5 py-0.5 rounded bg-rose-950/40 border border-rose-500/20 hover:border-rose-500/40"
                      >
                        <ShieldAlert className="w-3 h-3" />
                        <span>Report Misconduct</span>
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
        <div className="px-4 py-2 bg-rose-950/80 border-t border-rose-500/30 text-rose-200 text-xs flex items-center gap-2 animate-pulse">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{credentialWarning}</span>
        </div>
      )}

      {/* Input Form */}
      <form
        onSubmit={handleSendMessage}
        className="p-3 bg-slate-900/90 border-t border-white/10 flex items-center gap-2"
      >
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Type message to investigator... (never share OTP/PIN)"
          disabled={sending}
          className="flex-1 px-3.5 py-2.5 rounded-xl text-xs bg-slate-950 border border-white/10 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50"
        />

        <button
          type="submit"
          disabled={!inputText.trim() || sending}
          className="px-4 py-2.5 rounded-xl font-semibold text-xs bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 transition-all flex items-center gap-1.5 shadow-md active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
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
      {reportingMessage && (
        <ReportMisconductModal
          isOpen={showReportModal}
          onClose={() => {
            setShowReportModal(false);
            setReportingMessage(null);
          }}
          caseId={caseId}
          reportedMessageId={reportingMessage.id}
          reportedUserId={reportingMessage.sender_id}
          reportedUserName={reportingMessage.sender_name}
          onReportSuccess={(digest) => {
            pushToast("success", `Misconduct Preserved: Evidence snapshot generated. SHA-256: ${digest.substring(0, 16)}...`);
            setShowReportModal(false);
            setReportingMessage(null);
          }}
        />
      )}
    </div>
  );
}
