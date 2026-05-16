"""
SemanticIndex — in-memory numpy cosine-similarity index over event embeddings.

Lifecycle:
  - Call `build_from_db()` once on startup to load all existing embeddings.
  - Call `add(event_id, vector)` after each enrichment to keep the index live.
  - Call `search(query_vector, top_k, min_score)` from the search route.

Thread safety: a threading.Lock guards all mutations and reads of the
internal arrays. Reads are fast (numpy matmul on a copy) so contention is low.

Storage: embeddings are kept as a (N, 1536) float32 numpy matrix in memory
alongside a parallel list of event ids. The matrix is rebuilt from DB on
every server restart; nothing is persisted to disk separately.
"""
import logging
import threading
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_EMBED_DIM = 1536  # text-embedding-3-small


class SemanticIndex:
    def __init__(self):
        self._lock = threading.Lock()
        self._ids: list[int] = []
        self._matrix: Optional[np.ndarray] = None  # shape (N, 1536), float32

    # ------------------------------------------------------------------
    # Build on startup
    # ------------------------------------------------------------------

    def build_from_db(self) -> None:
        """Load all events with embeddings from SQLite into the in-memory index."""
        from app.database import SessionLocal
        from app.models.event import Event

        db = SessionLocal()
        try:
            rows = (
                db.query(Event.id, Event.embedding)
                .filter(Event.embedding.isnot(None))
                .all()
            )
            ids = []
            vecs = []
            for event_id, blob in rows:
                if blob and len(blob) == _EMBED_DIM * 4:  # 4 bytes per float32
                    arr = np.frombuffer(blob, dtype=np.float32).copy()
                    ids.append(event_id)
                    vecs.append(arr)

            with self._lock:
                self._ids = ids
                if vecs:
                    self._matrix = np.stack(vecs, axis=0)  # (N, 1536)
                else:
                    self._matrix = None

            logger.info("SemanticIndex: loaded %d embeddings from DB", len(ids))
        except Exception as exc:
            logger.error("SemanticIndex.build_from_db error: %s", exc)
        finally:
            db.close()

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def add(self, event_id: int, vector: np.ndarray) -> None:
        """Append a new (event_id, vector) pair to the in-memory index."""
        vec = vector.astype(np.float32)
        with self._lock:
            self._ids.append(event_id)
            if self._matrix is None:
                self._matrix = vec.reshape(1, -1)
            else:
                self._matrix = np.vstack([self._matrix, vec.reshape(1, -1)])
        logger.debug("SemanticIndex.add: event_id=%d, total=%d", event_id, len(self._ids))

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 20,
        min_score: float = 0.2,
    ) -> list[tuple[int, float]]:
        """
        Return [(event_id, cosine_score), ...] sorted by descending score.
        Only includes results with score >= min_score.
        """
        with self._lock:
            if self._matrix is None or len(self._ids) == 0:
                return []
            mat = self._matrix.copy()
            ids = list(self._ids)

        q = query_vector.astype(np.float32)

        # Normalise query
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # Normalise matrix rows
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        mat_normed = mat / norms

        scores = mat_normed @ q  # (N,)

        k = min(top_k, len(ids))
        top_indices = np.argpartition(scores, -k)[-k:]
        top_indices = top_indices[np.argsort(scores[top_indices])[::-1]]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score >= min_score:
                results.append((ids[idx], score))

        return results

    def size(self) -> int:
        with self._lock:
            return len(self._ids)


# Module-level singleton shared by enricher and search route
semantic_index = SemanticIndex()
