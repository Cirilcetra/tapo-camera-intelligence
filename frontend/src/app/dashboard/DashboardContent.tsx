"use client";

import { useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { useCameras } from "@/hooks/useCameras";
import { useEvents } from "@/hooks/useEvents";
import { useWebSocket } from "@/hooks/useWebSocket";
import { CameraFeed } from "@/components/camera/CameraFeed";
import { EventCard } from "@/components/events/EventCard";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Spinner } from "@/components/ui/Spinner";
import { Modal } from "@/components/ui/Modal";
import { Camera, Activity, AlertCircle, Wifi } from "lucide-react";
import { CamEvent } from "@/types/event";
import api from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DashboardContent() {
  const searchParams = useSearchParams();
  const { cameras, loading: camsLoading } = useCameras();
  const [selectedCameraId, setSelectedCameraId] = useState<number | null>(null);
  const [hlsUrl, setHlsUrl] = useState<string | null>(null);
  const [feedReason, setFeedReason] = useState<"cloud_account_no_rtsp" | null>(null);
  const [snapshotEvent, setSnapshotEvent] = useState<CamEvent | null>(null);
  const [liveEvents, setLiveEvents] = useState<CamEvent[]>([]);

  const { events, loading: eventsLoading, acknowledgeEvent } = useEvents(
    selectedCameraId ? { camera_id: selectedCameraId } : {}
  );

  const selectedCamera = cameras.find((c) => c.id === selectedCameraId);

  useEffect(() => {
    const paramId = searchParams.get("camera");
    const next = paramId
      ? Number(paramId)
      : cameras.length > 0 && !selectedCameraId
      ? cameras[0].id
      : null;
    if (next !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSelectedCameraId(next);
    }
  }, [searchParams, cameras]); // selectedCameraId intentionally omitted to avoid loop

  useEffect(() => {
    if (!selectedCameraId) return;
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setHlsUrl(null);
    setFeedReason(null);
    api
      .get(`/api/cameras/${selectedCameraId}/stream`)
      .then((r) => {
        if (cancelled) return;
        setHlsUrl(r.data?.hls_url ?? null);
        setFeedReason(r.data?.reason ?? null);
      })
      .catch(() => {
        if (!cancelled) setHlsUrl(null);
      });
    return () => { cancelled = true; };
  }, [selectedCameraId]);

  const onLiveEvent = useCallback(
    (event: CamEvent) => {
      if (selectedCameraId && event.camera_id !== selectedCameraId) return;
      setLiveEvents((prev) => [event, ...prev].slice(0, 5));
    },
    [selectedCameraId]
  );

  useWebSocket(onLiveEvent, undefined);

  const recentEvents = liveEvents.length > 0 ? liveEvents : events.slice(0, 5);
  const onlineCount = cameras.filter((c) => c.status === "online").length;

  return (
    <div className="space-y-6">
      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard icon={Camera} label="Cameras" value={cameras.length} />
        <StatCard icon={Wifi} label="Online" value={onlineCount} accent="emerald" />
        <StatCard icon={Activity} label="Events Today" value={events.length} />
        <StatCard
          icon={AlertCircle}
          label="Unacked"
          value={events.filter((e) => !e.acknowledged).length}
          accent="amber"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Camera feed panel */}
        <div className="space-y-4 lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Live Feed</CardTitle>
              {camsLoading ? (
                <Spinner />
              ) : (
                <select
                  className="rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-1.5 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={selectedCameraId ?? ""}
                  onChange={(e) =>
                    setSelectedCameraId(e.target.value ? Number(e.target.value) : null)
                  }
                >
                  {cameras.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              )}
            </CardHeader>
            {selectedCamera && (
              <div className="mb-2 flex items-center gap-2">
                <Badge
                  variant={
                    selectedCamera.status === "online"
                      ? "success"
                      : selectedCamera.status === "error"
                      ? "error"
                      : "warning"
                  }
                >
                  {selectedCamera.status}
                </Badge>
                <span className="text-xs text-zinc-500">{selectedCamera.ip}</span>
              </div>
            )}
            <CameraFeed hlsUrl={hlsUrl} unavailableReason={feedReason} className="aspect-video w-full" />
          </Card>
        </div>

        {/* Recent events strip */}
        <div>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Recent Events</CardTitle>
              {liveEvents.length > 0 && <Badge variant="info">Live</Badge>}
            </CardHeader>
            {eventsLoading ? (
              <div className="flex justify-center py-8">
                <Spinner />
              </div>
            ) : recentEvents.length === 0 ? (
              <p className="py-8 text-center text-sm text-zinc-500">No recent events</p>
            ) : (
              <div className="space-y-2">
                {recentEvents.map((ev) => (
                  <EventCard
                    key={ev.id}
                    event={ev}
                    onViewSnapshot={setSnapshotEvent}
                    onAcknowledge={acknowledgeEvent}
                  />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

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

function StatCard({
  icon: Icon,
  label,
  value,
  accent,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  accent?: "emerald" | "amber" | "red";
}) {
  const colors: Record<string, string> = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    red: "text-red-400",
  };
  const color = accent ? colors[accent] : "text-zinc-100";

  return (
    <Card className="flex items-center gap-4">
      <div className="rounded-lg bg-zinc-800 p-2.5">
        <Icon className="h-5 w-5 text-zinc-400" />
      </div>
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className={`text-2xl font-bold ${color}`}>{value}</p>
      </div>
    </Card>
  );
}
