"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCameras } from "@/hooks/useCameras";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  CheckCircle,
  XCircle,
  ArrowLeft,
  Zap,
  Radio,
  Shuffle,
  KeyRound,
  AtSign,
  AlertTriangle,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import type { PreferredProvider, AuthMethod } from "@/types/camera";

interface FormState {
  name: string;
  ip: string;
  username: string;
  password: string;
  rtsp_path: string;
}

interface TestResult {
  ok: boolean;
  message: string;
  tapoSupported?: boolean;
  rtspSupported?: boolean;
  mode?: string;
}

// ─────────────────────────────────────────────
// Camera type options
// ─────────────────────────────────────────────
const PROVIDER_OPTIONS: Array<{
  id: PreferredProvider;
  icon: React.ElementType;
  label: string;
  sublabel: string;
  iconColor: string;
  borderActive: string;
  bgActive: string;
}> = [
  {
    id: "auto",
    icon: Shuffle,
    label: "Auto-detect",
    sublabel: "Try Tapo first, fall back to RTSP",
    iconColor: "text-zinc-300",
    borderActive: "border-zinc-400",
    bgActive: "bg-zinc-800",
  },
  {
    id: "tapo",
    icon: Zap,
    label: "Tapo (native events)",
    sublabel: "On-device motion, person, vehicle & pet",
    iconColor: "text-blue-400",
    borderActive: "border-blue-500",
    bgActive: "bg-blue-950/40",
  },
  {
    id: "rtsp",
    icon: Radio,
    label: "RTSP / Generic",
    sublabel: "Any IP camera — CP Plus, Hikvision, etc.",
    iconColor: "text-amber-400",
    borderActive: "border-amber-500",
    bgActive: "bg-amber-950/30",
  },
];

// ─────────────────────────────────────────────
// Auth-method options (only shown when camera type is Tapo-capable)
// ─────────────────────────────────────────────
const AUTH_OPTIONS: Array<{
  id: AuthMethod;
  icon: React.ElementType;
  label: string;
  sublabel: string;
}> = [
  {
    id: "camera_account",
    icon: KeyRound,
    label: "Camera Account",
    sublabel: "Username/password from Tapo app → Advanced Settings",
  },
  {
    id: "cloud_account",
    icon: AtSign,
    label: "Tapo App Login",
    sublabel: "Your Tapo app email & password",
  },
];

// Per-mode field hints
type HintMode = "rtsp" | "camera_account" | "cloud_account";
const HINTS: Record<HintMode, { usernameLabel: string; usernamePlaceholder: string; usernameHint: string; passwordHint: string }> = {
  rtsp: {
    usernameLabel: "Username",
    usernamePlaceholder: "admin",
    usernameHint: "RTSP username (often admin)",
    passwordHint: "RTSP password",
  },
  camera_account: {
    usernameLabel: "Camera-Account Username",
    usernamePlaceholder: "camera_user",
    usernameHint: "From Tapo app → Settings → Advanced Settings → Camera Account",
    passwordHint: "From the same Camera Account screen",
  },
  cloud_account: {
    usernameLabel: "Tapo Email",
    usernamePlaceholder: "you@example.com",
    usernameHint: "The email you use to sign in to the Tapo app",
    passwordHint: "Your Tapo app password",
  },
};

export default function AddCameraPage() {
  const router = useRouter();
  const { createCamera, testConnection } = useCameras();

  const [preferredProvider, setPreferredProvider] = useState<PreferredProvider>("auto");
  const [authMethod, setAuthMethod] = useState<AuthMethod>("camera_account");
  const [form, setForm] = useState<FormState>({
    name: "",
    ip: "",
    username: "",
    password: "",
    rtsp_path: "stream1",
  });
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Partial<FormState>>({});

  const isTapoCapable = preferredProvider !== "rtsp";
  const hintMode: HintMode = preferredProvider === "rtsp" ? "rtsp" : authMethod;
  const hints = HINTS[hintMode];

  const set = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    setTestResult(null);
  };

  const selectProvider = (p: PreferredProvider) => {
    setPreferredProvider(p);
    setTestResult(null);
  };

  const selectAuth = (m: AuthMethod) => {
    setAuthMethod(m);
    setTestResult(null);
  };

  const validate = () => {
    const errs: Partial<FormState> = {};
    if (!form.name.trim()) errs.name = "Required";
    if (!form.ip.trim()) errs.ip = "Required";
    if (!form.username.trim()) errs.username = "Required";
    if (!form.password.trim()) errs.password = "Required";
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleTest = async () => {
    if (!validate()) return;
    setTesting(true);
    const result = await testConnection({
      ...form,
      preferred_provider: preferredProvider,
      auth_method: authMethod,
    });
    setTestResult(result);
    setTesting(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      await createCamera({
        ...form,
        preferred_provider: preferredProvider,
        auth_method: authMethod,
      });
      router.push("/cameras");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        "Failed to add camera";
      setTestResult({ ok: false, message: msg });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/cameras">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
        </Link>
        <div>
          <h2 className="text-xl font-bold text-zinc-100">Add Camera</h2>
          <p className="text-sm text-zinc-500">Connect a Tapo, RTSP, or generic IP camera</p>
        </div>
      </div>

      {/* Camera type selector */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-zinc-300">Camera type</p>
        <div className="grid grid-cols-3 gap-2">
          {PROVIDER_OPTIONS.map(({ id, icon: Icon, label, sublabel, iconColor, borderActive, bgActive }) => {
            const active = preferredProvider === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => selectProvider(id)}
                className={cn(
                  "flex flex-col items-center gap-1.5 rounded-xl border px-3 py-3 text-center transition-all",
                  active
                    ? `${borderActive} ${bgActive}`
                    : "border-zinc-700 bg-zinc-900 hover:border-zinc-600 hover:bg-zinc-800/60"
                )}
              >
                <Icon className={cn("h-5 w-5", active ? iconColor : "text-zinc-500")} />
                <span className={cn("text-xs font-medium leading-tight", active ? "text-zinc-100" : "text-zinc-400")}>
                  {label}
                </span>
                <span className="hidden text-[10px] leading-tight text-zinc-500 sm:block">{sublabel}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Auth method sub-selector — only relevant for Tapo */}
      {isTapoCapable && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-zinc-300">Auth method</p>
          <div className="grid grid-cols-2 gap-2">
            {AUTH_OPTIONS.map(({ id, icon: Icon, label, sublabel }) => {
              const active = authMethod === id;
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => selectAuth(id)}
                  className={cn(
                    "flex items-start gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-all",
                    active
                      ? "border-blue-500 bg-blue-950/30"
                      : "border-zinc-700 bg-zinc-900 hover:border-zinc-600 hover:bg-zinc-800/60"
                  )}
                >
                  <Icon className={cn("mt-0.5 h-4 w-4 flex-shrink-0", active ? "text-blue-400" : "text-zinc-500")} />
                  <div className="min-w-0">
                    <p className={cn("text-xs font-medium leading-tight", active ? "text-zinc-100" : "text-zinc-400")}>
                      {label}
                    </p>
                    <p className="mt-0.5 text-[10px] leading-tight text-zinc-500">{sublabel}</p>
                  </div>
                </button>
              );
            })}
          </div>

          {authMethod === "cloud_account" && (
            <div className="flex items-start gap-2 rounded-lg border border-amber-700/40 bg-amber-900/15 px-3 py-2 text-xs text-amber-300">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
              <p>
                Live video feed still requires the camera-account to be enabled in the Tapo app
                (RTSP only accepts those credentials). Without it, you&apos;ll get events but no
                live stream.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Form */}
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Camera Name</label>
            <input
              type="text"
              value={form.name}
              onChange={set("name")}
              placeholder="Front Door"
              className={cn(
                "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500",
                errors.name ? "border-red-600" : "border-zinc-700"
              )}
            />
            {errors.name && <p className="mt-1 text-xs text-red-400">{errors.name}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">IP Address</label>
            <input
              type="text"
              value={form.ip}
              onChange={set("ip")}
              placeholder="192.168.1.100"
              className={cn(
                "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500",
                errors.ip ? "border-red-600" : "border-zinc-700"
              )}
            />
            {errors.ip && <p className="mt-1 text-xs text-red-400">{errors.ip}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">{hints.usernameLabel}</label>
            <input
              type={hintMode === "cloud_account" ? "email" : "text"}
              value={form.username}
              onChange={set("username")}
              placeholder={hints.usernamePlaceholder}
              className={cn(
                "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500",
                errors.username ? "border-red-600" : "border-zinc-700"
              )}
            />
            {!errors.username && <p className="mt-1 text-xs text-zinc-500">{hints.usernameHint}</p>}
            {errors.username && <p className="mt-1 text-xs text-red-400">{errors.username}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">Password</label>
            <input
              type="password"
              value={form.password}
              onChange={set("password")}
              placeholder="••••••••"
              className={cn(
                "w-full rounded-lg border bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500",
                errors.password ? "border-red-600" : "border-zinc-700"
              )}
            />
            {!errors.password && <p className="mt-1 text-xs text-zinc-500">{hints.passwordHint}</p>}
            {errors.password && <p className="mt-1 text-xs text-red-400">{errors.password}</p>}
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-zinc-300">RTSP Path</label>
            <input
              type="text"
              value={form.rtsp_path}
              onChange={set("rtsp_path")}
              placeholder="stream1"
              className="w-full rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-zinc-500">
              {preferredProvider === "rtsp"
                ? "Check your camera's RTSP URL — common values: stream1, h264Preview_01_main, ch01/0"
                : "Use stream1 for main stream, stream2 for sub-stream (Tapo default)"}
            </p>
          </div>

          {/* Test result banner */}
          {testResult && (
            <div
              className={cn(
                "space-y-1.5 rounded-lg border px-3 py-2.5 text-sm",
                testResult.ok
                  ? "border-emerald-700/40 bg-emerald-900/20 text-emerald-300"
                  : "border-red-700/40 bg-red-900/20 text-red-300"
              )}
            >
              <div className="flex items-center gap-2">
                {testResult.ok ? (
                  <CheckCircle className="h-4 w-4 flex-shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 flex-shrink-0" />
                )}
                <span>{testResult.message}</span>
              </div>

              {testResult.ok && (
                <div className="space-y-1 pl-6 text-xs">
                  {testResult.mode && (
                    <div className="flex items-center gap-1.5">
                      {testResult.tapoSupported ? (
                        <Zap className="h-3.5 w-3.5 flex-shrink-0 text-blue-400" />
                      ) : (
                        <Radio className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" />
                      )}
                      <span className={testResult.tapoSupported ? "text-blue-300" : "text-amber-300"}>
                        {testResult.mode}
                      </span>
                    </div>
                  )}
                  {testResult.rtspSupported === false && (
                    <div className="flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-amber-400" />
                      <span className="text-amber-300">
                        RTSP not accessible — events will work, but live video will not
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={handleTest} loading={testing} className="flex-1">
              Test Connection
            </Button>
            <Button type="submit" loading={saving} className="flex-1">
              Add Camera
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
