"use client";

import { CamEvent } from "@/types/event";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { formatTimestamp, timeAgo } from "@/lib/utils";
import { Activity, CheckCheck, Image, Sparkles } from "lucide-react";

const typeBadge: Record<string, { variant: "warning" | "info" | "default"; label: string }> = {
  motion: { variant: "warning", label: "Motion" },
  object_detected: { variant: "info", label: "Object" },
  manual: { variant: "default", label: "Manual" },
};

interface EventCardProps {
  event: CamEvent;
  onViewSnapshot: (event: CamEvent) => void;
  onAcknowledge: (id: number) => void;
}

export function EventCard({ event, onViewSnapshot, onAcknowledge }: EventCardProps) {
  const badge = typeBadge[event.type] ?? { variant: "default" as const, label: event.type };
  const isPending = event.enrichment_status === "pending" || event.enrichment_status == null;
  const isFailed = event.enrichment_status === "failed";
  const hasSummary = !!event.ai_summary;

  return (
    <div
      className={`flex items-start gap-4 rounded-lg border p-4 transition-colors ${
        event.acknowledged
          ? "border-zinc-800 bg-zinc-900/40 opacity-70"
          : "border-zinc-700 bg-zinc-900"
      }`}
    >
      <div className="mt-0.5 flex-shrink-0 rounded-full bg-zinc-800 p-2">
        <Activity className="h-4 w-4 text-zinc-400" />
      </div>

      <div className="min-w-0 flex-1">
        {/* Header row */}
        <div className="mb-1 flex flex-wrap items-center gap-2">
          <Badge variant={badge.variant}>{badge.label}</Badge>
          {event.camera_name && (
            <span className="text-xs text-zinc-500">{event.camera_name}</span>
          )}
          {event.acknowledged && (
            <Badge variant="default">
              <CheckCheck className="mr-1 h-3 w-3 inline" />
              Acked
            </Badge>
          )}
          {typeof event.score === "number" && (
            <Badge variant="info">
              Match {Math.round(event.score * 100)}%
            </Badge>
          )}
        </div>

        {/* Timestamp */}
        <p className="text-xs text-zinc-400">
          {formatTimestamp(event.created_at)}{" "}
          <span className="text-zinc-600">({timeAgo(event.created_at)})</span>
        </p>

        {event.motion_score != null && (
          <p className="mt-0.5 text-xs text-zinc-500">
            Score: <span className="text-zinc-300">{event.motion_score.toFixed(0)}</span>
          </p>
        )}

        {/* AI summary section */}
        <div className="mt-2">
          {hasSummary ? (
            <div className="flex items-start gap-1.5">
              <Sparkles className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-violet-400" />
              <p className="text-xs leading-relaxed text-zinc-300">{event.ai_summary}</p>
            </div>
          ) : isPending ? (
            <div className="flex items-center gap-1.5">
              <Spinner size={12} className="text-zinc-500" />
              <span className="text-xs text-zinc-500 italic">Analyzing…</span>
            </div>
          ) : isFailed ? (
            <p className="text-xs text-zinc-600 italic">Analysis unavailable</p>
          ) : null}
        </div>
      </div>

      <div className="flex flex-shrink-0 items-center gap-2">
        {event.snapshot_path && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onViewSnapshot(event)}
          >
            <Image className="h-4 w-4" />
          </Button>
        )}
        {!event.acknowledged && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onAcknowledge(event.id)}
            className="text-emerald-400 hover:text-emerald-300"
          >
            <CheckCheck className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
