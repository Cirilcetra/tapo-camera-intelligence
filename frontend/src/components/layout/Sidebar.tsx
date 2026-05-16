"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Camera, LayoutDashboard, List, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/cameras", label: "Cameras", icon: Camera },
  { href: "/events", label: "Events", icon: List },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-60 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="flex h-14 items-center gap-2.5 border-b border-zinc-800 px-5">
        <Camera className="h-5 w-5 text-blue-400" />
        <span className="text-base font-bold tracking-tight text-zinc-100">
          CamWatcher
        </span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
              )}
            >
              <Icon className="h-4 w-4 flex-shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-800 px-5 py-3">
        <p className="text-xs text-zinc-600">CamWatcher MVP</p>
      </div>
    </aside>
  );
}
