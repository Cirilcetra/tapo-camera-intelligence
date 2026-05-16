"use client";

import { CamEvent } from "@/types/event";
import { EventCard } from "./EventCard";
import { EmptyState } from "@/components/ui/EmptyState";
import { Spinner } from "@/components/ui/Spinner";
import { Activity } from "lucide-react";

interface EventTimelineProps {
  events: CamEvent[];
  loading: boolean;
  onViewSnapshot: (event: CamEvent) => void;
  onAcknowledge: (id: number) => void;
}

export function EventTimeline({
  events,
  loading,
  onViewSnapshot,
  onAcknowledge,
}: EventTimelineProps) {
  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={28} />
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No events yet"
        description="Events will appear here when motion is detected"
      />
    );
  }

  return (
    <div className="space-y-2">
      {events.map((event) => (
        <EventCard
          key={event.id}
          event={event}
          onViewSnapshot={onViewSnapshot}
          onAcknowledge={onAcknowledge}
        />
      ))}
    </div>
  );
}
