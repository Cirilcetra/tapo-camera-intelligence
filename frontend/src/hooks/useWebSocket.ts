"use client";

import { useEffect, useState } from "react";
import { CamEvent } from "@/types/event";

const WS_URL =
  (typeof window !== "undefined" ? process.env.NEXT_PUBLIC_WS_URL : "") ||
  "ws://localhost:8000";

type CreatedListener = (event: CamEvent) => void;
type UpdatedListener = (event: CamEvent) => void;

// Module-level singleton so all components share one socket
let socket: WebSocket | null = null;
const createdListeners: Set<CreatedListener> = new Set();
const updatedListeners: Set<UpdatedListener> = new Set();
let unreadCount = 0;
const unreadListeners: Set<(n: number) => void> = new Set();

function broadcastUnread() {
  unreadListeners.forEach((fn) => fn(unreadCount));
}

function handleMessage(raw: string) {
  try {
    const msg = JSON.parse(raw);

    // Typed envelope: { type, data }
    if (msg && typeof msg.type === "string" && msg.data) {
      if (msg.type === "event_created") {
        const event: CamEvent = msg.data;
        createdListeners.forEach((fn) => fn(event));
        unreadCount += 1;
        broadcastUnread();
      } else if (msg.type === "event_updated") {
        const event: CamEvent = msg.data;
        updatedListeners.forEach((fn) => fn(event));
      }
      // heartbeat and other types are ignored
      return;
    }

    // Legacy bare event dict (backward compat if envelope is missing)
    if (msg && typeof msg.id === "number") {
      const event: CamEvent = msg;
      createdListeners.forEach((fn) => fn(event));
      unreadCount += 1;
      broadcastUnread();
    }
  } catch {
    // ignore malformed
  }
}

function connect() {
  if (socket && socket.readyState !== WebSocket.CLOSED) return;

  socket = new WebSocket(`${WS_URL}/ws/events`);

  socket.onmessage = (msg) => handleMessage(msg.data);

  socket.onclose = () => {
    setTimeout(connect, 3000);
  };

  socket.onerror = () => {
    socket?.close();
  };
}

if (typeof window !== "undefined") {
  connect();
}

export function useWebSocket(
  onCreated?: CreatedListener,
  onUpdated?: UpdatedListener,
) {
  const [lastCreated, setLastCreated] = useState<CamEvent | null>(null);
  const [lastUpdated, setLastUpdated] = useState<CamEvent | null>(null);

  useEffect(() => {
    const createdHandler: CreatedListener = (ev) => {
      setLastCreated(ev);
      onCreated?.(ev);
    };
    const updatedHandler: UpdatedListener = (ev) => {
      setLastUpdated(ev);
      onUpdated?.(ev);
    };
    createdListeners.add(createdHandler);
    updatedListeners.add(updatedHandler);
    return () => {
      createdListeners.delete(createdHandler);
      updatedListeners.delete(updatedHandler);
    };
  }, [onCreated, onUpdated]);

  return { lastCreated, lastUpdated };
}

export function useUnreadCount() {
  const [count, setCount] = useState(() => unreadCount);

  useEffect(() => {
    const sync = () => setCount(unreadCount);
    unreadListeners.add(sync);
    return () => {
      unreadListeners.delete(sync);
    };
  }, []);

  return count;
}

export function clearUnread() {
  unreadCount = 0;
  broadcastUnread();
}
