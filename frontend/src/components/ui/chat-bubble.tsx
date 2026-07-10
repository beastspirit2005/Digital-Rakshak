import React from "react";
import { cn } from "@/lib/utils";
import { User, Bot, ShieldAlert } from "lucide-react";
import { motion } from "framer-motion";

export type MessageType = "user" | "ai" | "admin" | "system";

export interface ChatMessage {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
}

interface ChatBubbleProps {
  message: ChatMessage;
}

export function ChatBubble({ message }: ChatBubbleProps) {
  const isUser = message.type === "user";
  const isSystem = message.type === "system";
  
  if (isSystem) {
    return (
      <div className="flex justify-center my-4">
        <span className="text-xs font-medium text-ink-3 bg-surface-2 px-3 py-1 rounded-full border border-line">
          {message.content}
        </span>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex w-full mt-4 space-x-3 max-w-lg", isUser ? "ml-auto justify-end" : "mr-auto")}
    >
      {!isUser && (
        <div className="flex-shrink-0">
          <div className={cn(
            "w-8 h-8 rounded-full flex items-center justify-center",
            message.type === "ai" ? "bg-primary/20 text-primary" : "bg-accent/20 text-accent"
          )}>
            {message.type === "ai" ? <Bot className="w-4 h-4" /> : <ShieldAlert className="w-4 h-4" />}
          </div>
        </div>
      )}
      
      <div>
        <div className={cn(
          "px-4 py-3 rounded-2xl text-sm whitespace-pre-wrap shadow-sm",
          isUser 
            ? "bg-primary text-primary-foreground rounded-tr-sm" 
            : "bg-surface-2 text-ink border border-line rounded-tl-sm"
        )}>
          {message.content}
        </div>
        <div className={cn("text-[10px] text-ink-3 mt-1 px-1", isUser && "text-right")}>
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {message.type === "admin" && " • Admin"}
          {message.type === "ai" && " • AI Support"}
        </div>
      </div>
    </motion.div>
  );
}

export function TypingIndicator() {
  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex w-full mt-4 space-x-3 max-w-lg mr-auto"
    >
      <div className="flex-shrink-0">
        <div className="w-8 h-8 rounded-full flex items-center justify-center bg-primary/20 text-primary">
          <Bot className="w-4 h-4" />
        </div>
      </div>
      <div className="px-4 py-4 rounded-2xl bg-surface-2 border border-line rounded-tl-sm flex gap-1 items-center">
        <motion.div className="w-1.5 h-1.5 bg-ink-3 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0 }} />
        <motion.div className="w-1.5 h-1.5 bg-ink-3 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.2 }} />
        <motion.div className="w-1.5 h-1.5 bg-ink-3 rounded-full" animate={{ y: [0, -3, 0] }} transition={{ repeat: Infinity, duration: 1, delay: 0.4 }} />
      </div>
    </motion.div>
  );
}
