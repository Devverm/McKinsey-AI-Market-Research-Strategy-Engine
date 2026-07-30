"""
ai/report_generation/agent.py

The Report Generation Agent: takes theme clusters (with their validated
evidence and any relevant memory hits) and produces the final client-ready
Report in a single Gemini call, using response_schema enforcement so the
output is always well-formed sections rather than free text to parse.
"""

from __future__ import annotations

from google import genai
from google.genai import types
from pydantic import BaseModel

from ai.state import EvidenceRecord, Report, ReportSection, ResearchRequest, ThemeCluster
from ai.report_generation.prompts import REPORT_SYSTEM_PROMPT, build_report_user_prompt
from backend.core.config import settings

DEFAULT_MODEL = settings.GEMINI_MODEL


class ReportSectionOutput(BaseModel):
    heading: str
    content: str
    cited_evidence_ids: list[str]


class ReportOutput(BaseModel):
    sections: list[ReportSectionOutput]


class ReportAgent:
    """
    Wraps a Gemini client. Instantiate once and reuse across jobs.
    """

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)

    def _build_themes_payload(
        self, themes: list[ThemeCluster], evidence_by_id: dict[str, EvidenceRecord]
    ) -> list[dict]:
        payload = []
        for theme in themes:
            evidence_dicts = []
            for eid in theme.evidence_ids:
                ev = evidence_by_id.get(eid)
                if ev is None:
                    continue  # evidence_id in theme but not found -- skip rather than crash
                evidence_dicts.append(
                    {
                        "evidence_id": ev.evidence_id,
                        "claim": ev.claim,
                        "entity": ev.entity,
                        "topic": ev.topic,
                    }
                )
            payload.append(
                {
                    "label": theme.label,
                    "evidence": evidence_dicts,
                    "memory_hits": [
                        {"content": h.content, "similarity": h.similarity}
                        for h in theme.memory_hits
                    ],
                }
            )
        return payload

    def generate_report(
        self,
        request: ResearchRequest,
        themes: list[ThemeCluster],
        evidence_list: list[EvidenceRecord],
    ) -> Report:
        """
        Produces the final Report. Any cited_evidence_id the model returns
        that doesn't correspond to a real evidence_id we actually gave it
        is dropped -- a citation to evidence that doesn't exist is worse
        than no citation, and this is a cheap, deterministic safety check
        (not a content-grounding check, just an ID-existence check).
        """
        evidence_by_id = {e.evidence_id: e for e in evidence_list}
        known_ids = set(evidence_by_id.keys())

        themes_payload = self._build_themes_payload(themes, evidence_by_id)
        user_prompt = build_report_user_prompt(request.query, themes_payload)

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=REPORT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=ReportOutput,
                temperature=0.3,
            ),
        )

        parsed: ReportOutput = response.parsed
        if parsed is None or not parsed.sections:
            raise ValueError("Report agent returned no sections. Refusing to produce an empty report.")

        sections = [
            ReportSection(
                heading=s.heading,
                content=s.content,
                cited_evidence_ids=[eid for eid in s.cited_evidence_ids if eid in known_ids],
            )
            for s in parsed.sections
        ]

        return Report(request_id=request.request_id, sections=sections)


if __name__ == "__main__":
    # Manual smoke test. Requires GEMINI_API_KEY in the environment.
    # Run from the project root: python -m ai.report_generation.agent
    from ai.state import MemoryHit

    request = ResearchRequest(
        query="Assess market entry opportunity for EV charging in Vietnam",
        sector="EV infrastructure",
        geography="Vietnam",
    )

    evidence = [
        EvidenceRecord(
            source_id="s1",
            claim="Vietnam's EV charging market grew 40% year over year in 2025",
            excerpt="grew 40% year over year",
            entity="Vietnam EV charging market",
            topic="market size",
            is_supported=True,
        ),
        EvidenceRecord(
            source_id="s2",
            claim="VinFast and ChargePoint announced a joint venture to build 5,000 stations by 2028",
            excerpt="joint venture to build 5,000 new EV charging stations",
            entity="VinFast",
            topic="competitor move",
            is_supported=True,
        ),
    ]

    themes = [
        ThemeCluster(
            label="Vietnam EV charging market — market size",
            evidence_ids=[evidence[0].evidence_id],
            memory_hits=[MemoryHit(memory_id="m1", content="Thailand EV market grew 25% in 2024", similarity=0.7)],
        ),
        ThemeCluster(
            label="VinFast — competitor move",
            evidence_ids=[evidence[1].evidence_id],
        ),
    ]

    agent = ReportAgent()
    report = agent.generate_report(request, themes, evidence)
    print(report.model_dump_json(indent=2))