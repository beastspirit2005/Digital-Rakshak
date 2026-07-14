"use client";

import { api } from "@/lib/api";
import { useEffect, useState, useRef } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Label } from "@/components/ui/field";
import { LifeBuoy, CheckCircle2, MessageSquare, Send, Settings2, StopCircle, ArrowLeft } from "lucide-react";
import { Rise } from "@/components/ui/motion";
import { ChatBubble, ChatMessage, TypingIndicator } from "@/components/ui/chat-bubble";
import { useToast } from "@/components/ui/toast";

export default function HelpPage() {
  const [view, setView] = useState<"chat" | "tickets">("chat");
  const { token, user } = useAuthStore();
  
  // --- Chat Settings State ---
  const [forceLocal, setForceLocal] = useState(false);
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("mistral");

  // --- Chat State ---
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMsg, setInputMsg] = useState("");
  const [isAiTyping, setIsAiTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // --- Ticket State ---
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const pushToast = useToast();

  // Fetch Chat Settings & Models
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const config = { headers: { Authorization: `Bearer ${token}` } };
        const settingsRes = await axios.get(api("/help/chat-settings"), config);
        const isLocal = settingsRes.data.force_local_inference;
        setForceLocal(isLocal);
        
        if (isLocal) {
           const modelsRes = await axios.get(api("/agents/models"), config);
           const ollamaModels = modelsRes.data.models.filter((m: any) => m.provider === "ollama");
           setAvailableModels(ollamaModels);
           
           const recommended = ollamaModels.find((m:any) => m.is_recommended);
           if (recommended) setSelectedModel(recommended.id.replace('ollama:', ''));
           else if (ollamaModels.length > 0) setSelectedModel(ollamaModels[0].id.replace('ollama:', ''));
        }
      } catch (e) {
        console.error("Failed to load chat settings", e);
      }
    };
    fetchSettings();
  }, [token]);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isAiTyping]);

  // Poll for Messages
  const fetchMessages = async () => {
    if (!token || !user) return;
    try {
      const res = await axios.get(api(`/help/messages/${user.id}`), {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const dbMsgs: ChatMessage[] = (res.data.messages || []).map((m: any) => ({
        id: m.id,
        type: m.role === "admin" ? "admin" : m.role === "system" ? "system" : m.role === "user" ? "user" : "ai",
        content: m.content,
        timestamp: new Date(m.created_at)
      }));

      // Content-based deduplication
      if (dbMsgs.length > 0) {
        setMessages(prev => {
          const dbContents = new Set(dbMsgs.map((m: any) => m.content.trim()));
          const localOnly = prev.filter(p => p.id.toString().startsWith('temp-') && !dbContents.has(p.content.trim()));
          
          const greeting: ChatMessage = { id: "msg-0", type: "ai", content: `Hello ${user?.full_name?.split(' ')[0] || "Citizen"}! I'm the Digital Rakshak AI Support Agent. How can I assist you today?`, timestamp: new Date(0) };
          
          return [greeting, ...dbMsgs, ...localOnly];
        });
        setIsAiTyping(false);
      }
    } catch (err) {
      // Silently ignore
    }
  };

  // Unified Polling Interval
  useEffect(() => {
    if (!user || !token) return;
    
    // Initial greeting
    setMessages([
      { id: "msg-0", type: "ai", content: `Hello ${user?.full_name?.split(' ')[0] || "Citizen"}! I'm the Digital Rakshak AI Support Agent. How can I assist you today?`, timestamp: new Date() }
    ]);

    const loadInitial = async () => {
        await Promise.all([
            fetchMessages(),
            fetchTickets()
        ]);
    };
    loadInitial();

    const pollInterval = setInterval(async () => {
        try {
            await Promise.all([
                fetchMessages(),
                view === "tickets" ? fetchTickets() : Promise.resolve()
            ]);
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 3000);
    
    return () => clearInterval(pollInterval);
  }, [user, token, view]);

  const sendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || !user) return;
    
    const content = inputMsg;
    setInputMsg("");
    setIsAiTyping(true);
    
    const newUserMsg: ChatMessage = { id: `temp-${crypto.randomUUID()}`, type: "user", content, timestamp: new Date() };
    setMessages(prev => [...prev, newUserMsg]);
    
    try {
      const res = await axios.post(api("/help/chat"), {
         session_id: user.id,
         message: content,
         role: user.role,
         model: forceLocal ? selectedModel : undefined
      }, { headers: { Authorization: `Bearer ${token}` } });
      
      const reply = res.data.reply;
      setIsAiTyping(false);
      
      // We rely on polling to fetch the AI reply. However, we immediately fetch it to reduce latency.
      await fetchMessages();
      
    } catch (e) {
      console.error(e);
      setIsAiTyping(false);
      setMessages(prev => [...prev, { id: `temp-${crypto.randomUUID()}`, type: "system", content: "Failed to send message.", timestamp: new Date() }]);
    }
  };

  const requestHuman = async () => {
    if (!user) return;
    setMessages(prev => [...prev, { id: `temp-${Date.now()}`, type: "user", content: "I need to talk to a human.", timestamp: new Date() }]);
    try {
      await axios.post(api("/help/escalate"), { session_id: user.id, client_id: user.id }, { headers: { Authorization: `Bearer ${token}` } });
      await fetchMessages();
    } catch (e) {
      console.error(e);
    }
  };

  const stopChat = () => {
    setIsAiTyping(false);
  };

  const fetchTickets = async () => {
    try {
      const res = await axios.get(api("/support/tickets"), { headers: { Authorization: `Bearer ${token}` } });
      setTickets(res.data.tickets);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleTicketSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("subject", subject);
      formData.append("message", message);
      await axios.post(api("/support/ticket"), formData, { headers: { Authorization: `Bearer ${token}` } });
      setSubject("");
      setMessage("");
      pushToast("success", "Ticket submitted successfully!");
      fetchTickets();
    } catch (err) {
      console.error(err);
      pushToast("danger", "Failed to submit ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-80px)] overflow-hidden">
      {/* Left Sidebar Menu */}
      <div className="w-64 border-r border-line bg-surface/50 p-4 flex flex-col space-y-2">
         <h2 className="text-xl font-bold text-ink mb-4 px-2">Support</h2>
         <Button 
            variant={view === "chat" ? "primary" : "ghost"} 
            className="w-full justify-start py-6 rounded-xl"
            onClick={() => setView("chat")}
         >
            <MessageSquare className="w-5 h-5 mr-3" /> Live Chat
         </Button>
         <Button 
            variant={view === "tickets" ? "primary" : "ghost"} 
            className="w-full justify-start py-6 rounded-xl"
            onClick={() => setView("tickets")}
         >
            <LifeBuoy className="w-5 h-5 mr-3" /> Support Tickets
         </Button>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col bg-surface relative">
        {view === "chat" ? (
          <Rise className="flex-1 flex flex-col min-h-0 absolute inset-0">
            {/* Chat Header */}
            <div className="px-6 py-4 border-b border-line bg-surface/80 backdrop-blur-md flex items-center justify-between z-10">
               <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                     <LifeBuoy className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                     <h3 className="font-semibold text-ink leading-tight">Digital Rakshak Support</h3>
                     <p className="text-xs text-ink-3 font-medium flex items-center gap-1">
                        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                        AI Agent Online
                     </p>
                  </div>
               </div>

               {forceLocal && (
                  <div className="flex items-center gap-3 text-sm">
                     <span className="text-ink-3">Local Model:</span>
                     <select 
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="bg-surface-2 border border-line rounded-md px-3 py-1.5 text-ink outline-none focus:border-primary"
                     >
                       {availableModels.map(m => (
                         <option key={m.id} value={m.id.replace('ollama:', '')}>
                           {m.name} {m.is_recommended ? "(Recommended)" : ""}
                         </option>
                       ))}
                     </select>
                  </div>
               )}
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-6 bg-surface-2/30">
              <div className="max-w-3xl mx-auto flex flex-col">
                <div className="text-center py-6">
                   <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center mx-auto mb-4 rotate-3">
                      <LifeBuoy className="w-8 h-8 text-primary" />
                   </div>
                   <h2 className="text-lg font-bold text-ink">How can we help?</h2>
                   <p className="text-sm text-ink-2 mt-1">Chat with our AI or request human escalation below.</p>
                </div>
                
                {messages.map((msg) => (
                  <ChatBubble key={msg.id} message={msg} />
                ))}
                {isAiTyping && <TypingIndicator />}
                <div ref={messagesEndRef} className="h-4" />
              </div>
            </div>

            {/* Chat Input */}
            <div className="p-4 bg-surface border-t border-line">
              <div className="max-w-3xl mx-auto">
                 <div className="flex gap-4 items-center mb-3 px-2">
                    <button onClick={requestHuman} className="text-xs font-semibold text-ink-2 hover:text-ink transition-colors flex items-center px-3 py-1.5 bg-surface-2 rounded-full border border-line">
                      <LifeBuoy className="w-3.5 h-3.5 mr-1.5" /> Request Human Agent
                    </button>
                    {isAiTyping && (
                      <button onClick={stopChat} className="text-xs font-semibold text-red-500 hover:text-red-600 transition-colors flex items-center px-3 py-1.5 bg-red-50 rounded-full border border-red-100">
                        <StopCircle className="w-3.5 h-3.5 mr-1.5" /> Stop Generating
                      </button>
                    )}
                 </div>
                 <form onSubmit={sendChatMessage} className="flex gap-3">
                   <Input
                     className="flex-1 rounded-2xl py-6 px-6 bg-surface border-line shadow-sm focus-visible:ring-primary/20 text-base"
                     placeholder="Type your message here..."
                     value={inputMsg}
                     onChange={(e) => setInputMsg(e.target.value)}
                   />
                   <Button type="submit" variant="primary" className="rounded-2xl aspect-square p-0 w-14 flex items-center justify-center shadow-md transition-transform active:scale-95" disabled={!inputMsg.trim() || isAiTyping}>
                     <Send className="w-5 h-5 -ml-0.5" />
                   </Button>
                 </form>
              </div>
            </div>
          </Rise>
        ) : (
          <Rise className="flex-1 overflow-y-auto p-8 absolute inset-0">
            <div className="max-w-4xl mx-auto">
               <h2 className="text-2xl font-bold text-ink mb-6">Support Tickets</h2>
               <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="order-2 md:order-1 space-y-4">
                     {loading ? (
                        <p className="text-ink-3">Loading tickets...</p>
                     ) : tickets.length === 0 ? (
                        <Card className="p-8 text-center text-ink-3 rounded-3xl border-dashed">
                           <CheckCircle2 className="w-8 h-8 mx-auto mb-3 opacity-30" />
                           <p>You have no open tickets.</p>
                        </Card>
                     ) : (
                        tickets.map((t) => (
                           <Card key={t.id} className="p-5 rounded-3xl shadow-sm hover:shadow-md transition-shadow">
                           <div className="flex items-center justify-between">
                              <h4 className="font-semibold text-ink text-base">{t.subject}</h4>
                              <span className="text-xs px-2.5 py-1 rounded-full bg-surface-2 text-ink-2 font-medium border border-line">{t.status}</span>
                           </div>
                           <p className="text-xs text-ink-3 mt-1.5 font-medium">{t.ticket_number} • {new Date(t.created_at).toLocaleString()}</p>
                           <p className="text-sm text-ink-2 mt-4 p-4 bg-surface-2 rounded-2xl whitespace-pre-wrap">{t.message}</p>
                           {t.history && t.history.length > 0 ? (
                              <div className="mt-5 space-y-3">
                                 {t.history.map((msg: any, idx: number) => (
                                 <div key={idx} className={`p-4 rounded-2xl ${msg.sender === 'admin' ? 'bg-primary/5 text-primary-text mr-8' : 'bg-surface border border-line ml-8'}`}>
                                    <p className={`text-[10px] font-bold uppercase tracking-wider mb-1.5 ${msg.sender === 'admin' ? 'text-primary' : 'text-ink-3'}`}>
                                       {msg.sender === 'admin' ? 'Admin' : 'You'}
                                    </p>
                                    <p className="text-sm font-medium">{msg.message}</p>
                                 </div>
                                 ))}
                              </div>
                           ) : t.admin_reply ? (
                              <div className="mt-4 p-4 bg-primary/5 rounded-2xl mr-8">
                                 <p className="text-[10px] font-bold uppercase tracking-wider text-primary mb-1.5">Admin Reply</p>
                                 <p className="text-sm text-primary-text font-medium">{t.admin_reply}</p>
                              </div>
                           ) : null}
                           </Card>
                        ))
                     )}
                  </div>
                  
                  <div className="order-1 md:order-2">
                     <Card className="p-6 rounded-3xl sticky top-8 bg-surface-2 border-transparent">
                        <form onSubmit={handleTicketSubmit} className="space-y-5">
                           <div className="mb-2">
                              <h3 className="font-bold text-ink text-lg">Create a Ticket</h3>
                              <p className="text-sm text-ink-2">We typically reply within 2 hours.</p>
                           </div>
                           <div className="space-y-1.5">
                              <Label htmlFor="subject" className="text-ink font-semibold ml-1">Subject</Label>
                              <Input id="subject" className="rounded-xl bg-surface" value={subject} onChange={(e) => setSubject(e.target.value)} required placeholder="Brief summary" />
                           </div>
                           <div className="space-y-1.5">
                              <Label htmlFor="message" className="text-ink font-semibold ml-1">Message</Label>
                              <Textarea id="message" className="rounded-xl bg-surface resize-none" value={message} onChange={(e) => setMessage(e.target.value)} required rows={5} placeholder="Describe your issue..." />
                           </div>
                           <Button type="submit" variant="primary" className="w-full rounded-xl py-6" loading={submitting}>Submit Ticket</Button>
                        </form>
                     </Card>
                  </div>
               </div>
            </div>
          </Rise>
        )}
      </div>
    </div>
  );
}
