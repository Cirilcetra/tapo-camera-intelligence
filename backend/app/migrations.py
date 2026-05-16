"""
Idempotent schema migrations for SQLite.

SQLite does not support IF NOT EXISTS on ALTER TABLE, so we check
PRAGMA table_info before each addition. Safe to run on every startup.
"""
import logging

from sqlalchemy import text

from app.database import engine

logger = logging.getLogger(__name__)

_CAMERAS_COLUMNS: list[tuple[str, str]] = [
    ("provider", "TEXT NOT NULL DEFAULT 'rtsp'"),
    ("preferred_provider", "TEXT NOT NULL DEFAULT 'auto'"),
    ("auth_method", "TEXT NOT NULL DEFAULT 'camera_account'"),
]

_EVENTS_COLUMNS: list[tuple[str, str]] = [
    ("enrichment_status", "TEXT DEFAULT 'pending'"),
    ("embedding", "BLOB"),
]


def _migrate_table(conn, table: str, columns: list[tuple[str, str]]) -> None:
    result = conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in result.fetchall()}
    for col_name, col_def in columns:
        if col_name not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
            conn.commit()
            logger.info("Migration: added column %s.%s", table, col_name)
        else:
            logger.debug("Migration: %s.%s already exists, skipping", table, col_name)


def run_migrations() -> None:
    with engine.connect() as conn:
        _migrate_table(conn, "cameras", _CAMERAS_COLUMNS)
        _migrate_table(conn, "events", _EVENTS_COLUMNS)
