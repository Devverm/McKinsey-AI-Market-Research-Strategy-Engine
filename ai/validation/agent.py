"""
ai/validation/agent.py

The Validation Agent: orchestrates Stage 5. Applies the deterministic
rule-based checks (credibility, recency, duplicates) from rules.py, then
runs an LLM-based contradiction check across evidence that shares the same
entity/topic -- the one check that genuinely needs semantic understanding
rather than a fixed rule.
"""

from __future__ import annotations

from collections import defaultdict

from google import genai
from google.genai import types
from pydantic import BaseModel

from ai.state import EvidenceRecord, ResearchRequest, SourceRecord, ValidationFlag
from ai.validation.rules import apply_rule_based_checks
from backend.core.config import settings

DEFAULT_MODEL = settings.GEMINI_EXTRACTION_MODEL

CONTRADICTION_SYSTEM_PROMPT = """You are the Validation Agent's contradiction
checker inside a McKinsey-style AI market research system. You will be given
a list of claims that all relate to the same entity and topic, collected
from potentially different sources.

Identify any claims in the list that directly contradict one another (e.g.
different market size figures for the same year, conflicting statements
about whether an event happened). Do not flag claims that are simply about
different time periods, different sub-markets, or complementary rather than
conflicting.

Respond with the indices (0-based, matching the order given) of every claim
that is involved in a contradiction with at least one other claim in the
list. If there are no contradictions, return an empty list."""


class ContradictionCheckOutput(BaseModel):
    contradicting_indices: list[int]


class ValidationAgent:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)

    def _check_group_for_contradictions(self, group: list[EvidenceRecord]) -> set[str]:
        if len(group) < 2:
            return set()

        claims_list = "\n".join(f"{i}. {e.claim}" for i, e in enumerate(group))
        response = self.client.models.generate_content(
            model=self.model,
            contents=f"Claims:\n{claims_list}",
            config=types.GenerateContentConfig(
                system_instruction=CONTRADICTION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ContradictionCheckOutput,
                temperature=0.0,
            ),
        )

        parsed: ContradictionCheckOutput = response.parsed
        if parsed is None:
            return set()

        flagged_ids = set()
        for idx in parsed.contradicting_indices:
            if 0 <= idx < len(group):
                flagged_ids.add(group[idx].evidence_id)
        return flagged_ids

    def _group_by_entity_topic(self, evidence_list: list[EvidenceRecord]) -> dict[tuple, list[EvidenceRecord]]:
        groups: dict[tuple, list[EvidenceRecord]] = defaultdict(list)
        for e in evidence_list:
            key = ((e.entity or "").lower().strip(), (e.topic or "").lower().strip())
            if key == ("", ""):
                continue
            groups[key].append(e)
        return groups

    def run(
        self,
        evidence_list: list[EvidenceRecord],
        sources: list[SourceRecord],
        request: ResearchRequest,
    ) -> list[EvidenceRecord]:
        sources_by_id = {s.source_id: s for s in sources}
        apply_rule_based_checks(evidence_list, sources_by_id, request)

        groups = self._group_by_entity_topic(evidence_list)
        contradicted_ids: set[str] = set()
        for group in groups.values():
            contradicted_ids |= self._check_group_for_contradictions(group)

        for e in evidence_list:
            if e.evidence_id in contradicted_ids:
                e.validation_flags.append(ValidationFlag.CONTRADICTED)
                e.confidence_score = round(e.confidence_score * 0.5, 3)
                e.is_supported = False

        return evidence_list