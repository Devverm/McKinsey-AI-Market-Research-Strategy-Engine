"""
ai/graph.py

Wires all 6 pipeline stages into a single LangGraph state machine, operating
on the canonical ResearchJobState from ai/state.py.

    intake -> planning -> browsing -> extraction -> validation
           -> aggregation -> report_generation -> (review | failed)

Each node does the work for its stage, then calls state.advance(next_stage).
If a node raises, the job is marked failed and the graph short-circuits to
END instead of continuing to run downstream stages on broken state.

Agents are injected via build_graph(...) rather than constructed at import
time -- this keeps the module importable/testable without API keys present,
and makes it easy to swap in fakes for testing.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from ai.state import JobStage, JobStatus, ResearchJobState

from ai.planner_agent.agent import PlannerAgent
from ai.browser_agents.agent import BrowserAgent
from ai.extraction.agent import ExtractionAgent
from ai.validation.agent import ValidationAgent
from ai.memory.retriever import MemoryRetriever, aggregate
from ai.report_generation.agent import ReportAgent


def _route_after(state: ResearchJobState) -> str:
    """Shared router: if a node marked the job failed, go straight to END."""
    return "failed" if state.status == JobStatus.FAILED else "continue"


def build_graph(
    planner: PlannerAgent | None = None,
    browser: BrowserAgent | None = None,
    extractor: ExtractionAgent | None = None,
    validator: ValidationAgent | None = None,
    memory_retriever: MemoryRetriever | None = None,
    reporter: ReportAgent | None = None,
):
    """
    Builds and compiles the LangGraph pipeline. Pass explicit agent
    instances for testing with fakes; omit them to use real agents
    (which will read API keys from the environment at construction time).
    """
    planner = planner or PlannerAgent()
    browser = browser or BrowserAgent()
    extractor = extractor or ExtractionAgent()
    validator = validator or ValidationAgent()
    memory_retriever = memory_retriever or MemoryRetriever()
    reporter = reporter or ReportAgent()

    # ---------------------------------------------------------------
    # Node implementations
    # ---------------------------------------------------------------

    def intake_node(state: ResearchJobState) -> ResearchJobState:
        if not state.request.is_sufficiently_scoped():
            state.mark_failed("Research request is insufficiently scoped to plan against.")
            return state
        state.status = JobStatus.RUNNING
        state.advance(JobStage.PLANNING)
        return state

    def planner_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.plan = planner.create_plan(state.request)
        except Exception as e:
            state.mark_failed(f"Planning failed: {e}")
            return state
        state.advance(JobStage.BROWSING)
        return state

    def browser_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.sources = browser.run(state.plan)
        except Exception as e:
            state.mark_failed(f"Browsing failed: {e}")
            return state
        state.advance(JobStage.EXTRACTION)
        return state

    def extraction_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.evidence = extractor.run(state.plan, state.sources)
        except Exception as e:
            state.mark_failed(f"Extraction failed: {e}")
            return state
        state.advance(JobStage.VALIDATION)
        return state

    def validation_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.evidence = validator.run(state.evidence, state.sources, state.request)
        except Exception as e:
            state.mark_failed(f"Validation failed: {e}")
            return state
        state.advance(JobStage.AGGREGATION)
        return state

    def aggregation_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.themes = aggregate(state.job_id, state.evidence, memory_retriever)
        except Exception as e:
            state.mark_failed(f"Aggregation failed: {e}")
            return state
        state.advance(JobStage.REPORT_GENERATION)
        return state

    def report_node(state: ResearchJobState) -> ResearchJobState:
        try:
            state.report = reporter.generate_report(state.request, state.themes, state.evidence)
        except Exception as e:
            state.mark_failed(f"Report generation failed: {e}")
            return state
        state.status = JobStatus.NEEDS_REVIEW
        state.advance(JobStage.REVIEW)
        return state

    # ---------------------------------------------------------------
    # Graph wiring
    # ---------------------------------------------------------------

    builder = StateGraph(ResearchJobState)

    builder.add_node("intake", intake_node)
    builder.add_node("planner", planner_node)
    builder.add_node("browser", browser_node)
    builder.add_node("extractor", extraction_node)
    builder.add_node("validator", validation_node)
    builder.add_node("aggregator", aggregation_node)
    builder.add_node("reporter", report_node)

    builder.set_entry_point("intake")

    for node_name, next_node in [
        ("intake", "planner"),
        ("planner", "browser"),
        ("browser", "extractor"),
        ("extractor", "validator"),
        ("validator", "aggregator"),
        ("aggregator", "reporter"),
    ]:
        builder.add_conditional_edges(
            node_name,
            _route_after,
            {"continue": next_node, "failed": END},
        )

    builder.add_edge("reporter", END)

    return builder.compile()


if __name__ == "__main__":
    # Manual smoke test. Requires GEMINI_API_KEY and TAVILY_API_KEY in the
    # environment. Run from the project root: python -m ai.graph
    from ai.state import ResearchRequest

    graph = build_graph()
    request = ResearchRequest(
        query="Assess market entry opportunity for EV charging in Vietnam",
        sector="EV infrastructure",
        geography="Vietnam",
        timeframe="last 12 months",
    )
    initial_state = ResearchJobState(request=request)

    result = graph.invoke(initial_state)
    final_state = ResearchJobState(**result) if isinstance(result, dict) else result

    print("Final status:", final_state.status)
    print("Final stage:", final_state.stage)
    print("Stage history:", final_state.stage_history)
    if final_state.status == JobStatus.FAILED:
        print("Error:", final_state.error_message)
    else:
        print("Report sections:", [s.heading for s in final_state.report.sections])