"""
backend/db/database.py

SQLite persistence for research jobs. ResearchJobState is a deeply nested
Pydantic object (plan, sources, evidence, themes, report all live inside
it), so rather than mapping it into relational columns we store the whole
state as a JSON blob per job, with a few flat columns (status, stage) kept
alongside purely so they're queryable/indexable without deserializing
every row.

Plain sqlite3 (stdlib) is used deliberately -- no ORM -- since the access
pattern here is simple key-value get/put by job_id, not relational queries.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "research_jobs.db"


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                state_json TEXT NOT NULL,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


@contextmanager
def get_connection():
    """
    Opens a fresh connection per call rather than sharing one across
    threads. FastAPI's BackgroundTasks run the pipeline in a separate
    thread from the request handler, and sqlite3 connections are not
    safe to share across threads by default -- opening per-call avoids
    that entirely at the cost of a small amount of overhead per query,
    which is negligible for this access pattern.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()