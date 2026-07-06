"use client";

import { useState, useEffect, useRef } from "react";
import { useAuthStore } from "@/lib/auth-store";
import { api } from "@/lib/api";
import axios from "axios";
import { Send, Bot, User, Trash2, ShieldAlert, Cpu } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export default function GlobalChatPage() {
  const { user } = useAuthStore();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [aiMode, setAiMode] = useState("groq");
  const [caseId, setCaseId] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load chat history from localStorage
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

  // Save chat history to localStorage
  useEffect(() => {
    if (user?.id && messages.length > 0) {
      localStorage.setItem(`rakshak_chat_${user.id}`, JSON.stringify(messages));
    }
  }, [messages, user]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

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
      const errorMsg = err.response?.data?.detail || "Failed to communicate with AI Core. Check your connection.";
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

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-slate-50 dark:bg-slate-900 rounded-xl overflow-hidden shadow-lg border border-slate-200 dark:border-slate-800">
      
      {/* Sidebar - GoalForge Style */}
      <div className="w-64 bg-slate-900 text-slate-300 p-4 flex flex-col border-r border-slate-800 shrink-0">
        <div className="flex items-center gap-2 font-semibold text-white mb-6">
          <Bot className="w-5 h-5 text-indigo-400" />
          <span>Rakshak Chat</span>
        </div>
        
        <button 
          onClick={handleClearChat}
          className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg font-medium transition-colors mb-6 text-sm flex items-center justify-center gap-2"
        >
          <Trash2 className="w-4 h-4" />
          New Chat
        </button>

        <div className="space-y-4 flex-1 overflow-y-auto">
          <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
            Configuration
          </div>
          
          <div className="space-y-1">
            <label className="text-xs text-slate-400">AI Model (Inference)</label>
            <select 
              value={aiMode}
              onChange={(e) => setAiMode(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-md py-1.5 px-2 text-sm text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="groq">Groq (LPU Ultra-Fast)</option>
              <option value="cloud">Gemini 2.0 (Cloud)</option>
              <option value="local">Ollama (Local Privacy)</option>
            </select>
          </div>

          {user?.role === "admin" && (
            <div className="space-y-1 pt-2">
              <label className="text-xs text-slate-400">Target Case ID (Optional)</label>
              <input 
                type="text" 
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                placeholder="CAS-1234..."
                className="w-full bg-slate-800 border border-slate-700 rounded-md py-1.5 px-2 text-sm text-white focus:outline-none focus:border-indigo-500 placeholder:text-slate-600"
              />
            </div>
          )}
        </div>
        
        <div className="pt-4 border-t border-slate-800 text-xs text-slate-500 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4" />
          Secure & Encrypted
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white dark:bg-slate-900 relative">
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
              <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center">
                <Cpu className="w-8 h-8 text-indigo-500" />
              </div>
              <h2 className="text-xl font-medium text-slate-700 dark:text-slate-300">How can I assist you today?</h2>
              <p className="text-sm max-w-md text-center text-slate-500">
                I am your role-aware intelligence assistant. I have secure access to your cases and platform telemetry based on your authorization level.
              </p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                )}
                
                <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                  msg.role === 'user' 
                    ? 'bg-indigo-600 text-white rounded-br-none' 
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-bl-none shadow-sm'
                }`}>
                  {msg.role === 'user' ? (
                    <div className="text-sm whitespace-pre-wrap">{msg.content}</div>
                  ) : (
                    <div className="prose prose-sm dark:prose-invert max-w-none">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
                
                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center shrink-0">
                    <User className="w-5 h-5 text-slate-500 dark:text-slate-400" />
                  </div>
                )}
              </div>
            ))
          )}
          
          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-full bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center shrink-0">
                <Bot className="w-5 h-5 text-indigo-600 dark:text-indigo-400 animate-pulse" />
              </div>
              <div className="bg-slate-100 dark:bg-slate-800 rounded-2xl rounded-bl-none px-5 py-4 flex items-center gap-1 shadow-sm">
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
          <form onSubmit={handleSend} className="max-w-4xl mx-auto relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask the Rakshak AI..."
              className="w-full bg-slate-100 dark:bg-slate-800 border-0 rounded-full py-4 pl-6 pr-14 text-sm focus:ring-2 focus:ring-indigo-500 dark:text-white"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="absolute right-2 p-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:dark:bg-slate-700 text-white rounded-full transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
          <div className="text-center mt-2 text-[10px] text-slate-400">
            AI can make mistakes. Verify critical investigative details independently.
          </div>
        </div>
      </div>
    </div>
  );
}
