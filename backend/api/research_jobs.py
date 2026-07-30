"""
backend/api/research_jobs.py

Endpoints for submitting a research job and polling its status/result.
Submission returns immediately with a job_id; the actual pipeline run
happens in a FastAPI BackgroundTask via backend/services/job_state.py,
persisting progress to SQLite after every stage.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from ai.state import ResearchJobState, ResearchRequest
from backend.db.crud import create_job, get_job, list_jobs
from backend.services.job_state import run_pipeline_job

router = APIRouter(prefix="/research-jobs", tags=["research-jobs"])


@router.post("")
def submit_research_job(request: ResearchRequest, background_tasks: BackgroundTasks) -> dict:
    if not request.is_sufficiently_scoped():
        raise HTTPException(
            status_code=422,
            detail="Research query is too short/vague to plan against. Add more detail.",
        )

    state = ResearchJobState(request=request)
    create_job(state)

    background_tasks.add_task(run_pipeline_job, state.job_id, state)

    return {"job_id": state.job_id, "status": state.status.value, "stage": state.stage.value}


@router.get("/{job_id}")
def get_research_job(job_id: str) -> ResearchJobState:
    state = get_job(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No job found with id '{job_id}'")
    return state


@router.get("")
def list_research_jobs(limit: int = 50) -> list[ResearchJobState]:
    return list_jobs(limit=limit)