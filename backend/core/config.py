"""
backend/core/config.py

Single source of truth for environment/config values. Every agent and
service should import `settings` from here instead of calling
os.environ[...] directly -- that scattered pattern meant API keys were
read in six different files with no single place to see what the app
actually needs configured, and no validation until the first agent call
happened to fail deep in a pipeline run.

Uses pydantic-settings, so missing required values fail fast and loudly
at process startup (e.g. `uvicorn backend.main:app`) rather than 20
minutes into a research job when the report agent finally gets called.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Required API keys ---
    GEMINI_API_KEY: str
    TAVILY_API_KEY: str

    # --- Model selection (centralized so a model bump is a one-line change) ---
    # GEMINI_MODEL is used for Planning and Report Generation -- stages that
    # need stronger reasoning and only run once per job.
    # GEMINI_EXTRACTION_MODEL is used for Extraction and Validation -- stages
    # that scale with the number of sub-questions/sources, so a lighter model
    # keeps per-job Gemini usage down and draws from a separate free-tier
    # quota bucket than GEMINI_MODEL.
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_EXTRACTION_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # --- Storage ---
    DB_PATH: str = "research_jobs.db"
    CHROMA_DB_PATH: str = "./chroma_db"

    # --- Browsing tuning ---
    BROWSER_RESULTS_PER_TASK: int = 5

    # --- Validation tuning ---
    VALIDATION_STALE_MONTHS_DEFAULT: int = 18
    VALIDATION_DUPLICATE_SIMILARITY_THRESHOLD: float = 0.85

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    AUDIT_LOG_PATH: str = "./logs/audit.log"

    # --- CORS ---
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


# Constructed once at import time. If GEMINI_API_KEY/TAVILY_API_KEY are
# missing from the environment or .env file, this raises immediately --
# by design, so misconfiguration is caught at startup, not mid-pipeline.
settings = Settings()