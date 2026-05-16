"use client";

import { useState, useCallback, useEffect } from "react";
import { useCameras } from "@/hooks/useCameras";
import { useEvents } from "@/hooks/useEvents";
import { useWebSocket } from "@/hooks/useWebSocket";
import { EventFilter } from "@/components/events/EventFilter";
import { EventTimeline } from "@/components/events/EventTimeline";
import { SemanticSearch } from "@/components/events/SemanticSearch";
import { Modal } from "@/components/ui/Modal";
import { CamEvent, EventFilters } from "@/types/event";
import { clearUnread } from "@/hooks/useWebSocket";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function EventsPage() {
  const { cameras } = useCameras();
  const [filters, setFilters] = useState<EventFilters>({});
  const { events, loading, prependEvent, patchEvent, acknowledgeEvent } = useEvents(filters);
  const [snapshotEvent, setSnapshotEvent] = useState<CamEvent | null>(null);

  // Semantic search state
  const [searchResults, setSearchResults] = useState<CamEvent[] | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const isSearchActive = searchResults !== null;

  // Clear notification badge when user views events page
  useEffect(() => {
    clearUnread();
  }, []);

  // Real-time: prepend newly created events to the live list
  const onCreated = useCallback(
    (event: CamEvent) => {
      prependEvent(event);
    },
    [prependEvent],
  );

  // Real-time: patch existing events when AI enrichment completes
  const onUpdated = useCallback(
    (event: CamEvent) => {
      patchEvent(event);
      // Also patch search results if a search is active
      setSearchResults((prev) =>
        prev ? prev.map((e) => (e.id === event.id ? { ...e, ...event } : e)) : null,
      );
    },
    [patchEvent],
  );

  useWebSocket(onCreated, onUpdated);

  const handleSearchResults = useCallback((results: CamEvent[], query: string) => {
    setSearchResults(results);
    setSearchQuery(query);
  }, []);

  const handleSearchClear = useCallback(() => {
    setSearchResults(null);
    setSearchQuery("");
  }, []);

  const displayedEvents = isSearchActive ? searchResults! : events;
  const countLabel = isSearchActive
    ? `${searchResults!.length} result${searchResults!.length !== 1 ? "s" : ""} for "${searchQuery}"`
    : `${events.length} event${events.length !== 1 ? "s" : ""} matching filters`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-zinc-100">Events</h2>
        <p className="mt-0.5 text-sm text-zinc-500">{countLabel}</p>
      </div>

      <SemanticSearch
        onResults={handleSearchResults}
        onClear={handleSearchClear}
        isActive={isSearchActive}
      />

      {!isSearchActive && (
        <EventFilter cameras={cameras} filters={filters} onChange={setFilters} />
      )}

      <EventTimeline
        events={displayedEvents}
        loading={loading && !isSearchActive}
        onViewSnapshot={setSnapshotEvent}
        onAcknowledge={acknowledgeEvent}
      />

      <Modal
        open={!!snapshotEvent}
        onClose={() => setSnapshotEvent(null)}
        title="Snapshot"
      >
        {snapshotEvent?.snapshot_path && (
          <img
            src={`${API_URL}/media/snapshots/${snapshotEvent.snapshot_path}`}
            alt="Event snapshot"
            className="w-full rounded-lg"
          />
        )}
      </Modal>
    </div>
  );
}
