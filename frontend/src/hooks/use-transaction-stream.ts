"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { wsApi } from "@/lib/api";

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
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);

  // Keep latest callbacks in refs to avoid re-triggering connection on parent render
  const onTransactionRef = useRef(onTransaction);
  const onReviewRef = useRef(onReview);
  useEffect(() => {
    onTransactionRef.current = onTransaction;
    onReviewRef.current = onReview;
  }, [onTransaction, onReview]);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    // Clean up existing instance if any
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }

    setStatus("CONNECTING");

    try {
      const url = wsApi("/transactions/ws");
      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onopen = () => {
        setStatus("CONNECTED");
        reconnectAttemptsRef.current = 0;

        // Set up periodic heartbeat ping
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
        } catch (err) {
          console.error("Error parsing WebSocket message:", err);
        }
      };

      socket.onerror = (err) => {
        console.warn("Transaction stream WebSocket error:", err);
        setStatus("ERROR");
      };

      socket.onclose = (evt) => {
        setStatus("DISCONNECTED");
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Schedule auto-reconnect with exponential backoff if enabled
        if (enabled && evt.code !== 1000) {
          const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 10000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };
    } catch (err) {
      console.error("Failed to construct WebSocket:", err);
      setStatus("ERROR");
    }
  }, [enabled]);

  useEffect(() => {
    if (enabled) {
      connect();
    } else {
      if (socketRef.current) {
        socketRef.current.close(1000, "Client disabled");
        socketRef.current = null;
      }
      setStatus("DISCONNECTED");
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close(1000, "Component unmounted");
        socketRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
    };
  }, [enabled, connect]);

  const reconnect = useCallback(() => {
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  return {
    isConnected: status === "CONNECTED",
    status,
    reconnect,
  };
}
