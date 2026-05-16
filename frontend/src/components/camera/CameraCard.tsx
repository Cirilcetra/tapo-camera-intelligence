"use client";

import { Camera } from "@/types/camera";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { timeAgo } from "@/lib/utils";
import { useCameraStatus } from "@/hooks/useCameraStatus";
import { Camera as CameraIcon, Trash2, Wifi, WifiOff, Zap, Radio } from "lucide-react";
import Link from "next/link";

const statusBadge: Record<string, { variant: "success" | "error" | "warning" | "info"; label: string }> = {
  online: { variant: "success", label: "Online" },
  offline: { variant: "error", label: "Offline" },
  error: { variant: "error", label: "Error" },
  connecting: { variant: "warning", label: "Connecting" },
};

interface CameraCardProps {
  camera: Camera;
  onDelete: (id: number) => void;
}

export function CameraCard({ camera, onDelete }: CameraCardProps) {
  const polledStatus = useCameraStatus(camera.id);
  const currentStatus = polledStatus ?? camera.status;
  const badge = statusBadge[currentStatus] ?? { variant: "info" as const, label: currentStatus };

  return (
    <Card className="flex flex-col gap-3">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex-shrink-0 rounded-lg bg-zinc-800 p-2">
            <CameraIcon className="h-4 w-4 text-zinc-400" />
          </div>
          <div className="min-w-0">
            <p className="truncate font-medium text-zinc-100">{camera.name}</p>
            <p className="text-xs text-zinc-500">{camera.ip}</p>
          </div>
        </div>
        <Badge variant={badge.variant}>{badge.label}</Badge>
      </div>

      <div className="flex items-center gap-1.5 text-xs text-zinc-500">
        {currentStatus === "online" ? (
          <Wifi className="h-3.5 w-3.5 text-emerald-400" />
        ) : (
          <WifiOff className="h-3.5 w-3.5 text-zinc-600" />
        )}
        {camera.last_seen ? `Last seen ${timeAgo(camera.last_seen)}` : "Never connected"}
      </div>

      <div className="flex items-center gap-1.5 text-xs">
        {camera.provider === "tapo" ? (
          <>
            <Zap className="h-3 w-3 text-blue-400" />
            <span className="text-blue-400">Tapo native</span>
          </>
        ) : (
          <>
            <Radio className="h-3 w-3 text-amber-500" />
            <span className="text-amber-500">RTSP / OpenCV</span>
          </>
        )}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <Link href={`/dashboard?camera=${camera.id}`} className="flex-1">
          <Button variant="secondary" size="sm" className="w-full">
            View Feed
          </Button>
        </Link>
        <Button
          variant="ghost"
          size="sm"
          className="text-red-400 hover:text-red-300 hover:bg-red-900/20"
          onClick={() => onDelete(camera.id)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>
    </Card>
  );
}
