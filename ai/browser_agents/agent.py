"""
ai/browser_agents/agent.py

The Web Browsing Agent: for each ResearchTask in a plan, runs a Tavily
search to find candidate URLs, then runs Tavily Extract to pull full,
cleaned page content for each URL. Produces SourceRecord objects that
feed the Extraction stage.
"""

from __future__ import annotations

from tavily import TavilyClient

from ai.state import ResearchPlan, SourceRecord
from ai.browser_agents.source_utils import build_source_record
from backend.core.config import settings

DEFAULT_RESULTS_PER_TASK = settings.BROWSER_RESULTS_PER_TASK


class BrowserAgent:
    """
    Wraps a Tavily client. Instantiate once and reuse -- do not construct a
    new client per task.
    """

    def __init__(self, api_key: str | None = None, results_per_task: int = DEFAULT_RESULTS_PER_TASK):
        self.client = TavilyClient(api_key=api_key or settings.TAVILY_API_KEY)
        self.results_per_task = results_per_task

    def _search_task(self, sub_question: str) -> list[dict]:
        """Runs a Tavily search for one sub-question. Returns raw result dicts."""
        response = self.client.search(
            query=sub_question,
            max_results=self.results_per_task,
            search_depth="advanced",
        )
        return response.get("results", [])

    def _extract_urls(self, urls: list[str]) -> dict[str, dict]:
        """
        Runs Tavily Extract on a batch of URLs. Returns a dict keyed by URL
        so results can be matched back to their originating search result.
        Failures for individual URLs are captured, not raised -- one bad
        URL should not fail the whole browsing stage.
        """
        if not urls:
            return {}
        response = self.client.extract(urls=urls)
        by_url: dict[str, dict] = {}
        for item in response.get("results", []):
            by_url[item["url"]] = item
        for failure in response.get("failed_results", []):
            by_url[failure["url"]] = {"error": failure.get("error", "extract failed")}
        return by_url

    def run(self, plan: ResearchPlan) -> list[SourceRecord]:
        """
        Executes browsing for every task in the plan. Returns a flat list of
        SourceRecords. Tasks that turn up zero search results are skipped,
        not failed -- validation/aggregation later will flag any sub-question
        left with insufficient coverage.
        """
        all_sources: list[SourceRecord] = []

        for task in plan.tasks:
            search_results = self._search_task(task.sub_question)
            urls = [r["url"] for r in search_results if r.get("url")]
            extracted_by_url = self._extract_urls(urls)

            for result in search_results:
                url = result.get("url")
                if not url:
                    continue

                extracted = extracted_by_url.get(url, {})
                fetch_failed = "error" in extracted
                full_content = extracted.get("raw_content") if not fetch_failed else None

                source = build_source_record(
                    task_id=task.task_id,
                    url=url,
                    title=result.get("title"),
                    raw_snippet=result.get("content"),
                    full_content=full_content,
                    published_at_raw=result.get("published_date"),
                    fetch_failed=fetch_failed,
                    fetch_error=extracted.get("error") if fetch_failed else None,
                )
                all_sources.append(source)

        return all_sources


if __name__ == "__main__":
    # Manual smoke test. Requires TAVILY_API_KEY in the environment.
    # Run from the project root: python -m ai.browser_agents.agent
    from ai.state import ResearchPlan, ResearchTask, SourceType

    sample_plan = ResearchPlan(
        request_id="req_demo",
        tasks=[
            ResearchTask(
                sub_question="Top EV charging network operators in Vietnam 2025 2026",
                source_categories=[SourceType.NEWS, SourceType.COMPANY_SITE],
            )
        ],
    )
    agent = BrowserAgent(results_per_task=3)
    sources = agent.run(sample_plan)
    for s in sources:
        print(f"- {s.url} | failed={s.fetch_failed} | content_len={len(s.full_content or '')}")