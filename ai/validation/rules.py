"""
ai/validation/rules.py

Deterministic, rule-based validation checks: credibility scoring, recency,
and duplicate detection. These run without any LLM call -- cheap, fast,
and fully reproducible. Contradiction detection (which needs semantic
understanding) lives separately in agent.py since it requires an LLM.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from ai.state import EvidenceRecord, ResearchRequest, SourceRecord, SourceType, ValidationFlag
from backend.core.config import settings

# Base credibility score by source type. Used as a starting point for
# confidence_score before other signals (recency, duplication) adjust it.
_CREDIBILITY_BY_SOURCE_TYPE: dict[SourceType, float] = {
    SourceType.FILING: 0.95,
    SourceType.INDUSTRY_REPORT: 0.9,
    SourceType.ANALYST_COMMENTARY: 0.8,
    SourceType.NEWS: 0.75,
    SourceType.COMPANY_SITE: 0.65,
    SourceType.INTERNAL_KNOWLEDGE: 0.6,
    SourceType.WEB_PAGE: 0.5,
    SourceType.OTHER: 0.4,
}

DEFAULT_STALE_MONTHS = settings.VALIDATION_STALE_MONTHS_DEFAULT

# Roughly maps common timeframe phrasings to a max age in months.
# Falls back to DEFAULT_STALE_MONTHS if the phrasing isn't recognized.
_TIMEFRAME_MONTHS_PATTERN = re.compile(r"(\d+)\s*(month|year)", re.IGNORECASE)


def _resolve_max_age_months(timeframe: str | None) -> int:
    if not timeframe:
        return DEFAULT_STALE_MONTHS
    match = _TIMEFRAME_MONTHS_PATTERN.search(timeframe)
    if not match:
        return DEFAULT_STALE_MONTHS
    quantity, unit = int(match.group(1)), match.group(2).lower()
    return quantity * 12 if unit == "year" else quantity


def score_credibility(source: SourceRecord | None) -> float:
    """Base score from source type alone. 0.5 if source is missing/unknown."""
    if source is None:
        return 0.5
    return _CREDIBILITY_BY_SOURCE_TYPE.get(source.source_type, 0.5)


def check_recency(
    evidence: EvidenceRecord,
    source: SourceRecord | None,
    request: ResearchRequest,
) -> bool:
    """
    Returns True if evidence is stale (should be flagged), False if fresh
    or if the source has no date at all (undated evidence is not penalized
    here -- absence of a date is a separate, weaker signal than a known
    old date).
    """
    if source is None or source.published_at is None:
        return False

    max_age_months = _resolve_max_age_months(request.timeframe)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_months * 30)

    published = source.published_at
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)

    return published < cutoff


def _text_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def find_duplicates(
    evidence_list: list[EvidenceRecord],
    similarity_threshold: float = settings.VALIDATION_DUPLICATE_SIMILARITY_THRESHOLD,
) -> dict[str, str]:
    """
    Compares every claim against every other claim (only within reasonable
    scale -- fine for a single research job's evidence set, not meant for
    large batch dedup). Returns a mapping of evidence_id -> evidence_id it
    duplicates (the earlier one in the list is treated as canonical).
    """
    duplicate_of: dict[str, str] = {}

    for i, current in enumerate(evidence_list):
        if current.evidence_id in duplicate_of:
            continue  # already marked as a duplicate of something earlier
        for earlier in evidence_list[:i]:
            if earlier.evidence_id in duplicate_of:
                continue  # don't chain duplicates of duplicates
            if _text_similarity(current.claim, earlier.claim) >= similarity_threshold:
                duplicate_of[current.evidence_id] = earlier.evidence_id
                break

    return duplicate_of


def apply_rule_based_checks(
    evidence_list: list[EvidenceRecord],
    sources_by_id: dict[str, SourceRecord],
    request: ResearchRequest,
) -> None:
    """
    Mutates evidence_list in place: sets confidence_score, validation_flags
    (credibility/recency/duplicate related), and duplicate_of. Contradiction
    flags are applied separately by the LLM-based check in agent.py.
    """
    duplicate_map = find_duplicates(evidence_list)

    for evidence in evidence_list:
        source = sources_by_id.get(evidence.source_id)
        credibility = score_credibility(source)
        is_stale = check_recency(evidence, source, request)
        is_duplicate = evidence.evidence_id in duplicate_map

        flags: list[ValidationFlag] = []
        if credibility < 0.6:
            flags.append(ValidationFlag.LOW_CREDIBILITY_SOURCE)
        if is_stale:
            flags.append(ValidationFlag.STALE)
        if is_duplicate:
            flags.append(ValidationFlag.DUPLICATE)
            evidence.duplicate_of = duplicate_map[evidence.evidence_id]

        # Confidence blends source credibility with relevance; staleness
        # and duplication pull it down further.
        confidence = credibility * 0.7 + evidence.relevance_score * 0.3
        if is_stale:
            confidence *= 0.7
        if is_duplicate:
            confidence *= 0.5

        evidence.confidence_score = round(min(max(confidence, 0.0), 1.0), 3)
        evidence.validation_flags = flags
        evidence.is_supported = confidence >= 0.4 and not is_duplicate