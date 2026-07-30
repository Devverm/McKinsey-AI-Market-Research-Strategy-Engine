"""
ai/planner_agent/agent.py

The Planner Agent: takes a ResearchRequest and produces a ResearchPlan
by calling Gemini with a strict JSON response schema (no manual parsing
of free-text JSON).
"""

from __future__ import annotations

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from ai.state import ResearchPlan, ResearchRequest, ResearchTask, SourceType
from ai.planner_agent.prompts import PLANNER_SYSTEM_PROMPT, build_planner_user_prompt
from backend.core.config import settings

DEFAULT_MODEL = settings.GEMINI_MODEL


# ---------------------------------------------------------------------------
# Schema the LLM must fill in. Kept separate from ai.state.ResearchTask
# because the LLM should NOT be responsible for generating task_id --
# that's assigned locally after the response comes back.
# ---------------------------------------------------------------------------

class PlannerTaskOutput(BaseModel):
    sub_question: str
    source_categories: list[SourceType] = Field(default_factory=list)
    expected_evidence_types: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    tasks: list[PlannerTaskOutput]


class PlannerAgent:
    """
    Wraps a Gemini client. Instantiate once (e.g. at app startup) and reuse
    across requests -- do not construct a new client per call.
    """

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)

    def create_plan(self, request: ResearchRequest) -> ResearchPlan:
        """
        Calls Gemini to decompose `request` into a ResearchPlan.
        Raises on API failure or empty task list -- callers (the LangGraph
        node) are responsible for catching this and routing the job to a
        failed state rather than silently producing an empty plan.
        """
        user_prompt = build_planner_user_prompt(
            query=request.query,
            sector=request.sector,
            geography=request.geography,
            competitors=request.competitors,
            timeframe=request.timeframe,
            output_format=request.output_format.value,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=PlannerOutput,
                temperature=0.2,
            ),
        )

        parsed: PlannerOutput = response.parsed
        if parsed is None or not parsed.tasks:
            raise ValueError(
                "Planner returned no tasks. Refusing to produce an empty ResearchPlan."
            )

        tasks = [
            ResearchTask(
                sub_question=t.sub_question,
                source_categories=t.source_categories,
                expected_evidence_types=t.expected_evidence_types,
                validation_rules=t.validation_rules,
            )
            for t in parsed.tasks
        ]

        return ResearchPlan(request_id=request.request_id, tasks=tasks)


if __name__ == "__main__":
    # Manual smoke test. Requires GEMINI_API_KEY to be set in the environment.
    # Run from the project root: python -m ai.planner_agent.agent
    sample_request = ResearchRequest(
        query="Assess market entry opportunity for EV charging in Southeast Asia",
        sector="EV infrastructure",
        geography="Southeast Asia",
        competitors=["ChargePoint", "Shell Recharge"],
        timeframe="last 12 months",
    )
    agent = PlannerAgent()
    plan = agent.create_plan(sample_request)
    print(plan.model_dump_json(indent=2))