"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsApi, API_BASE_URL } from "@/lib/api";

export type StreamConnectionStatus = "CONNECTED" | "CONNECTING" | "DISCONNECTED" | "ERROR";

export interface TransactionStreamItem {
  id: string;
  transaction_id: string;
  account_id: string;
  beneficiary_id: string;
  device_id?: string;
  amount: number;
  currency: string;
  transaction_type: string;
  timestamp: string;
  status: string;
  decision: string;
  risk_score: number;
  risk_band: "LOW" | "GUARDED" | "ELEVATED" | "HIGH" | "CRITICAL";
  confidence: number;
  top_reason_code?: string;
  reason_codes?: string[];
  attack_dna?: any;
}

export interface ReviewStreamItem {
  transaction_id: string;
  human_decision: string;
  new_status: string;
  investigator_id?: string;
  recorded_at: string;
}

interface UseTransactionStreamOptions {
  onTransaction?: (transaction: TransactionStreamItem) => void;
  onReview?: (review: ReviewStreamItem) => void;
  enabled?: boolean;
}

export function useTransactionStream({
  onTransaction,
  onReview,
  enabled = true,
}: UseTransactionStreamOptions = {}) {
  const [status, setStatus] = useState<StreamConnectionStatus>("CONNECTING");
  const socketRef = useRef<WebSocket | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const useSSEFallbackRef = useRef(false);

  // Keep latest callbacks in refs to avoid re-triggering connection on parent render
  const onTransactionRef = useRef(onTransaction);
  const onReviewRef = useRef(onReview);

  useEffect(() => {
    onTransactionRef.current = onTransaction;
    onReviewRef.current = onReview;
  }, [onTransaction, onReview]);

  const cleanupConnections = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (socketRef.current) {
      try {
        socketRef.current.onopen = null;
        socketRef.current.onmessage = null;
        socketRef.current.onerror = null;
        socketRef.current.onclose = null;
        if (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING) {
          socketRef.current.close(1000, "Cleanup");
        }
      } catch (e) {}
      socketRef.current = null;
    }
    if (eventSourceRef.current) {
      try {
        eventSourceRef.current.close();
      } catch (e) {}
      eventSourceRef.current = null;
    }
  }, []);

  const startSSEFallback = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;
    cleanupConnections();
    useSSEFallbackRef.current = true;

    try {
      const token = localStorage.getItem("token") || localStorage.getItem("access_token") || "";
      const tokenParam = token ? `?token=${encodeURIComponent(token)}` : "";
      const sseUrl = `${API_BASE_URL}/transactions/stream${tokenParam}`;

      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus("CONNECTED");
        reconnectAttemptsRef.current = 0;
      };

      es.onmessage = (evt) => {
        if (!evt.data || evt.data.trim().startsWith(":")) return; // keepalive
        try {
          const payload = JSON.parse(evt.data);
          if (payload.type === "TRANSACTION_INGESTED" && onTransactionRef.current) {
            onTransactionRef.current(payload.data);
          } else if (payload.type === "TRANSACTION_REVIEWED" && onReviewRef.current) {
            onReviewRef.current(payload.data);
          }
        } catch (err) {}
      };

      es.onerror = () => {
        setStatus("DISCONNECTED");
        es.close();
        eventSourceRef.current = null;

        if (enabled) {
          const delay = Math.min(2000 * Math.pow(1.5, reconnectAttemptsRef.current), 15000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            startSSEFallback();
          }, delay);
        }
      };
    } catch (err) {
      setStatus("ERROR");
    }
  }, [enabled, cleanupConnections]);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    // If environment is known to fail WebSockets (e.g. Vercel Serverless), go straight to SSE
    if (useSSEFallbackRef.current) {
      startSSEFallback();
      return;
    }

    cleanupConnections();

    try {
      const url = wsApi("/transactions/ws");
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        setStatus("CONNECTED");
        reconnectAttemptsRef.current = 0;

        if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "PING" }));
          }
        }, 20000);
      };

      socket.onmessage = (evt) => {
        try {
          const payload = JSON.parse(evt.data);
          if (payload.type === "TRANSACTION_INGESTED" && onTransactionRef.current) {
            onTransactionRef.current(payload.data);
          } else if (payload.type === "TRANSACTION_REVIEWED" && onReviewRef.current) {
            onReviewRef.current(payload.data);
          }
        } catch (err) {}
      };

      socket.onerror = () => {
        // Automatically switch to SSE fallback without flooding console
        startSSEFallback();
      };

      socket.onclose = (evt) => {
        if (!useSSEFallbackRef.current && enabled && evt.code !== 1000) {
          // If WS closed unexpectedly, fallback to SSE stream
          startSSEFallback();
        } else {
          setStatus("DISCONNECTED");
        }
      };
    } catch (err) {
      startSSEFallback();
    }
  }, [enabled, cleanupConnections, startSSEFallback]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      cleanupConnections();
      setStatus("DISCONNECTED");
    }

    return () => {
      cleanupConnections();
    };
  }, [enabled, connect, cleanupConnections]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    useSSEFallbackRef.current = false;
    connect();
  }, [connect]);

  return {
    isConnected: status === "CONNECTED",
    status,
    reconnect,
  };
}
