export type EventType = "motion" | "object_detected" | "manual";
export type EnrichmentStatus = "pending" | "done" | "failed" | "skipped";

export interface CamEvent {
  id: number;
  camera_id: number;
  camera_name?: string;
  type: EventType;
  motion_score: number | null;
  snapshot_path: string | null;
  ai_summary?: string | null;
  enrichment_status?: EnrichmentStatus | null;
  acknowledged: boolean;
  created_at: string;
  /** Present on search results only */
  score?: number;
}

export interface EventFilters {
  camera_id?: number;
  type?: EventType;
  since?: string;
  until?: string;
}
