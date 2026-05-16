"use client";

import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { Loader2, VideoOff, Zap } from "lucide-react";

interface CameraFeedProps {
  hlsUrl: string | null;
  className?: string;
  /**
   * When set, the player renders an explanatory placeholder instead of trying
   * to load HLS.  Currently only used for `cloud_account_no_rtsp`.
   */
  unavailableReason?: "cloud_account_no_rtsp" | null;
}

const MAX_RETRIES = 12;      // up to ~24s total wait
const RETRY_DELAY_MS = 2000; // retry every 2s while stream buffers

export function CameraFeed({ hlsUrl, className, unavailableReason }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCount = useRef(0);
  const [status, setStatus] = useState<"loading" | "playing" | "error">("loading");
  const [retrying, setRetrying] = useState(false);

  const clearRetry = () => {
    if (retryRef.current) {
      clearTimeout(retryRef.current);
      retryRef.current = null;
    }
  };

  const destroyHls = () => {
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
  };

  const attach = (url: string) => {
    const video = videoRef.current;
    if (!video) return;

    destroyHls();

    if (Hls.isSupported()) {
      const hls = new Hls({
        // Standard HLS — no LL-HLS mode (mediamtx uses fmp4 variant)
        enableWorker: true,
        maxBufferLength: 10,
        maxMaxBufferLength: 30,
      });
      hlsRef.current = hls;

      hls.loadSource(url);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        retryCount.current = 0;
        setRetrying(false);
        video.play().catch(() => {});
        setStatus("playing");
      });

      hls.on(Hls.Events.ERROR, (_, data) => {
        if (!data.fatal) return;

        const isNetworkError =
          data.type === Hls.ErrorTypes.NETWORK_ERROR &&
          (data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR ||
            data.details === Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT);

        // 404 during initial buffer → MediaMTX hasn't muxed 7 segments yet.
        // Retry with backoff until MAX_RETRIES.
        if (isNetworkError && retryCount.current < MAX_RETRIES) {
          retryCount.current += 1;
          setRetrying(true);
          destroyHls();
          clearRetry();
          retryRef.current = setTimeout(() => attach(url), RETRY_DELAY_MS);
        } else {
          setStatus("error");
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Safari native HLS
      video.src = url;
      video.addEventListener("loadedmetadata", () => {
        retryCount.current = 0;
        setRetrying(false);
        video.play().catch(() => {});
        setStatus("playing");
      });
      video.addEventListener("error", () => {
        if (retryCount.current < MAX_RETRIES) {
          retryCount.current += 1;
          setRetrying(true);
          retryRef.current = setTimeout(() => attach(url), RETRY_DELAY_MS);
        } else {
          setStatus("error");
        }
      });
    } else {
      setStatus("error");
    }
  };

  useEffect(() => {
    retryCount.current = 0;
    setRetrying(false);
    clearRetry();

    if (!hlsUrl) {
      setStatus("error");
      return;
    }

    setStatus("loading");
    attach(hlsUrl);

    return () => {
      clearRetry();
      destroyHls();
    };
    // attach is stable — only re-run when hlsUrl changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hlsUrl]);

  if (unavailableReason === "cloud_account_no_rtsp") {
    return (
      <div
        className={`relative flex flex-col items-center justify-center gap-3 overflow-hidden rounded-xl bg-zinc-900 px-6 text-center ${className ?? ""}`}
      >
        <Zap className="h-10 w-10 text-blue-400" />
        <div>
          <p className="text-sm font-medium text-zinc-200">Live video unavailable</p>
          <p className="mt-1 text-xs text-zinc-500 max-w-xs">
            This camera uses Tapo cloud-account auth, which doesn&apos;t grant RTSP access.
            Events still work — enable the camera-account in the Tapo app to add live video.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative overflow-hidden rounded-xl bg-zinc-900 ${className ?? ""}`}>
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        autoPlay
        muted
        playsInline
      />

      {status === "loading" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-zinc-900">
          <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
          {retrying && (
            <p className="text-xs text-zinc-500">
              Waiting for stream… ({retryCount.current}/{MAX_RETRIES})
            </p>
          )}
        </div>
      )}

      {status === "error" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-zinc-900">
          <VideoOff className="h-8 w-8 text-zinc-600" />
          <p className="text-sm text-zinc-500">Stream unavailable</p>
          {hlsUrl && (
            <button
              onClick={() => {
                retryCount.current = 0;
                setStatus("loading");
                attach(hlsUrl);
              }}
              className="mt-1 text-xs text-blue-400 underline hover:text-blue-300"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
