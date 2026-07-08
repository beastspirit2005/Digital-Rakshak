"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";
import axios from "axios";
import { Send, Bot, Trash2, X } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export function GlobalChatWidget() {
  const { user, token } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiMode, setAiMode] = useState("groq");
  const [caseId, setCaseId] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion();

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

    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(
        api("/cases/global"),
        {
          query: userMsg.content,
          ai_mode: aiMode,
          case_id: caseId || undefined,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.data.reply,
        timestamp: Date.now(),
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
                  <option value="groq">Groq — fast cloud</option>
                  <option value="cloud">Gemini — cloud</option>
                  <option value="local">Ollama — local</option>
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

            {/* body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center gap-2">
                  <Bot className="w-8 h-8 text-ink-3" />
                  <p className="text-xs text-ink-2 max-w-[15rem]">
                    Ask about your cases, the platform, or what to do next. The assistant knows
                    you're signed in as a {user.role.replace(/_/g, " ")}.
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
                        <div className="chat-markdown [&_p]:leading-snug [&_p+p]:mt-2 [&_pre]:bg-surface [&_pre]:p-2 [&_pre]:rounded-control [&_pre]:text-xs [&_code]:text-xs [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4 [&_a]:underline">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
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
            <div className="p-3 border-t border-line">
              <form onSubmit={handleSend} className="relative flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question"
                  className="w-full h-10 bg-surface-2 rounded-pill pl-4 pr-11 text-sm text-ink placeholder:text-ink-3 border border-transparent focus:border-accent-text focus:outline-none transition-colors"
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
