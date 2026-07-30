"""
ai/browser_agents/source_utils.py

Small helpers used by the browser agent: mapping raw Tavily responses into
our canonical SourceRecord shape, and basic source-type classification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from ai.state import SourceRecord, SourceType

# Very lightweight heuristics for classifying a URL into a SourceType.
# Not meant to be exhaustive -- the validation stage does the real
# credibility scoring. This just gives extraction/validation a starting hint.
_NEWS_HINTS = ("reuters.com", "bloomberg.com", "ft.com", "cnbc.com", "wsj.com", "/news/")
_FILING_HINTS = ("sec.gov", "10-k", "10-q", "annual-report", "prospectus")
_REPORT_HINTS = ("mckinsey.com", "gartner.com", "statista.com", "report", "whitepaper")


def classify_source_type(url: str) -> SourceType:
    lowered = url.lower()
    if any(hint in lowered for hint in _FILING_HINTS):
        return SourceType.FILING
    if any(hint in lowered for hint in _REPORT_HINTS):
        return SourceType.INDUSTRY_REPORT
    if any(hint in lowered for hint in _NEWS_HINTS):
        return SourceType.NEWS
    return SourceType.WEB_PAGE


def _parse_published_date(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def build_source_record(
    task_id: str,
    url: str,
    title: Optional[str] = None,
    raw_snippet: Optional[str] = None,
    full_content: Optional[str] = None,
    published_at_raw: Optional[str] = None,
    fetch_failed: bool = False,
    fetch_error: Optional[str] = None,
) -> SourceRecord:
    """Maps a Tavily search/extract result into our canonical SourceRecord."""
    return SourceRecord(
        task_id=task_id,
        url=url,
        title=title,
        source_type=classify_source_type(url),
        published_at=_parse_published_date(published_at_raw),
        raw_snippet=raw_snippet[:500] if raw_snippet else None,
        full_content=full_content,
        fetch_failed=fetch_failed,
        fetch_error=fetch_error,
    )