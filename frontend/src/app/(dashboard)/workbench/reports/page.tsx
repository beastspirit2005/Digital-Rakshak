"use client";


import { api } from "@/lib/api";
import React, { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/auth-store";
import axios from "axios";
import { Loader2, Search, Filter, FileText, ChevronDown, ChevronUp, AlertTriangle, Shield } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

export default function ReportsRegisterPage() {
  const [cases, setCases] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [chatQuery, setChatQuery] = useState("");
  const [chatHistory, setChatHistory] = useState<{role: string, text: string}[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchAllCases = async () => {
      try {
        const res = await axios.get(api("/cases/?limit=500"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setCases(res.data.cases);
      } catch (err) {
        console.error("Failed to load cases", err);
      } finally {
        setLoading(false);
      }
    };
    if (token) fetchAllCases();
  }, [token]);

  const handleChatSubmit = async (e: React.FormEvent, caseId: string) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    const userMessage = chatQuery.trim();
    setChatHistory(prev => [...prev, { role: "user", text: userMessage }]);
    setChatQuery("");
    setChatLoading(true);

    try {
      const res = await axios.post(api(`/cases/${caseId}/chat`), 
        { query: userMessage },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setChatHistory(prev => [...prev, { role: "ai", text: res.data.reply }]);
    } catch (err) {
      console.error("Chat failed", err);
      setChatHistory(prev => [...prev, { role: "ai", text: "Error: Could not reach the Co-Pilot." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch(priority?.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'medium': return 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20';
      default: return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  };

  const getStatusColor = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'under_review': return 'text-orange-500 border-orange-500/30 bg-orange-500/10';
      case 'investigating': return 'text-blue-500 border-blue-500/30 bg-blue-500/10';
      case 'resolved': return 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10';
      default: return 'text-gray-500 border-gray-500/30 bg-gray-500/10';
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">FIR / TPR Register</h1>
          <p className="text-muted-foreground mt-1">Comprehensive log of all threat reports and their AI analysis.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input 
              type="text" 
              placeholder="Search case ID or type..." 
              className="pl-9 pr-4 py-2 rounded-xl bg-background border border-border focus:ring-2 focus:ring-primary/20 outline-none text-sm w-64"
            />
          </div>
          <button className="p-2 border border-border bg-background rounded-xl hover:bg-muted transition-colors flex items-center gap-2 text-sm font-medium">
            <Filter className="w-4 h-4" /> Filter
          </button>
        </div>
      </div>

      <div className="glass-panel rounded-2xl border border-border overflow-hidden">
        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center text-muted-foreground">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-primary" />
            <p>Loading case register...</p>
          </div>
        ) : cases.length === 0 ? (
          <div className="p-12 text-center text-muted-foreground">
            <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>No reports found in the database.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-muted-foreground uppercase bg-muted/50 border-b border-border">
                <tr>
                  <th className="px-6 py-4 font-medium">Case Number</th>
                  <th className="px-6 py-4 font-medium">Date & Time</th>
                  <th className="px-6 py-4 font-medium">Scam Type</th>
                  <th className="px-6 py-4 font-medium">Location</th>
                  <th className="px-6 py-4 font-medium">AI Score</th>
                  <th className="px-6 py-4 font-medium">Priority</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {cases.map((c) => (
                  <React.Fragment key={c.id}>
                    <tr 
                      className={`hover:bg-muted/30 transition-colors cursor-pointer ${expandedId === c.id ? 'bg-muted/30' : ''}`}
                      onClick={() => {
                        setExpandedId(expandedId === c.id ? null : c.id);
                        setChatHistory([]);
                        setChatQuery("");
                      }}
                    >
                      <td className="px-6 py-4 font-medium text-primary">{c.case_number}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-muted-foreground">
                        {new Date(c.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="px-6 py-4">{c.scam_type_code || "Unknown"}</td>
                      <td className="px-6 py-4 text-muted-foreground">
                        {c.city ? `${c.city}${c.state ? `, ${c.state}` : ''}` : "Unknown"}
                      </td>
                      <td className="px-6 py-4 font-mono font-medium">
                        {(c.threat_confidence_score * 100).toFixed(1)}%
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-md text-xs font-medium border capitalize ${getPriorityColor(c.priority)}`}>
                          {c.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-xs font-medium border capitalize ${getStatusColor(c.status)}`}>
                          {c.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        {expandedId === c.id ? <ChevronUp className="w-5 h-5 inline text-muted-foreground" /> : <ChevronDown className="w-5 h-5 inline text-muted-foreground" />}
                      </td>
                    </tr>
                    
                    <AnimatePresence>
                      {expandedId === c.id && (
                        <tr>
                          <td colSpan={8} className="p-0 border-b border-border bg-card/30">
                            <motion.div 
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              className="overflow-hidden"
                            >
                              <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
                                <div className="lg:col-span-2 space-y-4">
                                  <div>
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Original Report Text</h4>
                                    <p className="bg-background p-4 rounded-xl text-sm border border-border whitespace-pre-wrap">
                                      {c.scam_text}
                                    </p>
                                  </div>
                                  
                                  {c.ai_decision?.evidence && c.ai_decision.evidence.length > 0 && (
                                    <div>
                                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI Extracted Evidence</h4>
                                      <ul className="space-y-2">
                                        {c.ai_decision.evidence.map((ev: any, idx: number) => (
                                          <li key={idx} className="bg-primary/5 text-primary text-sm px-3 py-2 rounded-lg border border-primary/10 flex items-start gap-2">
                                            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                                            {ev.relevance || JSON.stringify(ev)}
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                                
                                <div className="space-y-4">
                                  <div className="bg-background p-4 rounded-xl border border-border">
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">AI Intelligence Summary</h4>
                                    
                                    <div className="space-y-3 text-sm">
                                      <div>
                                        <span className="text-muted-foreground">Threat Decision:</span>
                                        <p className="font-medium text-red-500 mt-0.5">{c.ai_decision?.decision || "N/A"}</p>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Models Used:</span>
                                        <div className="flex gap-2 mt-1">
                                          {(c.ai_decision?.models_used || []).map((m: string) => (
                                            <span key={m} className="px-2 py-0.5 rounded bg-muted text-xs capitalize">{m}</span>
                                          ))}
                                        </div>
                                      </div>
                                      <div>
                                        <span className="text-muted-foreground">Inference Latency:</span>
                                        <p className="font-mono mt-0.5">{c.ai_decision?.inference_time_ms || 0}ms</p>
                                      </div>
                                    </div>
                                  </div>

                                  {c.ai_decision?.ztivf_metrics && (
                                    <div className="bg-indigo-500/10 p-4 rounded-xl border border-indigo-500/20">
                                      <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-3 flex items-center gap-2">
                                        <Shield className="w-4 h-4" /> Zero-Trust Metrics
                                      </h4>
                                      <div className="space-y-3 text-xs">
                                        {Object.entries(c.ai_decision.ztivf_metrics).map(([key, value]) => (
                                          <div key={key} className="space-y-1">
                                            <div className="flex justify-between text-muted-foreground capitalize">
                                              <span>{key.replace('_score', '')}</span>
                                              <span className="font-medium text-foreground">{((value as number) * 100).toFixed(0)}%</span>
                                            </div>
                                            <div className="h-1.5 w-full bg-background rounded-full overflow-hidden">
                                              <div 
                                                className={`h-full rounded-full ${
                                                  (value as number) > 0.8 ? 'bg-emerald-500' : 
                                                  (value as number) > 0.5 ? 'bg-amber-500' : 'bg-red-500'
                                                }`} 
                                                style={{ width: `${(value as number) * 100}%` }}
                                              />
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                  )}

                                  {c.ai_decision?.raw_explanation && (
                                    <div className="bg-muted/30 p-4 rounded-xl border border-border">
                                      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI Reasoning</h4>
                                      <p className="text-sm text-foreground/90 leading-relaxed">
                                        {c.ai_decision.raw_explanation}
                                      </p>
                                    </div>
                                  )}

                                  {/* AI Co-Pilot Chat Interface */}
                                  <div className="bg-background p-4 rounded-xl border border-border flex flex-col h-64">
                                    <h4 className="text-xs font-semibold uppercase tracking-wider text-primary flex items-center gap-2 mb-3">
                                      <Search className="w-4 h-4" /> Investigation Co-Pilot
                                    </h4>
                                    
                                    <div className="flex-1 overflow-y-auto mb-3 space-y-3 pr-2 text-sm">
                                      {chatHistory.length === 0 ? (
                                        <div className="text-muted-foreground text-center mt-4">
                                          Ask the AI about the evidence in this case.
                                        </div>
                                      ) : (
                                        chatHistory.map((msg, i) => (
                                          <div key={i} className={`p-3 rounded-lg ${msg.role === 'user' ? 'bg-muted ml-4 text-right' : 'bg-primary/10 border border-primary/20 mr-4'}`}>
                                            <span className="font-bold text-xs opacity-50 block mb-1 uppercase">{msg.role}</span>
                                            {msg.text}
                                          </div>
                                        ))
                                      )}
                                      {chatLoading && (
                                        <div className="text-primary text-xs animate-pulse">Co-Pilot is typing...</div>
                                      )}
                                    </div>

                                    <form onSubmit={(e) => handleChatSubmit(e, c.id)} className="flex gap-2">
                                      <input 
                                        type="text" 
                                        value={chatQuery}
                                        onChange={(e) => setChatQuery(e.target.value)}
                                        placeholder="Ask a question..."
                                        className="flex-1 px-3 py-2 bg-muted border-transparent rounded-lg text-sm outline-none focus:ring-1 focus:ring-primary"
                                        disabled={chatLoading}
                                      />
                                      <button type="submit" disabled={chatLoading} className="px-3 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50">
                                        Send
                                      </button>
                                    </form>
                                  </div>
                                </div>
                              </div>
                            </motion.div>
                          </td>
                        </tr>
                      )}
                    </AnimatePresence>
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
