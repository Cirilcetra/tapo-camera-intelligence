"use client";

import { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { CameraStatus } from "@/types/camera";

interface StatusResult {
  camera_id: number;
  status: CameraStatus;
}

export function useCameraStatus(cameraId: number | null, pollMs = 10000) {
  const [status, setStatus] = useState<CameraStatus | null>(null);

  const poll = useCallback(async () => {
    if (!cameraId) return;
    try {
      const res = await api.get<StatusResult>(`/api/cameras/${cameraId}/status`);
      setStatus(res.data.status);
    } catch {
      setStatus("offline");
    }
  }, [cameraId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    poll(); // async — setState is called inside the resolved promise, not synchronously
    const id = setInterval(poll, pollMs);
    return () => clearInterval(id);
  }, [poll, pollMs]);

  return status;
}
