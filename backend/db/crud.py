"""
backend/db/crud.py

Get/put operations for job state, storing ResearchJobState as a JSON blob
per the schema in ai/state.py. This module knows about ai.state but the
rest of the backend should go through these functions rather than touching
sqlite directly, so the storage mechanism can be swapped later without
touching API or pipeline code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from ai.state import ResearchJobState
from backend.db.database import get_connection


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(state: ResearchJobState) -> None:
    now = _utcnow_iso()
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, status, stage, state_json, error_message, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.job_id,
                state.status.value,
                state.stage.value,
                state.model_dump_json(),
                state.error_message,
                now,
                now,
            ),
        )
        conn.commit()


def update_job(state: ResearchJobState) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = ?, stage = ?, state_json = ?, error_message = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (
                state.status.value,
                state.stage.value,
                state.model_dump_json(),
                state.error_message,
                _utcnow_iso(),
                state.job_id,
            ),
        )
        conn.commit()


def get_job(job_id: str) -> Optional[ResearchJobState]:
    with get_connection() as conn:
        row = conn.execute("SELECT state_json FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    return ResearchJobState.model_validate_json(row["state_json"])


def list_jobs(limit: int = 50) -> list[ResearchJobState]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT state_json FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [ResearchJobState.model_validate_json(row["state_json"]) for row in rows]