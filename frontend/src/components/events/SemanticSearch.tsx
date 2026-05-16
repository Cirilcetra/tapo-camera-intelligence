"use client";

import { useState, useRef, useCallback } from "react";
import { Search, X, Loader2 } from "lucide-react";
import api from "@/lib/api";
import { CamEvent } from "@/types/event";

interface SemanticSearchProps {
  onResults: (results: CamEvent[], query: string) => void;
  onClear: () => void;
  isActive: boolean;
}

export function SemanticSearch({ onResults, onClear, isActive }: SemanticSearchProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const runSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        onClear();
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await api.get<CamEvent[]>("/api/events/search", {
          params: { q: q.trim(), top_k: 30 },
        });
        onResults(res.data, q.trim());
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          "Search failed. Is OPENAI_API_KEY configured?";
        setError(msg);
        onClear();
      } finally {
        setLoading(false);
      }
    },
    [onResults, onClear],
  );

  const handleChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!value.trim()) {
      onClear();
      setError(null);
      return;
    }
    debounceRef.current = setTimeout(() => runSearch(value), 500);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (debounceRef.current) clearTimeout(debounceRef.current);
    runSearch(query);
  };

  const handleClear = () => {
    setQuery("");
    setError(null);
    onClear();
  };

  return (
    <div className="space-y-2">
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <Search className="absolute left-3 h-4 w-4 text-zinc-500 pointer-events-none" />
        <input
          type="text"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Search events by meaning… e.g. &quot;delivery person at night&quot;"
          className="w-full rounded-lg border border-zinc-700 bg-zinc-900 py-2.5 pl-9 pr-10 text-sm text-zinc-100 placeholder-zinc-600 outline-none ring-offset-zinc-950 transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/40"
        />
        {loading && (
          <Loader2 className="absolute right-3 h-4 w-4 animate-spin text-violet-400" />
        )}
        {!loading && (isActive || query) && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 rounded p-0.5 text-zinc-500 hover:text-zinc-300 transition"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </form>

      {isActive && !loading && !error && (
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-violet-700/60 bg-violet-950/40 px-3 py-0.5 text-xs text-violet-300">
            <Search className="h-3 w-3" />
            Semantic search active
          </span>
          <button
            onClick={handleClear}
            className="text-xs text-zinc-500 underline hover:text-zinc-300 transition"
          >
            Clear
          </button>
        </div>
      )}

      {error && (
        <p className="text-xs text-red-400">{error}</p>
      )}
    </div>
  );
}
