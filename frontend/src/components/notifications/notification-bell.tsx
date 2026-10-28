"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import {
  Bell,
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Clock,
  CheckCheck,
  Inbox,
  X,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export interface SystemNotification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: string;
  priority: string;
  link?: string | null;
  metadata_json?: Record<string, any>;
  is_read: boolean;
  created_at: string;
  read_at?: string | null;
}

export function NotificationBell() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<SystemNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inFlightRef = useRef(false);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Fetch notifications
  const fetchNotifications = useCallback(async (quiet = true) => {
    if (!user || inFlightRef.current) return;
    inFlightRef.current = true;
    if (!quiet) setIsLoading(true);

    try {
      const res = await axios.get(api("/notifications"), {
        params: { limit: 25 },
      });
      if (res.data) {
        setNotifications(res.data.notifications || []);
        setUnreadCount(res.data.unread_count || 0);
      }
    } catch {
      // Quiet fail if network glitch or auth not ready
    } finally {
      inFlightRef.current = false;
      if (!quiet) setIsLoading(false);
    }
  }, [user]);

  // Initial fetch and 20s interval polling
  useEffect(() => {
    if (!user) return;
    fetchNotifications(true);

    const interval = setInterval(() => {
      fetchNotifications(true);
    }, 20000);

    return () => clearInterval(interval);
  }, [user, fetchNotifications]);

  // Refresh when opened
  const toggleDropdown = () => {
    const nextState = !isOpen;
    setIsOpen(nextState);
    if (nextState) {
      fetchNotifications(false);
    }
  };

  // Mark single notification as read and optionally navigate
  const handleNotificationClick = async (notif: SystemNotification) => {
    if (!notif.is_read) {
      // Optimistic update
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));

      try {
        await axios.post(api(`/notifications/${notif.id}/read`));
      } catch {
        // Fallback sync
      }
    }

    if (notif.link) {
      setIsOpen(false);
      router.push(notif.link);
    }
  };

  // Mark all notifications as read
  const handleMarkAllRead = async () => {
    if (unreadCount === 0) return;

    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);

    try {
      await axios.post(api("/notifications/mark-all-read"));
    } catch {
      fetchNotifications(true);
    }
  };

  // Get icon by notification type
  const getIcon = (type: string, priority: string) => {
    switch (type) {
      case "chat_message":
        return <MessageSquare className="w-4 h-4 text-sky-400 shrink-0" />;
      case "kyc_approved":
        return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
      case "kyc_submitted":
        return <FileText className="w-4 h-4 text-amber-400 shrink-0" />;
      case "case_assigned":
        return <FileText className="w-4 h-4 text-indigo-400 shrink-0" />;
      case "misconduct_report":
        return <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />;
      default:
        if (priority === "urgent" || priority === "high") {
          return <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />;
        }
        return <Bell className="w-4 h-4 text-accent shrink-0" />;
    }
  };

  // Format relative timestamp
  const formatTimeAgo = (isoString: string) => {
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffSecs < 45) return "Just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return "Yesterday";
      return `${diffDays}d ago`;
    } catch {
      return "Recent";
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger */}
      <button
        onClick={toggleDropdown}
        aria-label="System Notifications"
        className="relative p-2.5 text-ink-2 hover:text-ink rounded-pill hover:bg-surface-2 transition-colors duration-150 focus:outline-none"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-4 min-w-4 px-1 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-surface animate-in zoom-in-50">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown Tray */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl bg-surface border border-line shadow-2xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 bg-surface-2/60 border-b border-line">
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-ink">Notifications</span>
              {unreadCount > 0 ? (
                <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-500/15 text-rose-500 border border-rose-500/25">
                  {unreadCount} unread
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-surface-3 text-ink-3">
                  All caught up
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-accent hover:text-accent/80 hover:underline"
                  title="Mark all as read"
                >
                  <CheckCheck className="w-3.5 h-3.5" />
                  Mark all read
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 text-ink-3 hover:text-ink rounded-lg hover:bg-surface-2"
                aria-label="Close"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Body */}
          <div className="max-h-[380px] overflow-y-auto divide-y divide-line/60">
            {isLoading && notifications.length === 0 ? (
              <div className="py-8 text-center text-xs text-ink-3">
                Loading notifications...
              </div>
            ) : notifications.length === 0 ? (
              <div className="py-10 px-4 text-center space-y-2">
                <div className="w-10 h-10 rounded-full bg-surface-2 border border-line flex items-center justify-center mx-auto text-ink-3">
                  <Inbox className="w-5 h-5" />
                </div>
                <p className="text-xs font-medium text-ink">No notifications yet</p>
                <p className="text-[11px] text-ink-3">
                  You will be notified here when cases are assigned, direct chats arrive, or KYC statuses change.
                </p>
              </div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleNotificationClick(item)}
                  className={`p-3.5 flex gap-3 text-left transition-colors cursor-pointer group ${
                    !item.is_read
                      ? "bg-accent/5 hover:bg-accent/10"
                      : "hover:bg-surface-2/60"
                  }`}
                >
                  {/* Icon */}
                  <div className="mt-0.5 p-2 rounded-xl bg-surface-2 border border-line shadow-xs shrink-0 self-start">
                    {getIcon(item.type, item.priority)}
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className={`text-xs truncate ${!item.is_read ? "font-bold text-ink" : "font-medium text-ink-2"}`}>
                        {item.title}
                      </p>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <span className="text-[10px] text-ink-3 flex items-center gap-0.5">
                          <Clock className="w-2.5 h-2.5" />
                          {formatTimeAgo(item.created_at)}
                        </span>
                        {!item.is_read && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-ink-3 line-clamp-2 leading-relaxed">
                      {item.message}
                    </p>

                    {item.link && (
                      <div className="pt-0.5 flex items-center gap-1 text-[11px] font-semibold text-accent group-hover:underline">
                        <span>Open Details</span>
                        <ExternalLink className="w-3 h-3" />
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
