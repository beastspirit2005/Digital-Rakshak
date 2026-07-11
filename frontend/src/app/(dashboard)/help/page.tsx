"use client";

import { api } from "@/lib/api";
import { useEffect, useState, useRef } from "react";
import axios from "axios";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/lib/auth-store";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea, Label } from "@/components/ui/field";
import { LifeBuoy, CheckCircle2, MessageSquare, Send, ArrowLeft, Settings2, StopCircle } from "lucide-react";
import { Rise } from "@/components/ui/motion";
import { ChatBubble, ChatMessage, TypingIndicator } from "@/components/ui/chat-bubble";

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
           
           // Default to first recommended or mistral
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

  // Connect Supabase Realtime
  useEffect(() => {
    if (!user) return;
    
    // Initial greeting
    setMessages([
      { id: "msg-0", type: "ai", content: `Hello ${user?.full_name?.split(' ')[0] || "Citizen"}! I'm the Digital Rakshak AI Support Agent. How can I assist you today?`, timestamp: new Date() }
    ]);

    console.log("[HelpChat] Subscribing to Supabase Realtime for session:", user.id);
    const channel = supabase
      .channel(`help_chat_${user.id}`)
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'help_messages', filter: `session_id=eq.${user.id}` },
        (payload) => {
          const msg = payload.new as any;
          setIsAiTyping(false);
          
          // We optimistically render user messages, so ignore them here
          if (msg.role === "user") return;
          
          let type: any = "ai";
          if (msg.role === "system") type = "system";
          if (msg.role === "admin") type = "admin";
          
          setMessages(prev => [...prev, { id: msg.id, type, content: msg.content, timestamp: new Date(msg.created_at) }]);
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user]);


  const sendChatMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || !user) return;
    
    const content = inputMsg;
    setInputMsg("");
    setIsAiTyping(true);
    
    const newUserMsg = { id: crypto.randomUUID(), type: "user" as const, content, timestamp: new Date() };
    setMessages(prev => [...prev, newUserMsg]);
    
    try {
      await axios.post(api("/help/chat"), {
         session_id: user.id,
         message: content,
         role: user.role,
         model: forceLocal ? selectedModel : undefined
      }, { headers: { Authorization: `Bearer ${token}` } });
    } catch (e) {
      console.error(e);
      setIsAiTyping(false);
      setMessages(prev => [...prev, { id: crypto.randomUUID(), type: "system", content: "Failed to send message.", timestamp: new Date() }]);
    }
  };

  const requestHuman = async () => {
    if (!user) return;
    setMessages(prev => [...prev, { id: Date.now().toString(), type: "user", content: "I need to talk to a human.", timestamp: new Date() }]);
    try {
      await axios.post(api("/help/escalate"), { session_id: user.id, client_id: user.id }, { headers: { Authorization: `Bearer ${token}` } });
    } catch (e) {
      console.error(e);
    }
  };

  const stopChat = () => {
    // Streaming not natively supported via simple Realtime fallback without abort controllers on backend,
    // so just hide typing indicator and let background task finish.
    setIsAiTyping(false);
  };

  // Ticket fetching
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

  useEffect(() => {
    if (token) fetchTickets();
  }, [token, view]);

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
      alert("Ticket submitted successfully!");
      fetchTickets();
    } catch (err) {
      console.error(err);
      alert("Failed to submit ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pt-2 max-w-4xl mx-auto h-[calc(100vh-80px)] flex flex-col">
      <Rise>
        <PageHeader
          title="Help & Support"
          sub="Chat with our AI agent instantly, or escalate to a human admin."
        />
      </Rise>

      <div className="flex gap-4 mb-4">
        <Button variant={view === "chat" ? "primary" : "secondary"} onClick={() => setView("chat")}>
          <MessageSquare className="w-4 h-4 mr-2" /> Live Chat
        </Button>
        <Button variant={view === "tickets" ? "primary" : "secondary"} onClick={() => setView("tickets")}>
          <LifeBuoy className="w-4 h-4 mr-2" /> Support Tickets
        </Button>
      </div>

      {view === "chat" ? (
        <Rise index={1} className="flex-1 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col overflow-hidden bg-surface shadow-md border border-line rounded-3xl">
            {/* Header / Local Model Selector */}
            {forceLocal && (
               <div className="px-6 py-3 border-b border-line bg-surface flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-ink-2 font-medium">
                     <Settings2 className="w-4 h-4 text-accent" /> Local Mode Active
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                     <span className="text-ink-3">AI Model:</span>
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
               </div>
            )}
            
            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-6 bg-surface/50">
              {messages.map((msg) => (
                <ChatBubble key={msg.id} message={msg} />
              ))}
              {isAiTyping && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>
            
            {/* Chat Input */}
            <div className="p-4 bg-surface border-t border-line">
              <div className="flex gap-2 items-center mb-2 px-2">
                 <button onClick={requestHuman} className="text-xs font-medium text-accent hover:underline flex items-center">
                   <LifeBuoy className="w-3 h-3 mr-1" /> Request Human Agent
                 </button>
                 {isAiTyping && (
                   <button onClick={stopChat} className="text-xs font-medium text-red-500 hover:underline flex items-center ml-4">
                     <StopCircle className="w-3 h-3 mr-1" /> Stop Generating
                   </button>
                 )}
              </div>
              <form onSubmit={sendChatMessage} className="flex gap-3">
                <Input
                  className="flex-1 rounded-full px-6 bg-surface-2 border-transparent focus-visible:ring-primary/30"
                  placeholder="Type your message..."
                  value={inputMsg}
                  onChange={(e) => setInputMsg(e.target.value)}
                />
                <Button type="submit" variant="primary" className="rounded-full aspect-square p-0 w-12 flex items-center justify-center" disabled={!inputMsg.trim() || isAiTyping}>
                  <Send className="w-5 h-5 -ml-1" />
                </Button>
              </form>
            </div>
          </Card>
        </Rise>
      ) : (
        <Rise index={1} className="overflow-y-auto pb-10">
          <Card className="p-6 mb-8">
            <form onSubmit={handleTicketSubmit} className="space-y-4">
              <h3 className="font-semibold text-ink text-lg flex items-center gap-2">
                <LifeBuoy className="w-5 h-5 text-accent-text" /> Create a Support Ticket
              </h3>
              <div className="space-y-1">
                <Label htmlFor="subject">Subject</Label>
                <Input id="subject" value={subject} onChange={(e) => setSubject(e.target.value)} required placeholder="Brief summary of your issue" />
              </div>
              <div className="space-y-1">
                <Label htmlFor="message">Message</Label>
                <Textarea id="message" value={message} onChange={(e) => setMessage(e.target.value)} required rows={4} placeholder="Describe your issue in detail..." />
              </div>
              <Button type="submit" variant="primary" loading={submitting}>Submit Ticket</Button>
            </form>
          </Card>

          <h3 className="font-semibold text-ink text-lg mb-4">Your Recent Tickets</h3>
          {loading ? (
            <p className="text-ink-3">Loading tickets...</p>
          ) : tickets.length === 0 ? (
            <Card className="p-8 text-center text-ink-3">
              <CheckCircle2 className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p>You have no support tickets.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {tickets.map((t) => (
                <Card key={t.id} className="p-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-ink">{t.subject}</h4>
                    <span className="text-xs px-2 py-1 rounded-full bg-surface-2 text-ink-2 font-medium border border-line">{t.status}</span>
                  </div>
                  <p className="text-sm text-ink-3 mt-1 tabular-nums font-mono">{t.ticket_number} • {new Date(t.created_at).toLocaleString()}</p>
                  <p className="text-sm text-ink-2 mt-3 p-3 bg-surface-2 rounded-control border border-line whitespace-pre-wrap">{t.message}</p>
                </Card>
              ))}
            </div>
          )}
        </Rise>
      )}
    </div>
  );
}
