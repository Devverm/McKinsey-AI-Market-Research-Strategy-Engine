"""
backend/main.py

FastAPI entrypoint. Initializes SQLite on startup and mounts the
research-jobs router.

Run from the project root with:
    uvicorn backend.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import init_db
from backend.api.research_jobs import router as research_jobs_router
from backend.core.config import settings
from backend.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    logger.info("Application startup complete.")
    yield


app = FastAPI(
    title="AI Market Research & Strategy Engine",
    description="Agentic research pipeline: query intake through client-ready strategy brief.",
    version="0.1.0",
    lifespan=lifespan,
)

# Without this, a browser-based frontend on a different origin (e.g. a
# Vercel-deployed Next.js app calling a backend on Render/Fly.io) gets
# silently blocked by the browser itself -- CORS_ALLOWED_ORIGINS in
# backend/core/config.py controls which origins are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_jobs_router)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}