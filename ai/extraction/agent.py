"""
ai/extraction/agent.py

The Extraction Agent: for each SourceRecord collected during browsing,
calls Gemini to pull out structured EvidenceRecords (claim + excerpt pairs)
relevant to the research task that source was gathered for.

Runs per-source (one LLM call per page) rather than batching multiple
sources into one call -- this keeps each extraction tightly scoped to a
single page's actual content, lowering the risk of the model blending
claims across sources.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from backend.core.config import settings

from ai.state import EvidenceRecord, ResearchPlan, SourceRecord
from ai.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, build_extraction_user_prompt

DEFAULT_MODEL = settings.GEMINI_EXTRACTION_MODEL


class ExtractedClaim(BaseModel):
    claim: str
    excerpt: str
    entity: str | None = None
    topic: str | None = None
    relevance_score: float = Field(0.5, ge=0.0, le=1.0)


class ExtractionOutput(BaseModel):
    claims: list[ExtractedClaim]


class ExtractionAgent:
    """
    Wraps a Gemini client. Instantiate once and reuse across sources --
    do not construct a new client per call.
    """

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)

    def extract_from_source(self, sub_question: str, source: SourceRecord) -> list[EvidenceRecord]:
        page_text = source.full_content or source.raw_snippet
        if not page_text or source.fetch_failed:
            return []

        user_prompt = build_extraction_user_prompt(
            sub_question=sub_question,
            source_url=source.url,
            page_text=page_text,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ExtractionOutput,
                temperature=0.1,
            ),
        )

        parsed: ExtractionOutput = response.parsed
        if parsed is None:
            return []

        return [
            EvidenceRecord(
                task_id=source.task_id,
                source_id=source.source_id,
                claim=c.claim,
                excerpt=c.excerpt,
                entity=c.entity,
                topic=c.topic,
                relevance_score=c.relevance_score,
            )
            for c in parsed.claims
        ]

    def run(self, plan: ResearchPlan, sources: list[SourceRecord]) -> list[EvidenceRecord]:
        task_by_id = {t.task_id: t for t in plan.tasks}
        all_evidence: list[EvidenceRecord] = []

        for source in sources:
            task = task_by_id.get(source.task_id)
            if task is None:
                continue
            evidence = self.extract_from_source(task.sub_question, source)
            all_evidence.extend(evidence)

        return all_evidence


if __name__ == "__main__":
    from ai.state import ResearchTask, SourceType

    sample_task = ResearchTask(
        sub_question="What EV charging operators are active in Vietnam?",
        source_categories=[SourceType.NEWS],
    )
    sample_plan = ResearchPlan(request_id="req_demo", tasks=[sample_task])

    sample_source = SourceRecord(
        task_id=sample_task.task_id,
        url="https://example.com/ev-article",
        title="Vietnam EV Charging Market",
        full_content=(
            "VinFast and ChargePoint announced a joint venture in March 2026 "
            "to build 5,000 new EV charging stations across Vietnam by 2028. "
            "The Vietnamese government also introduced a 10% tax credit for "
            "EV charging infrastructure investment starting January 2026."
        ),
    )

    agent = ExtractionAgent()
    evidence = agent.run(sample_plan, [sample_source])
    for e in evidence:
        print(f"- claim: {e.claim}")
        print(f"  excerpt: {e.excerpt}")
        print(f"  entity={e.entity} topic={e.topic} relevance={e.relevance_score}")