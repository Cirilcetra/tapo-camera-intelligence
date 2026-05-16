"use client";

import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { Camera, CameraCreate } from "@/types/camera";

export function useCameras() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<Camera[]>("/api/cameras");
      setCameras(res.data);
    } catch (e: unknown) {
      setError("Failed to load cameras");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetch(); // async — setState happens inside the resolved promise
  }, [fetch]);

  const createCamera = useCallback(
    async (data: CameraCreate): Promise<Camera> => {
      const res = await api.post<Camera>("/api/cameras", data);
      setCameras((prev) => [...prev, res.data]);
      return res.data;
    },
    []
  );

  const deleteCamera = useCallback(async (id: number) => {
    await api.delete(`/api/cameras/${id}`);
    setCameras((prev) => prev.filter((c) => c.id !== id));
  }, []);

  const testConnection = useCallback(
    async (
      data: CameraCreate
    ): Promise<{
      ok: boolean;
      message: string;
      tapoSupported?: boolean;
      rtspSupported?: boolean;
      mode?: string;
    }> => {
      try {
        const res = await api.post("/api/cameras/test", data);
        return {
          ok: true,
          message: res.data?.message ?? "Connection successful",
          tapoSupported: res.data?.tapo_supported ?? false,
          rtspSupported: res.data?.rtsp_supported ?? true,
          mode: res.data?.mode,
        };
      } catch (e: unknown) {
        const msg =
          (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          "Connection failed";
        return { ok: false, message: msg };
      }
    },
    []
  );

  const refreshCamera = useCallback(async (id: number): Promise<Camera | null> => {
    try {
      const res = await api.get<Camera>(`/api/cameras/${id}`);
      setCameras((prev) => prev.map((c) => (c.id === id ? res.data : c)));
      return res.data;
    } catch {
      return null;
    }
  }, []);

  return { cameras, loading, error, createCamera, deleteCamera, testConnection, refresh: fetch, refreshCamera };
}
