"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";
import axios from "axios";
import { Send, Bot, User, Trash2, X, Cpu } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export function GlobalChatWidget() {
  const { user } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiMode, setAiMode] = useState("groq");
  const [caseId, setCaseId] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history
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

  // Save chat history
  useEffect(() => {
    if (user?.id && messages.length > 0) {
      localStorage.setItem(`rakshak_chat_${user.id}`, JSON.stringify(messages));
    }
  }, [messages, user]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

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
      timestamp: Date.now()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(api("/chat/global"), {
        query: userMsg.content,
        ai_mode: aiMode,
        case_id: caseId || undefined
      });

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.data.reply,
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to communicate with AI Core.";
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `**Error:** ${errorMsg}`,
        timestamp: Date.now()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Only render if logged in
  if (!user) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      <AnimatePresence>
        {isOpen && (
          <motion.div 
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="mb-4 w-[400px] h-[600px] max-h-[80vh] max-w-[calc(100vw-3rem)] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 flex flex-col overflow-hidden"
          >
            {/* Chat Header */}
            <div className="bg-slate-900 text-white p-4 flex flex-col gap-3 shrink-0">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-indigo-400" />
                  <span className="font-semibold text-sm">Rakshak Global Assistant</span>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={handleClearChat} className="p-1.5 hover:bg-slate-800 rounded-md transition-colors" title="Clear Chat">
                    <Trash2 className="w-4 h-4 text-slate-400 hover:text-red-400" />
                  </button>
                  <button onClick={() => setIsOpen(false)} className="p-1.5 hover:bg-slate-800 rounded-md transition-colors">
                    <X className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
              </div>
              
              {/* Settings Row */}
              <div className="flex items-center gap-2 text-xs">
                <select 
                  value={aiMode}
                  onChange={(e) => setAiMode(e.target.value)}
                  className="bg-slate-800 border border-slate-700 rounded py-1 px-2 text-slate-300 focus:outline-none focus:border-indigo-500 w-full"
                >
                  <option value="groq">Groq (LPU Fast)</option>
                  <option value="cloud">Gemini (Cloud)</option>
                  <option value="local">Ollama (Local)</option>
                </select>
                {user.role === "admin" && (
                  <input 
                    type="text" 
                    value={caseId}
                    onChange={(e) => setCaseId(e.target.value)}
                    placeholder="Case ID (Opt)"
                    className="bg-slate-800 border border-slate-700 rounded py-1 px-2 text-slate-300 focus:outline-none focus:border-indigo-500 w-full placeholder:text-slate-500"
                  />
                )}
              </div>
            </div>

            {/* Chat Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50 dark:bg-slate-900/50">
              {messages.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3 opacity-70">
                  <Cpu className="w-10 h-10 text-indigo-400" />
                  <p className="text-xs text-center px-4">
                    I am aware of your role as a {user.role}. Ask me anything about the platform or your cases.
                  </p>
                </div>
              ) : (
                messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center shrink-0 mt-1">
                        <Bot className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                      </div>
                    )}
                    
                    <div className={`text-sm max-w-[85%] rounded-2xl px-4 py-2.5 ${
                      msg.role === 'user' 
                        ? 'bg-indigo-600 text-white rounded-br-none' 
                        : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-none shadow-sm border border-slate-100 dark:border-slate-700/50'
                    }`}>
                      {msg.role === 'user' ? (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-snug prose-pre:bg-slate-900 prose-pre:p-2">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                      )}
                    </div>
                  </div>
                ))
              )}
              
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-7 h-7 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4 text-indigo-600 dark:text-indigo-400 animate-pulse" />
                  </div>
                  <div className="bg-white dark:bg-slate-800 rounded-2xl rounded-bl-none px-4 py-3 flex items-center gap-1.5 shadow-sm border border-slate-100 dark:border-slate-700/50">
                    <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce"></div>
                    <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Footer */}
            <div className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
              <form onSubmit={handleSend} className="relative flex items-center">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask a question..."
                  className="w-full bg-slate-100 dark:bg-slate-800 border-0 rounded-full py-2.5 pl-4 pr-12 text-sm focus:ring-2 focus:ring-indigo-500 dark:text-white"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={!input.trim() || isLoading}
                  className="absolute right-1.5 p-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:dark:bg-slate-700 text-white rounded-full transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Toggle Button */}
      <motion.button
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        onClick={() => setIsOpen(!isOpen)}
        className="w-14 h-14 bg-indigo-600 text-white rounded-full flex items-center justify-center shadow-2xl hover:bg-indigo-700 transition-colors border-4 border-white dark:border-slate-900 relative group"
      >
        {isOpen ? <X className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
        {!isOpen && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500 border-2 border-white dark:border-slate-900"></span>
          </span>
        )}
      </motion.button>
    </div>
  );
}
