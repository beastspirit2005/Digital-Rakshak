"use client";

import { api } from "@/lib/api";
import { useEffect, useState, useRef, useCallback } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input, Textarea } from "@/components/ui/field";
import { MessageSquare, Mail, CheckCircle, Send, Users, AlertCircle, RefreshCw, UserCircle, Clock, FileText, ChevronRight } from "lucide-react";
import { Rise } from "@/components/ui/motion";
import { ChatBubble, ChatMessage } from "@/components/ui/chat-bubble";
import { useToast } from "@/components/ui/toast";

export default function AdminSupportPage() {
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { token, user } = useAuthStore();
  const pushToast = useToast();
  
  // View State
  const [activeTab, setActiveTab] = useState<"live" | "async">("live");
  
  // Chat State
  const [escalatedSessions, setEscalatedSessions] = useState<any[]>([]);
  const [activeChats, setActiveChats] = useState<{ [clientId: string]: ChatMessage[] }>({});
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [currentTicketId, setCurrentTicketId] = useState<string | null>(null);
  const [inputMsg, setInputMsg] = useState("");
  const [ticketReply, setTicketReply] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchTickets = async () => {
    try {
      const res = await axios.get(api("/support/tickets"), {
        headers: { Authorization: `Bearer ${token}` }
      });
      // Filter out tickets that are just LIVE_CHAT proxies if we want, 
      // but the original system keeps them as async tickets. Let's just show them.
      setTickets(res.data.tickets || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchSessions = useCallback(async () => {
    if (!token) return;
    try {
      const res = await axios.get(api("/help/admin/sessions"), {
        headers: { Authorization: `Bearer ${token}` }
      });
      setEscalatedSessions(res.data.sessions || []);
    } catch (err) {
      // Silently ignore polling errors
    }
  }, [token]);

  const fetchMessages = useCallback(async () => {
    if (!token || !currentChatId) return;
    try {
      const res = await axios.get(api(`/help/admin/session/${currentChatId}/messages`), {
        headers: { Authorization: `Bearer ${token}` }
      });
      const msgs: ChatMessage[] = (res.data.messages || []).map((m: any) => ({
        id: m.id,
        type: m.role === "admin" ? "admin" : m.role === "system" ? "system" : "user",
        content: m.content,
        timestamp: new Date(m.created_at + "Z")
      }));
      setActiveChats(prev => ({ ...prev, [currentChatId]: msgs }));
    } catch (err) {
      // Silently ignore
    }
  }, [token, currentChatId]);

  // Unified Polling Interval
  useEffect(() => {
    if (!token) return;
    
    const loadInitial = async () => {
        await Promise.all([
            fetchSessions(),
            fetchTickets()
        ]);
    };
    loadInitial();
    
    const pollInterval = setInterval(async () => {
        try {
            await Promise.all([
                fetchSessions(),
                currentChatId ? fetchMessages() : Promise.resolve(),
                activeTab === "async" ? fetchTickets() : Promise.resolve()
            ]);
        } catch (err) {
            console.error("Polling error:", err);
        }
    }, 3000);
    
    return () => clearInterval(pollInterval);
  }, [token, currentChatId, activeTab, fetchSessions, fetchMessages]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChats, currentChatId]);

  const sendAdminMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || !currentChatId) return;
    
    const content = inputMsg;
    setInputMsg("");

    // Optimistically render admin message
    setActiveChats(prev => ({
      ...prev,
      [currentChatId]: [...(prev[currentChatId] || []), { id: `temp-${crypto.randomUUID()}`, type: "admin", content, timestamp: new Date() }]
    }));
    
    try {
      await axios.post(api("/help/admin-reply"), {
        session_id: currentChatId,
        message: content
      }, { headers: { Authorization: `Bearer ${token}` } });
      await fetchMessages();
    } catch (err) {
      console.error(err);
      pushToast("danger", "Failed to send reply");
    }
  };

  const sendTicketReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticketReply.trim() || !currentTicketId) return;
    try {
      const fd = new FormData();
      fd.append("admin_reply", ticketReply);
      await axios.post(api(`/support/ticket/${currentTicketId}/reply`), fd, { headers: { Authorization: `Bearer ${token}` } });
      setTicketReply("");
      pushToast("success", "Reply sent");
      await fetchTickets();
    } catch (err) {
      console.error(err);
      pushToast("danger", "Failed to send ticket reply");
    }
  };

  const selectedSessionDetails = escalatedSessions.find(s => s.session_id === currentChatId);
  const selectedTicketDetails = tickets.find(t => t.id === currentTicketId);

  return (
    <div className="flex h-[calc(100vh-80px)] overflow-hidden bg-surface-2/20">
      
      {/* Left Pane - Inbox */}
      <div className="w-80 border-r border-line bg-surface flex flex-col z-10 shadow-sm">
        <div className="p-4 border-b border-line">
           <h2 className="text-xl font-bold text-ink mb-4">Support Inbox</h2>
           <div className="flex bg-surface-2 p-1 rounded-lg">
              <button 
                 className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'live' ? 'bg-surface shadow text-ink' : 'text-ink-3 hover:text-ink-2'}`}
                 onClick={() => setActiveTab('live')}
              >
                 Live Chats
                 {escalatedSessions.length > 0 && <span className="ml-2 px-1.5 py-0.5 bg-red-100 text-red-600 rounded text-[10px]">{escalatedSessions.length}</span>}
              </button>
              <button 
                 className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors ${activeTab === 'async' ? 'bg-surface shadow text-ink' : 'text-ink-3 hover:text-ink-2'}`}
                 onClick={() => setActiveTab('async')}
              >
                 Tickets
              </button>
           </div>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'live' ? (
             escalatedSessions.length === 0 ? (
               <div className="p-8 text-center text-ink-3">
                 <AlertCircle className="w-8 h-8 mx-auto mb-3 opacity-20" />
                 <p className="text-sm">No active live chats.</p>
               </div>
             ) : (
               <div className="divide-y divide-line">
                 {escalatedSessions.map(session => (
                   <div 
                     key={session.session_id}
                     onClick={() => { setCurrentChatId(session.session_id); setCurrentTicketId(null); }}
                     className={`p-4 cursor-pointer hover:bg-surface-2 transition-colors ${currentChatId === session.session_id ? 'border-l-4 border-l-primary bg-primary/5' : 'border-l-4 border-transparent'}`}
                   >
                      <div className="flex justify-between items-start mb-1">
                         <h4 className="font-semibold text-ink text-sm truncate pr-2">{session.citizen_name}</h4>
                         <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse mt-1" />
                      </div>
                      <p className="text-xs text-ink-3 truncate">Escalated from AI</p>
                   </div>
                 ))}
               </div>
             )
          ) : (
             tickets.length === 0 ? (
               <div className="p-8 text-center text-ink-3">
                 <CheckCircle className="w-8 h-8 mx-auto mb-3 opacity-20" />
                 <p className="text-sm">Inbox Zero! All tickets resolved.</p>
               </div>
             ) : (
               <div className="divide-y divide-line">
                 {tickets.map(t => (
                   <div 
                     key={t.id}
                     onClick={() => { setCurrentTicketId(t.id); setCurrentChatId(null); }}
                     className={`p-4 cursor-pointer hover:bg-surface-2 transition-colors ${currentTicketId === t.id ? 'border-l-4 border-l-primary bg-primary/5' : 'border-l-4 border-transparent'}`}
                   >
                      <div className="flex justify-between items-start mb-1">
                         <h4 className="font-semibold text-ink text-sm truncate pr-2">{t.subject}</h4>
                      </div>
                      <div className="flex justify-between items-center mt-2">
                         <span className="text-[10px] px-1.5 py-0.5 rounded-sm bg-surface-2 border border-line font-medium text-ink-2">{t.status}</span>
                         <span className="text-[10px] text-ink-3 font-mono">{t.ticket_number}</span>
                      </div>
                   </div>
                 ))}
               </div>
             )
          )}
        </div>
      </div>

      {/* Middle Pane - Main Workspace */}
      <div className="flex-1 flex flex-col bg-surface min-w-0 relative">
        {currentChatId ? (
           // --- LIVE CHAT VIEW ---
           !activeChats[currentChatId] ? (
             <div className="flex-1 flex flex-col items-center justify-center gap-3 bg-surface/50">
               <RefreshCw className="w-6 h-6 text-primary animate-spin" />
               <p className="text-ink-2 text-sm">Loading chat history...</p>
             </div>
           ) : (
           <>
              <div className="px-6 py-4 border-b border-line bg-surface/80 backdrop-blur-md flex items-center justify-between">
                 <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary font-bold">
                       {selectedSessionDetails?.citizen_name?.charAt(0) || "C"}
                    </div>
                    <div>
                       <h3 className="font-semibold text-ink leading-tight">{selectedSessionDetails?.citizen_name || "Citizen"}</h3>
                       <p className="text-xs text-ink-3">Live Session: {currentChatId.substring(0,8)}</p>
                    </div>
                 </div>
                 <Button variant="ghost" size="sm" onClick={() => setCurrentChatId(null)} className="text-ink-3 hover:text-ink">Close</Button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 bg-surface-2/30">
                 <div className="max-w-3xl mx-auto flex flex-col">
                    {activeChats[currentChatId]?.map((msg) => (
                       <ChatBubble key={msg.id} message={msg} />
                    ))}
                    <div ref={messagesEndRef} className="h-4" />
                 </div>
              </div>
              
              <div className="p-4 bg-surface border-t border-line">
                 <form onSubmit={sendAdminMessage} className="max-w-3xl mx-auto flex gap-3">
                   <Input
                     className="flex-1 rounded-2xl py-6 px-6 bg-surface border-line shadow-sm focus-visible:ring-primary/20 text-base"
                     placeholder="Type your reply to the citizen..."
                     value={inputMsg}
                     onChange={(e) => setInputMsg(e.target.value)}
                   />
                   <Button type="submit" variant="primary" className="rounded-2xl aspect-square p-0 w-14 flex items-center justify-center shadow-md transition-transform active:scale-95" disabled={!inputMsg.trim()}>
                     <Send className="w-5 h-5 -ml-0.5" />
                   </Button>
                 </form>
              </div>
           </>
           )
        ) : currentTicketId && selectedTicketDetails ? (
           // --- TICKET VIEW ---
           <div className="flex-1 flex flex-col h-full overflow-hidden">
              <div className="px-6 py-4 border-b border-line bg-surface flex items-center justify-between">
                 <div>
                    <div className="flex items-center gap-2 mb-1">
                       <span className="text-[10px] px-2 py-0.5 rounded bg-surface-2 border border-line font-medium text-ink-2">{selectedTicketDetails.status}</span>
                       <span className="text-xs text-ink-3 font-mono">{selectedTicketDetails.ticket_number}</span>
                    </div>
                    <h3 className="font-bold text-ink text-lg leading-tight">{selectedTicketDetails.subject}</h3>
                 </div>
                 <Button variant="ghost" size="sm" onClick={() => setCurrentTicketId(null)}>Close</Button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 bg-surface-2/30">
                 <div className="max-w-3xl mx-auto space-y-6">
                    {/* Original Message */}
                    <div className="bg-surface rounded-2xl border border-line p-5 shadow-sm">
                       <div className="flex items-center gap-2 mb-3 pb-3 border-b border-line border-dashed">
                          <UserCircle className="w-5 h-5 text-ink-3" />
                          <span className="text-sm font-semibold text-ink">Citizen Request</span>
                          <span className="text-xs text-ink-3 ml-auto">{new Date(selectedTicketDetails.created_at + "Z").toLocaleString()}</span>
                       </div>
                       <p className="text-sm text-ink whitespace-pre-wrap">{selectedTicketDetails.message}</p>
                    </div>
                    
                    {/* History / Replies */}
                    {selectedTicketDetails.history && selectedTicketDetails.history.map((msg: any, idx: number) => (
                       <div key={idx} className={`rounded-2xl border p-5 shadow-sm ${msg.sender === 'admin' ? 'bg-primary/5 border-primary/20 ml-12' : 'bg-surface border-line mr-12'}`}>
                          <div className="flex items-center gap-2 mb-2">
                             <span className={`text-xs font-bold uppercase tracking-wider ${msg.sender === 'admin' ? 'text-primary' : 'text-ink-3'}`}>
                                {msg.sender === 'admin' ? 'Admin' : 'Citizen'}
                             </span>
                             <span className="text-[10px] text-ink-3 ml-auto">{new Date(msg.timestamp + "Z").toLocaleString()}</span>
                          </div>
                          <p className="text-sm text-ink whitespace-pre-wrap">{msg.message}</p>
                       </div>
                    ))}
                    
                    {/* Reply Box */}
                    <div className="bg-surface rounded-2xl border border-line p-5 shadow-sm mt-8">
                       <h4 className="text-sm font-bold text-ink mb-3 flex items-center gap-2"><Send className="w-4 h-4 text-primary" /> Reply to Ticket</h4>
                       <form onSubmit={sendTicketReply}>
                          <Textarea 
                             rows={4} 
                             className="w-full bg-surface-2 border-line rounded-xl resize-none mb-3" 
                             placeholder="Write your response..."
                             value={ticketReply}
                             onChange={(e) => setTicketReply(e.target.value)}
                          />
                          <div className="flex justify-end">
                             <Button type="submit" variant="primary" disabled={!ticketReply.trim()}>Send Reply</Button>
                          </div>
                       </form>
                    </div>
                 </div>
              </div>
           </div>
        ) : (
           // --- EMPTY STATE ---
           <div className="flex-1 flex flex-col items-center justify-center text-ink-3 p-10 text-center bg-surface-2/30">
             <div className="w-24 h-24 rounded-full bg-surface shadow-sm border border-line flex items-center justify-center mb-6">
                <MessageSquare className="w-10 h-10 text-ink-3 opacity-50" />
             </div>
             <p className="text-xl font-bold text-ink-2 mb-2">Select a conversation</p>
             <p className="max-w-xs text-sm">Choose an active live chat or an async ticket from the left inbox to begin helping citizens.</p>
           </div>
        )}
      </div>

      {/* Right Pane - Citizen Context */}
      <div className="w-80 border-l border-line bg-surface p-6 flex flex-col overflow-y-auto shadow-sm z-10">
         <h3 className="text-sm font-bold text-ink-3 uppercase tracking-wider mb-6 flex items-center gap-2"><UserCircle className="w-4 h-4" /> Citizen Profile</h3>
         
         {currentChatId && selectedSessionDetails ? (
            <div className="space-y-6">
               <div className="text-center">
                  <div className="w-20 h-20 rounded-full bg-primary/10 text-primary flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                     {selectedSessionDetails.citizen_name?.charAt(0) || "C"}
                  </div>
                  <h2 className="text-lg font-bold text-ink">{selectedSessionDetails.citizen_name}</h2>
                  <p className="text-sm text-ink-2 truncate" title={selectedSessionDetails.email}>{selectedSessionDetails.email}</p>
               </div>
               
               <div className="p-4 bg-surface-2 rounded-2xl border border-line space-y-4">
                  <div>
                     <p className="text-xs text-ink-3 font-semibold uppercase tracking-wider mb-1">User ID</p>
                     <p className="text-xs text-ink font-mono bg-surface p-1.5 rounded border border-line truncate" title={selectedSessionDetails.user_id || "Anonymous"}>
                        {selectedSessionDetails.user_id || "Anonymous"}
                     </p>
                  </div>
                  <div>
                     <p className="text-xs text-ink-3 font-semibold uppercase tracking-wider mb-1">Total Tickets</p>
                     <p className="text-sm font-bold text-ink flex items-center gap-2">
                        <FileText className="w-4 h-4 text-primary" /> {selectedSessionDetails.ticket_count} submitted
                     </p>
                  </div>
               </div>
            </div>
         ) : currentTicketId && selectedTicketDetails ? (
            <div className="space-y-6">
               <div className="text-center">
                  <div className="w-20 h-20 rounded-full bg-accent/10 text-accent flex items-center justify-center mx-auto mb-4 text-2xl font-bold">
                     <Mail className="w-8 h-8" />
                  </div>
                  <h2 className="text-lg font-bold text-ink">Ticket Details</h2>
               </div>
               
               <div className="p-4 bg-surface-2 rounded-2xl border border-line space-y-4">
                  <div>
                     <p className="text-xs text-ink-3 font-semibold uppercase tracking-wider mb-1">Status</p>
                     <p className="text-sm font-bold text-ink">{selectedTicketDetails.status}</p>
                  </div>
                  <div>
                     <p className="text-xs text-ink-3 font-semibold uppercase tracking-wider mb-1">Created At</p>
                     <p className="text-sm text-ink flex items-center gap-2">
                        <Clock className="w-4 h-4 text-accent" /> {selectedTicketDetails.created_at ? new Date(selectedTicketDetails.created_at.endsWith("Z") ? selectedTicketDetails.created_at : selectedTicketDetails.created_at + "Z").toLocaleDateString() : "—"}
                     </p>
                  </div>
                  <div>
                     <p className="text-xs text-ink-3 font-semibold uppercase tracking-wider mb-1">User ID Reference</p>
                     <p className="text-[10px] text-ink-2 font-mono bg-surface p-1.5 rounded border border-line truncate" title={selectedTicketDetails.user_id}>
                        {selectedTicketDetails.user_id}
                     </p>
                  </div>
               </div>
            </div>
         ) : (
            <div className="text-center text-ink-3 py-10">
               <UserCircle className="w-12 h-12 mx-auto mb-3 opacity-20" />
               <p className="text-sm">Select a chat or ticket to view citizen details.</p>
            </div>
         )}
      </div>

    </div>
  );
}
