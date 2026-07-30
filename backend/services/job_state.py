"""
backend/services/job_state.py

Runs the LangGraph pipeline for a job in the background and persists state
to SQLite after every stage (not just at the end), using graph.stream()
rather than graph.invoke(). This is what lets the frontend poll a job and
see it move through stages live, instead of the API going silent for
however long the full pipeline takes.
"""

from __future__ import annotations

from ai.graph import build_graph
from ai.state import JobStatus, ResearchJobState
from backend.db.crud import update_job
from backend.core.logging import get_logger, log_audit_event

logger = get_logger(__name__)

# Built once per process and reused across jobs -- constructing a new
# graph (and new agent clients) per job would be wasteful.
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_pipeline_job(job_id: str, initial_state: ResearchJobState) -> None:
    """
    Intended to be scheduled as a FastAPI BackgroundTask. Streams the
    pipeline stage by stage, persisting to the DB after every step so
    GET /research-jobs/{job_id} always reflects current progress.

    Every stage transition and terminal outcome is also recorded to the
    audit log (backend/core/logging.py), independent of the SQLite state
    -- this gives a durable, append-only record of what happened to a job
    and when, even if the DB row is later overwritten.

    Any exception that escapes graph.stream() itself (as opposed to a
    node catching its own error and setting status=FAILED, which the
    nodes in ai/graph.py already do) is treated as an infrastructure
    failure and also persisted as a failed job, rather than crashing
    the background thread silently.
    """
    graph = _get_graph()
    latest_state = initial_state
    last_logged_stage = None

    logger.info(f"Job {job_id} starting pipeline run.")
    log_audit_event("job_started", job_id, query=initial_state.request.query)

    try:
        for step_output in graph.stream(initial_state, stream_mode="values"):
            latest_state = (
                ResearchJobState(**step_output)
                if isinstance(step_output, dict)
                else step_output
            )
            update_job(latest_state)

            if latest_state.stage.value != last_logged_stage:
                log_audit_event(
                    "stage_transition",
                    job_id,
                    stage=latest_state.stage.value,
                    status=latest_state.status.value,
                )
                last_logged_stage = latest_state.stage.value

        if latest_state.status == JobStatus.FAILED:
            logger.warning(f"Job {job_id} failed: {latest_state.error_message}")
            log_audit_event("job_failed", job_id, error=latest_state.error_message)
        else:
            logger.info(f"Job {job_id} completed with status {latest_state.status.value}.")
            log_audit_event("job_completed", job_id, final_status=latest_state.status.value)

    except Exception as e:
        latest_state.mark_failed(f"Pipeline infrastructure error: {e}")
        update_job(latest_state)
        logger.error(f"Job {job_id} hit an infrastructure error: {e}")
        log_audit_event("job_failed", job_id, error=str(e), infrastructure_error=True)