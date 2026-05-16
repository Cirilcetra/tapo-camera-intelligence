"use client";

import { useState, useEffect } from "react";
import api from "@/lib/api";
import { Card, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

interface Settings {
  snapshot_dir: string;
  motion_threshold: number;
  frame_skip: number;
  mediamtx_url: string;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<Settings>("/api/settings")
      .then((r) => setSettings(r.data))
      .catch(() =>
        setSettings({
          snapshot_dir: "/media/snapshots",
          motion_threshold: 5000,
          frame_skip: 5,
          mediamtx_url: "http://localhost:8888",
        })
      )
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setError(null);
    try {
      await api.put("/api/settings", settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner size={28} />
      </div>
    );
  }

  if (!settings) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h2 className="text-xl font-bold text-zinc-100">Settings</h2>
        <p className="mt-0.5 text-sm text-zinc-500">Configure CamWatcher behaviour</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Storage</CardTitle>
        </CardHeader>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-300">
            Snapshot Directory
          </label>
          <input
            type="text"
            readOnly
            value={settings.snapshot_dir}
            className="w-full cursor-not-allowed rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-400"
          />
          <p className="mt-1 text-xs text-zinc-600">Configured via backend .env — read only</p>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Motion Detection</CardTitle>
        </CardHeader>
        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">
              Motion Threshold:{" "}
              <span className="text-blue-400">{settings.motion_threshold}</span>
            </label>
            <input
              type="range"
              min={500}
              max={50000}
              step={500}
              value={settings.motion_threshold}
              onChange={(e) =>
                setSettings((s) => s ? { ...s, motion_threshold: Number(e.target.value) } : s)
              }
              className="w-full accent-blue-500"
            />
            <div className="mt-1 flex justify-between text-xs text-zinc-600">
              <span>500 (sensitive)</span>
              <span>50000 (less sensitive)</span>
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">
              Frame Skip:{" "}
              <span className="text-blue-400">{settings.frame_skip}</span>
            </label>
            <input
              type="range"
              min={1}
              max={30}
              step={1}
              value={settings.frame_skip}
              onChange={(e) =>
                setSettings((s) => s ? { ...s, frame_skip: Number(e.target.value) } : s)
              }
              className="w-full accent-blue-500"
            />
            <div className="mt-1 flex justify-between text-xs text-zinc-600">
              <span>1 (every frame)</span>
              <span>30 (every 30th)</span>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Stream</CardTitle>
        </CardHeader>
        <div>
          <label className="mb-1.5 block text-sm font-medium text-zinc-300">
            MediaMTX HLS URL
          </label>
          <input
            type="text"
            readOnly
            value={settings.mediamtx_url}
            className="w-full cursor-not-allowed rounded-lg border border-zinc-700 bg-zinc-800/50 px-3 py-2 text-sm text-zinc-400"
          />
          <p className="mt-1 text-xs text-zinc-600">Configured via backend .env — read only</p>
        </div>
      </Card>

      {error && (
        <p className="rounded-lg border border-red-800 bg-red-900/20 px-4 py-3 text-sm text-red-400">
          {error}
        </p>
      )}

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} loading={saving}>
          {saved ? "Saved!" : "Save Settings"}
        </Button>
        {saved && <span className="text-sm text-emerald-400">Settings saved successfully</span>}
      </div>
    </div>
  );
}
