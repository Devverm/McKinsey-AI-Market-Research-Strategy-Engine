"""
backend/core/logging.py

Two things:
1. configure_logging() / get_logger() -- standard Python logging for
   day-to-day debugging (console output).
2. log_audit_event() -- a separate, structured (JSON-lines) audit trail
   of job lifecycle events (created, stage transitions, failures,
   completions). This is what satisfies "monitoring and audit logs" from
   the architecture's Deployment & Governance layer: it's queryable,
   append-only, and answers "what happened to job X and when" without
   needing to grep free-text debug logs.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.core.config import settings

_configured = False


def configure_logging() -> None:
    """Call once at app startup (backend/main.py does this)."""
    global _configured
    if _configured:
        return

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    Path(settings.AUDIT_LOG_PATH).parent.mkdir(parents=True, exist_ok=True)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_audit_event(event_type: str, job_id: str, **details) -> None:
    """
    Appends one JSON line to the audit log. Never raises -- a failure to
    write an audit log entry should not take down the pipeline that
    triggered it, so any I/O error here is caught and logged to the
    regular logger instead.

    Example event_types: "job_created", "stage_transition", "job_failed",
    "job_completed".
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "job_id": job_id,
        **details,
    }
    try:
        with open(settings.AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError as e:
        get_logger("audit").error(f"Failed to write audit log entry: {e}")