"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";
import axios from "axios";
import { Send, Bot, Trash2, X, Sparkles, Headphones, Loader2 } from "lucide-react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  engine?: string;
}

import { usePathname } from "next/navigation";

function stripThinkingTags(content: string): string {
  if (!content) return "";
  const cleaned = content.replace(/<think>[\s\S]*?<\/think>/g, "").replace(/<think>[\s\S]*$/g, "").trim();
  return cleaned || content;
}

export function GlobalChatWidget() {
  const { user, token } = useAuthStore();
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiMode, setAiMode] = useState("groq");
  const [lastAnswerEngine, setLastAnswerEngine] = useState<string>("");
  const [caseId, setCaseId] = useState("");
  const [isEscalating, setIsEscalating] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

  const isProUser = Boolean(
    user?.is_pro ||
    user?.b2c_plan_code === "b2c_pro" ||
    user?.role === "police" ||
    user?.role === "admin" ||
    user?.role === "cyber_cell"
  );

  const handleEscalatePriority = async () => {
    if (!user || isEscalating) return;
    setIsEscalating(true);
    try {
      const res = await axios.post(
        api("/help/escalate-priority"),
        {
          session_id: user.id,
          reason: "Priority human investigator support requested from chat copilot",
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const ticketNum = res.data?.ticket_number || "PRO-QUEUE";
      const sysMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: `**Priority Support Escalated (${ticketNum})**\n\nYour session has been prioritized and routed to our on-duty human investigator team. A specialized investigator will review your recent queries and case records.`,
        timestamp: Date.now(),
        engine: "Human Investigator Priority Queue",
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch (err: any) {
      console.error("Priority escalation failed:", err);
      const msg =
        err.response?.data?.detail ||
        "Priority escalation is only available to Digital Rakshak Pro subscribers.";
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: `**Escalation Notice:** ${msg}`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsEscalating(false);
    }
  };

  useEffect(() => {
    if (user?.id) {
      const saved = localStorage.getItem(`rakshak_chat_${user.id}`);
      if (saved) {
        try {
          setMessages(JSON.parse(saved));
        } catch (e) {
          console.error("Failed to parse chat history");
        }
      }
    }
  }, [user]);

  useEffect(() => {
    if (user?.id && messages.length > 0) {
      localStorage.setItem(`rakshak_chat_${user.id}`, JSON.stringify(messages));
    }
  }, [messages, user]);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
    }
  }, [messages, isOpen, reduced]);

  const handleClearChat = () => {
    setMessages([]);
    if (user?.id) {
      localStorage.removeItem(`rakshak_chat_${user.id}`);
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: Date.now(),
    };

    if (!user) return;
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(
        api("/help/chat"),
        {
          session_id: user.id,
          message: userMsg.content,
          role: user.role,
          model: aiMode,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const engine = response.data.engine || (aiMode === "ollama" ? "Ollama (local)" : "Groq (cloud)");
      setLastAnswerEngine(engine);

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.data.reply,
        timestamp: Date.now(),
        engine: engine,
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "The AI core couldn't be reached.";
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `**Error:** ${errorMsg}`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  if (!user) return null;
  
  // Hide widget on dedicated help/support pages to avoid confusion
  if (pathname === "/help" || pathname === "/admin/support") return null;

  return (
    <div className="fixed bottom-20 md:bottom-6 right-4 md:right-6 z-50 flex flex-col items-end">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduced ? { opacity: 0 } : { opacity: 0, y: 12 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="mb-3 w-[380px] h-[560px] max-h-[75vh] max-w-[calc(100vw-2rem)] bg-surface rounded-card shadow-card border border-line flex flex-col overflow-hidden"
          >
            {/* header */}
            <div className="bg-surface-2 px-4 py-3 flex flex-col gap-2.5 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-ink" />
                  <span className="font-display font-semibold text-sm text-ink">
                    Rakshak assistant
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={handleClearChat}
                    className="p-1.5 rounded-pill text-ink-3 hover:text-danger hover:bg-surface transition-colors"
                    title="Clear conversation"
                    aria-label="Clear conversation"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1.5 rounded-pill text-ink-3 hover:text-ink hover:bg-surface transition-colors"
                    aria-label="Close chat"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <select
                  value={aiMode}
                  onChange={(e) => setAiMode(e.target.value)}
                  className="h-8 flex-1 rounded-control bg-surface border border-line px-2 text-xs text-ink focus:border-accent-text focus:outline-none"
                  aria-label="AI engine"
                >
                  <option value="groq">Groq — cloud</option>
                  <option value="ollama">Ollama — local</option>
                </select>
                {user.role === "admin" && (
                  <input
                    type="text"
                    value={caseId}
                    onChange={(e) => setCaseId(e.target.value)}
                    placeholder="Case ID (optional)"
                    className="h-8 flex-1 rounded-control bg-surface border border-line px-2 text-xs text-ink placeholder:text-ink-3 focus:border-accent-text focus:outline-none"
                  />
                )}
              </div>
            </div>

            {/* Pro Priority Support Bar */}
            <div className="px-3.5 py-1.5 bg-gradient-to-r from-amber-500/10 via-sky-500/10 to-indigo-500/10 border-b border-line flex items-center justify-between text-xs shrink-0">
              {isProUser ? (
                <>
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span className="font-semibold text-amber-300 text-[11px]">Pro Priority Active</span>
                  </div>
                  <button
                    onClick={handleEscalatePriority}
                    disabled={isEscalating}
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-400 hover:text-sky-300 transition-colors disabled:opacity-50"
                  >
                    {isEscalating ? (
                      <>
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Routing...</span>
                      </>
                    ) : (
                      <>
                        <Headphones className="w-3 h-3" />
                        <span>Human Investigator</span>
                      </>
                    )}
                  </button>
                </>
              ) : (
                <>
                  <div className="flex items-center gap-1.5 text-ink-3 text-[11px]">
                    <span>AI Copilot Active</span>
                  </div>
                  <Link
                    href="/personal"
                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-400 hover:text-amber-300 transition-colors"
                  >
                    <Sparkles className="w-3 h-3" />
                    <span>Get Pro Priority Support</span>
                  </Link>
                </>
              )}
            </div>

            {/* body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2">
                  <Bot className="w-8 h-8 text-ink-3" />
                  <p className="text-xs text-ink-2 max-w-[15rem]">
                    Ask about your cases, the platform, or what to do next. The assistant knows
                    you&apos;re signed in as a {user.role.replace(/_/g, " ")}.
                  </p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}
                  >
                    <div
                      className={cn(
                        "text-sm max-w-[85%] rounded-card px-3.5 py-2.5",
                        msg.role === "user"
                          ? "bg-surface-3 text-ink"
                          : "bg-surface-2 text-ink"
                      )}
                    >
                      {msg.role === "user" ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        <div className="space-y-1">
                          <div className="chat-markdown [&_p]:leading-snug [&_p+p]:mt-2 [&_pre]:bg-surface [&_pre]:p-2 [&_pre]:rounded-control [&_pre]:text-xs [&_code]:text-xs [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_a]:underline">
                            <ReactMarkdown>{stripThinkingTags(msg.content)}</ReactMarkdown>
                          </div>
                          {msg.engine && (
                            <div className="text-[10px] text-ink-3 font-mono flex items-center gap-1 pt-1 border-t border-line/10">
                              <span className={`w-1.5 h-1.5 rounded-full ${msg.engine.toLowerCase().includes("ollama") ? "bg-emerald-500" : "bg-sky-500"}`} />
                              <span>via {msg.engine}</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}

              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-surface-2 rounded-card px-3.5 py-3 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-ink-3 rounded-pill animate-bounce" />
                    <span
                      className="w-1.5 h-1.5 bg-ink-3 rounded-pill animate-bounce"
                      style={{ animationDelay: "0.15s" }}
                    />
                    <span
                      className="w-1.5 h-1.5 bg-ink-3 rounded-pill animate-bounce"
                      style={{ animationDelay: "0.3s" }}
                    />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* input */}
            <div className="p-3 border-t border-line flex flex-col gap-1.5 bg-surface">
              <form onSubmit={handleSend} className="relative flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    lastAnswerEngine
                      ? `Ask a question (answered by ${lastAnswerEngine})...`
                      : `Ask a question (${aiMode === "ollama" ? "Ollama — local" : "Groq — cloud"})...`
                  }
                  className="w-full h-10 bg-surface-2 rounded-pill pl-4 pr-11 text-sm text-ink placeholder:text-ink-3/80 border border-transparent focus:border-accent-text focus:outline-none transition-colors"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  aria-label="Send message"
                  className="absolute right-1.5 p-2 bg-accent text-accent-ink rounded-pill transition-colors hover:bg-accent-hover disabled:opacity-40"
                >
                  <Send className="w-3.5 h-3.5" />
                </button>
              </form>

              {/* Explicit engine specification in the text input box container */}
              <div className="flex items-center justify-between px-1 text-[11px] text-ink-3">
                <span className="flex items-center gap-1.5">
                  <span className={`w-1.5 h-1.5 rounded-full ${aiMode === "ollama" ? "bg-emerald-500 animate-pulse" : "bg-sky-500 animate-pulse"}`} />
                  <span>
                    Routing: <strong className="text-ink font-medium">{aiMode === "ollama" ? "Ollama (Local)" : "Groq (Cloud)"}</strong>
                  </span>
                </span>
                {lastAnswerEngine && (
                  <span className="text-[10px] font-mono text-ink-3 bg-surface-2 px-1.5 py-0.5 rounded border border-line/20">
                    Answered by: <strong className="text-ink-2">{lastAnswerEngine}</strong>
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.button
        whileHover={reduced ? undefined : { scale: 1.05 }}
        whileTap={reduced ? undefined : { scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? "Close assistant" : "Open assistant"}
        className="w-13 h-13 bg-ink text-bg rounded-pill flex items-center justify-center shadow-card"
      >
        {isOpen ? <X className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
      </motion.button>
    </div>
  );
}
