"use client";

import { Bell } from "lucide-react";
import { useUnreadCount } from "@/hooks/useWebSocket";
import { cn } from "@/lib/utils";

export function NotificationBell() {
  const unread = useUnreadCount();

  return (
    <button className="relative rounded-lg p-2 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100 transition-colors">
      <Bell className="h-5 w-5" />
      {unread > 0 && (
        <span
          className={cn(
            "absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-blue-600 text-[10px] font-bold text-white",
            unread > 9 && "w-5"
          )}
        >
          {unread > 99 ? "99+" : unread}
        </span>
      )}
    </button>
  );
}
