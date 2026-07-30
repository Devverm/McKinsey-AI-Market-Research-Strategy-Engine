"""
ai/state.py

Canonical data contracts for the AI Market Research & Strategy Engine.

This module defines the SINGLE source of truth for every shape of data that
flows through the LangGraph pipeline:

    Query Intake -> Planner -> Web Browsing -> Extraction
                 -> Validation -> Aggregation + Memory -> Report Generation

Every agent (planner, browser, extractor, validator, aggregator, report
writer) reads from and writes to `ResearchJobState`. Nothing downstream
(backend Pydantic models, evidence store, frontend types) should redefine
these shapes -- they should import or mirror this file exactly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStage(str, Enum):
    """The 7 pipeline stages from the technical architecture diagram."""
    INTAKE = "intake"
    PLANNING = "planning"
    BROWSING = "browsing"
    EXTRACTION = "extraction"
    VALIDATION = "validation"
    AGGREGATION = "aggregation"
    REPORT_GENERATION = "report_generation"
    REVIEW = "review"
    DONE = "done"
    FAILED = "failed"


class JobStatus(str, Enum):
    """Coarse-grained status, independent of which stage is running."""
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceType(str, Enum):
    WEB_PAGE = "web_page"
    NEWS = "news"
    COMPANY_SITE = "company_site"
    INDUSTRY_REPORT = "industry_report"
    FILING = "filing"
    ANALYST_COMMENTARY = "analyst_commentary"
    INTERNAL_KNOWLEDGE = "internal_knowledge"
    OTHER = "other"


class OutputFormat(str, Enum):
    MARKET_ENTRY_SCAN = "market_entry_scan"
    COMPETITOR_LANDSCAPE = "competitor_landscape"
    TREND_BRIEF = "trend_brief"
    PROPOSAL_SUPPORT = "proposal_support"


class ValidationFlag(str, Enum):
    """Reasons a piece of evidence may be downgraded or excluded."""
    LOW_CREDIBILITY_SOURCE = "low_credibility_source"
    STALE = "stale"
    DUPLICATE = "duplicate"
    CONTRADICTED = "contradicted"
    UNSUPPORTED_BY_EXCERPT = "unsupported_by_excerpt"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


# ---------------------------------------------------------------------------
# 1. Query Intake
# ---------------------------------------------------------------------------

class ResearchRequest(BaseModel):
    """What the consultant submits at intake (Stage 1)."""
    request_id: str = Field(default_factory=lambda: _new_id("req"))
    query: str = Field(..., description="The raw research question from the consultant.")
    sector: Optional[str] = None
    geography: Optional[str] = None
    competitors: list[str] = Field(default_factory=list)
    timeframe: Optional[str] = Field(
        None, description="e.g. 'last 12 months', 'Q1 2026'."
    )
    output_format: OutputFormat = OutputFormat.MARKET_ENTRY_SCAN
    report_depth: str = Field("standard", description="'quick' | 'standard' | 'deep'")
    source_preference: list[SourceType] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=_utcnow)

    def is_sufficiently_scoped(self) -> bool:
        """Cheap intake gate: reject clearly under-specified queries early."""
        return bool(self.query and len(self.query.strip()) >= 12)


# ---------------------------------------------------------------------------
# 2. Planner Agent output
# ---------------------------------------------------------------------------

class ResearchTask(BaseModel):
    """One sub-question / search task produced by the planner."""
    task_id: str = Field(default_factory=lambda: _new_id("task"))
    sub_question: str
    source_categories: list[SourceType] = Field(default_factory=list)
    expected_evidence_types: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    request_id: str
    plan_id: str = Field(default_factory=lambda: _new_id("plan"))
    tasks: list[ResearchTask] = Field(default_factory=list)
    output_sections: list[str] = Field(
        default_factory=lambda: [
            "executive_summary",
            "market_signals",
            "competitor_observations",
            "implications",
            "recommendations",
            "evidence_appendix",
        ]
    )
    approved_by_user: bool = False
    created_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# 3. Web Browsing output
# ---------------------------------------------------------------------------

class SourceRecord(BaseModel):
    source_id: str = Field(default_factory=lambda: _new_id("src"))
    task_id: Optional[str] = None
    url: str
    title: Optional[str] = None
    source_type: SourceType = SourceType.OTHER
    publisher: Optional[str] = None
    published_at: Optional[datetime] = None
    retrieved_at: datetime = Field(default_factory=_utcnow)
    raw_snippet: Optional[str] = Field(
        None, description="Short excerpt captured during browsing, pre-extraction."
    )
    full_content: Optional[str] = Field(
        None,
        description=(
            "Full cleaned page text (e.g. from Tavily Extract). This, not "
            "raw_snippet, is what the extraction agent should read claims from."
        ),
    )
    fetch_failed: bool = False
    fetch_error: Optional[str] = None


# ---------------------------------------------------------------------------
# 4. Extraction output
# ---------------------------------------------------------------------------

class EvidenceRecord(BaseModel):
    """
    A single structured claim extracted from a source.

    `excerpt` MUST be a verbatim (or near-verbatim) snippet from the source
    that actually supports `claim`. Extraction agents should refuse to
    produce an EvidenceRecord if they cannot ground the claim in an excerpt.
    """
    evidence_id: str = Field(default_factory=lambda: _new_id("ev"))
    task_id: Optional[str] = None
    source_id: str
    claim: str
    excerpt: str
    entity: Optional[str] = None
    topic: Optional[str] = None
    relevance_score: float = Field(0.5, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=_utcnow)

    # Populated by the validation stage:
    confidence_score: float = Field(0.5, ge=0.0, le=1.0)
    validation_flags: list[ValidationFlag] = Field(default_factory=list)
    is_supported: bool = Field(
        True, description="False if validation determined this claim is unreliable."
    )
    duplicate_of: Optional[str] = Field(
        None, description="evidence_id of the record this duplicates, if any."
    )


# ---------------------------------------------------------------------------
# 6. Aggregation + Memory
# ---------------------------------------------------------------------------

class MemoryHit(BaseModel):
    """A reusable prior finding retrieved from the vector memory (Chroma)."""
    memory_id: str
    content: str
    similarity: float = Field(..., ge=0.0, le=1.0)
    source_job_id: Optional[str] = None
    created_at: Optional[datetime] = None


class ThemeCluster(BaseModel):
    """A group of related, validated evidence records aggregated together."""
    theme_id: str = Field(default_factory=lambda: _new_id("theme"))
    label: str
    evidence_ids: list[str] = Field(default_factory=list)
    memory_hits: list[MemoryHit] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 7. Report Generation output
# ---------------------------------------------------------------------------

class ReportSection(BaseModel):
    heading: str
    content: str
    cited_evidence_ids: list[str] = Field(default_factory=list)


class Report(BaseModel):
    report_id: str = Field(default_factory=lambda: _new_id("rpt"))
    request_id: str
    sections: list[ReportSection] = Field(default_factory=list)
    version: int = 1
    generated_at: datetime = Field(default_factory=_utcnow)
    requires_human_review: bool = True


# ---------------------------------------------------------------------------
# Master pipeline state
# ---------------------------------------------------------------------------

class ResearchJobState(BaseModel):
    """
    The single object passed between every LangGraph node.

    LangGraph nodes should take this object in, mutate/extend the relevant
    fields for their stage, and return it -- never construct a competing
    shape. Treat this class as the contract for the entire pipeline.
    """
    job_id: str = Field(default_factory=lambda: _new_id("job"))
    status: JobStatus = JobStatus.PENDING
    stage: JobStage = JobStage.INTAKE

    request: ResearchRequest
    plan: Optional[ResearchPlan] = None
    sources: list[SourceRecord] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    themes: list[ThemeCluster] = Field(default_factory=list)
    report: Optional[Report] = None

    error_message: Optional[str] = None
    stage_history: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_utcnow)

    def advance(self, next_stage: JobStage) -> None:
        """Record a stage transition. Call this at the end of every node."""
        self.stage_history.append(f"{self.stage.value} -> {next_stage.value}")
        self.stage = next_stage
        self.updated_at = _utcnow()

    def mark_failed(self, error_message: str) -> None:
        self.status = JobStatus.FAILED
        self.stage = JobStage.FAILED
        self.error_message = error_message
        self.updated_at = _utcnow()

    def validated_evidence(self) -> list[EvidenceRecord]:
        """Evidence that survived validation and is safe for report generation."""
        return [e for e in self.evidence if e.is_supported and not e.duplicate_of]