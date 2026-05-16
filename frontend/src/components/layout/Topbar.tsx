"use client";

import { NotificationBell } from "./NotificationBell";
import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/cameras": "Cameras",
  "/events": "Events",
  "/settings": "Settings",
};

export function Topbar() {
  const pathname = usePathname();
  const title =
    Object.entries(titles).find(([k]) => pathname === k || pathname.startsWith(k + "/"))?.[1] ?? "CamWatcher";

  return (
    <header className="flex h-14 items-center justify-between border-b border-zinc-800 bg-zinc-950 px-6">
      <h1 className="text-sm font-semibold text-zinc-100">{title}</h1>
      <div className="flex items-center gap-2">
        <NotificationBell />
      </div>
    </header>
  );
}
