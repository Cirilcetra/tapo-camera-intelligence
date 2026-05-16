"use client";

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { CamEvent, EventFilters } from "@/types/event";

export function useEvents(filters: EventFilters = {}) {
  const [events, setEvents] = useState<CamEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (filters.camera_id) params.camera_id = filters.camera_id;
      if (filters.type) params.type = filters.type;
      if (filters.since) params.since = filters.since;
      if (filters.until) params.until = filters.until;

      const res = await api.get<CamEvent[]>("/api/events", { params });
      setEvents(res.data);
    } catch {
      setError("Failed to load events");
    } finally {
      setLoading(false);
    }
  }, [filters.camera_id, filters.type, filters.since, filters.until]);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const prependEvent = useCallback((event: CamEvent) => {
    setEvents((prev) => [event, ...prev]);
  }, []);

  /** Patch a single event in the cache (used for event_updated from WS). */
  const patchEvent = useCallback((updated: CamEvent) => {
    setEvents((prev) =>
      prev.map((e) => (e.id === updated.id ? { ...e, ...updated } : e))
    );
  }, []);

  const acknowledgeEvent = useCallback(async (id: number) => {
    await api.patch(`/api/events/${id}/ack`);
    setEvents((prev) =>
      prev.map((e) => (e.id === id ? { ...e, acknowledged: true } : e))
    );
  }, []);

  return { events, loading, error, refresh: fetch, prependEvent, patchEvent, acknowledgeEvent };
}
