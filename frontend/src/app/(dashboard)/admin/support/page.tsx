"use client";

import { api } from "@/lib/api";
import { useEffect, useState, useRef } from "react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/field";
import { MessageSquare, Mail, CheckCircle, Send, Users, AlertCircle } from "lucide-react";
import { Rise } from "@/components/ui/motion";
import { ChatBubble, ChatMessage } from "@/components/ui/chat-bubble";

export default function AdminSupportPage() {
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { token, user } = useAuthStore();
  
  // WS State
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [activeChats, setActiveChats] = useState<{ [clientId: string]: ChatMessage[] }>({});
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [inputMsg, setInputMsg] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const fetchTickets = async () => {
    try {
      const res = await axios.get(api("/support/tickets"), {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTickets(res.data.tickets);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) fetchTickets();
  }, [token]);

  // Connect WebSocket for Admin
  useEffect(() => {
    if (!user) return;
    
    const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api/v1";
    let wsBase: string;
    if (API_BASE_URL.startsWith("http")) {
      wsBase = API_BASE_URL.replace(/^http/, "ws");
    } else {
      const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsBase = `${proto}//${window.location.hostname}:8000/api/v1`;
    }
    
    const socket = new WebSocket(`${wsBase}/help/ws/admin/${user.id}`);
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === "escalation_request") {
        const clientId = data.client_id;
        setActiveChats(prev => {
          if (prev[clientId]) return prev;
          return { ...prev, [clientId]: [{ id: Date.now().toString(), type: "system", content: `Citizen ${clientId} has requested live support.`, timestamp: new Date() }] };
        });
        if (!currentChatId) setCurrentChatId(clientId); // Auto-focus if none selected
      } 
      else if (data.type === "human_chat" && data.target_client_id) {
        // Echo of our own message sent to a user
         const clientId = data.target_client_id;
         setActiveChats(prev => {
            const chat = prev[clientId] || [];
            return { ...prev, [clientId]: [...chat, { id: Date.now().toString(), type: "admin", content: data.content, timestamp: new Date() }] };
         });
      }
      // Note: If the citizen replies while in human chat mode, we need to handle it. 
      // The current backend routes citizen 'chat' type directly to AI. 
      // We'll just show escalations for now and the admin can reply. A full robust system would track the state in DB.
    };
    
    setWs(socket);
    
    return () => socket.close();
  }, [user, currentChatId]);

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeChats, currentChatId]);

  const sendAdminMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMsg.trim() || !ws || !currentChatId) return;
    
    ws.send(JSON.stringify({ type: "admin_reply", content: inputMsg, target_client_id: currentChatId }));
    setInputMsg("");
  };

  return (
    <div className="space-y-6 pt-2 h-[calc(100vh-80px)] flex flex-col">
      <Rise>
        <PageHeader
          title="Support Console"
          sub="Manage tickets and handle live chat escalations from citizens."
        />
      </Rise>

      <div className="flex gap-6 flex-1 min-h-0">
        
        {/* Left Column: Tickets & Active Escalations */}
        <Rise index={1} className="w-1/3 flex flex-col gap-6 overflow-y-auto pr-2 pb-10">
          
          {Object.keys(activeChats).length > 0 && (
            <div className="space-y-3">
              <h3 className="font-semibold text-ink flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-accent" /> Active Live Chats
              </h3>
              {Object.keys(activeChats).map(clientId => (
                <Card 
                  key={clientId} 
                  className={`p-4 cursor-pointer transition-colors ${currentChatId === clientId ? 'border-primary bg-primary/5' : 'hover:border-primary/50'}`}
                  onClick={() => setCurrentChatId(clientId)}
                >
                  <div className="flex items-center gap-2">
                    <Users className="w-4 h-4 text-primary" />
                    <span className="font-medium text-sm text-ink truncate">Citizen {clientId.slice(0,8)}...</span>
                  </div>
                </Card>
              ))}
            </div>
          )}

          <div className="space-y-4">
            <h3 className="font-semibold text-ink flex items-center gap-2 mt-4">
               <Mail className="w-4 h-4 text-ink-2" /> Async Tickets
            </h3>
            {loading ? (
              <p className="text-ink-3">Loading tickets...</p>
            ) : tickets.length === 0 ? (
              <Card className="p-8 text-center text-ink-3">
                <CheckCircle className="w-8 h-8 mx-auto mb-3 opacity-50" />
                <p>No open tickets.</p>
              </Card>
            ) : (
              tickets.map((t) => (
                <Card key={t.id} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-ink flex items-center gap-2 truncate">
                      {t.subject}
                    </h4>
                  </div>
                  <div className="flex gap-2 mb-3">
                     <span className="text-xs px-2 py-0.5 rounded-full bg-surface-2 text-ink-2 font-medium border border-line">{t.status}</span>
                     <span className="text-xs text-ink-3 tabular-nums font-mono">{t.ticket_number}</span>
                  </div>
                  
                  <p className="text-sm text-ink-2 mb-4 p-3 bg-surface-2 rounded-control border border-line whitespace-pre-wrap line-clamp-3">
                    {t.message}
                  </p>
                  
                  <div className="flex items-center gap-3">
                     <Button variant="secondary" size="sm" className="w-full">
                       <Mail className="w-4 h-4 mr-2" /> Reply via Email
                     </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
        </Rise>

        {/* Right Column: Live Chat Interface */}
        <Rise index={2} className="flex-1 flex flex-col min-h-0 bg-surface shadow-md border border-line rounded-3xl overflow-hidden">
          {currentChatId ? (
             <>
                <div className="px-6 py-4 border-b border-line bg-surface flex items-center justify-between">
                   <h3 className="font-semibold text-ink flex items-center gap-2">
                     <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                     Live Chat: {currentChatId}
                   </h3>
                   <Button variant="secondary" size="sm" onClick={() => setCurrentChatId(null)}>Close</Button>
                </div>
                <div className="flex-1 overflow-y-auto p-6 bg-surface/50">
                  {activeChats[currentChatId]?.map((msg) => (
                    <ChatBubble key={msg.id} message={msg} />
                  ))}
                  <div ref={messagesEndRef} />
                </div>
                <div className="p-4 bg-surface border-t border-line">
                  <form onSubmit={sendAdminMessage} className="flex gap-3">
                    <Input
                      className="flex-1 rounded-full px-6 bg-surface-2 border-transparent focus-visible:ring-primary/30"
                      placeholder="Type your reply to the citizen..."
                      value={inputMsg}
                      onChange={(e) => setInputMsg(e.target.value)}
                    />
                    <Button type="submit" variant="primary" className="rounded-full aspect-square p-0 w-12 flex items-center justify-center" disabled={!inputMsg.trim()}>
                      <Send className="w-5 h-5 -ml-1" />
                    </Button>
                  </form>
                </div>
             </>
          ) : (
             <div className="flex-1 flex flex-col items-center justify-center text-ink-3 p-10 text-center">
               <MessageSquare className="w-12 h-12 mb-4 opacity-20" />
               <p className="text-lg font-medium text-ink-2">No Active Live Chat Selected</p>
               <p className="max-w-xs mt-2">When a citizen requests human support, they will appear in the left sidebar.</p>
             </div>
          )}
        </Rise>
        
      </div>
    </div>
  );
}
