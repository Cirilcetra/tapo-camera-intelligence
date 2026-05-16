"use client";

import { Camera } from "@/types/camera";
import { EventFilters, EventType } from "@/types/event";

interface EventFilterProps {
  cameras: Camera[];
  filters: EventFilters;
  onChange: (filters: EventFilters) => void;
}

const types: { value: EventType | ""; label: string }[] = [
  { value: "", label: "All Types" },
  { value: "motion", label: "Motion" },
  { value: "object_detected", label: "Object Detected" },
  { value: "manual", label: "Manual" },
];

export function EventFilter({ cameras, filters, onChange }: EventFilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <select
        className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={filters.camera_id ?? ""}
        onChange={(e) =>
          onChange({ ...filters, camera_id: e.target.value ? Number(e.target.value) : undefined })
        }
      >
        <option value="">All Cameras</option>
        {cameras.map((c) => (
          <option key={c.id} value={c.id}>
            {c.name}
          </option>
        ))}
      </select>

      <select
        className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={filters.type ?? ""}
        onChange={(e) =>
          onChange({ ...filters, type: (e.target.value as EventType) || undefined })
        }
      >
        {types.map((t) => (
          <option key={t.value} value={t.value}>
            {t.label}
          </option>
        ))}
      </select>

      <input
        type="date"
        className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={filters.since ?? ""}
        onChange={(e) => onChange({ ...filters, since: e.target.value || undefined })}
        placeholder="From"
      />

      <input
        type="date"
        className="rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        value={filters.until ?? ""}
        onChange={(e) => onChange({ ...filters, until: e.target.value || undefined })}
        placeholder="To"
      />

      {Object.values(filters).some(Boolean) && (
        <button
          onClick={() => onChange({})}
          className="text-xs text-zinc-500 hover:text-zinc-300 underline"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
