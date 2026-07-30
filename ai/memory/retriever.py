"""
ai/memory/retriever.py

Stage 6: Aggregation + Memory. Two responsibilities, matching the
combined box in the architecture diagram:

1. Cluster validated evidence into ThemeClusters, grouped by the
   entity/topic tags extraction already assigned -- no extra LLM call
   needed, this reuses work already done upstream.
2. For each theme, retrieve related prior findings from Chroma memory
   and attach them as MemoryHits, so the report can draw on reusable
   firm knowledge alongside fresh evidence from this job.
"""

from __future__ import annotations

from collections import defaultdict

from ai.state import EvidenceRecord, MemoryHit, ThemeCluster
from ai.memory.chroma_store import ChromaStore

MIN_SIMILARITY_FOR_MEMORY_HIT = 0.6


def build_theme_clusters(evidence_list: list[EvidenceRecord]) -> list[ThemeCluster]:
    """
    Groups validated evidence by (entity, topic). Evidence missing both
    tags is grouped into a single "general" theme rather than dropped --
    it should still reach the report, just without a specific label.
    """
    groups: dict[tuple, list[str]] = defaultdict(list)

    for e in evidence_list:
        entity = (e.entity or "").strip()
        topic = (e.topic or "").strip()
        key = (entity, topic) if (entity or topic) else ("General", "General")
        groups[key].append(e.evidence_id)

    clusters = []
    for (entity, topic), evidence_ids in groups.items():
        if entity == "General" and topic == "General":
            label = "General"
        elif entity and topic:
            label = f"{entity} — {topic}"
        else:
            label = entity or topic or "General"
        clusters.append(ThemeCluster(label=label, evidence_ids=evidence_ids))

    return clusters


class MemoryRetriever:
    """
    Wraps a ChromaStore. Instantiate once and reuse across jobs.
    """

    def __init__(self, store: ChromaStore | None = None):
        self.store = store or ChromaStore()

    def attach_memory_hits(self, clusters: list[ThemeCluster], top_k: int = 3) -> list[ThemeCluster]:
        """
        For each theme, queries memory using the theme label as the search
        text and attaches any sufficiently similar prior findings. Themes
        with no relevant memory are left with an empty memory_hits list --
        that's expected for a brand new topic with no research history yet.
        """
        for cluster in clusters:
            raw = self.store.query(cluster.label, top_k=top_k)
            ids = raw.get("ids", [[]])[0]
            documents = raw.get("documents", [[]])[0]
            distances = raw.get("distances", [[]])[0]
            metadatas = raw.get("metadatas", [[]])[0]

            hits = []
            for mem_id, doc, distance, meta in zip(ids, documents, distances, metadatas):
                # Chroma returns distance (lower = more similar) by default
                # for cosine space; convert to a 0-1 similarity for our schema.
                similarity = max(0.0, 1.0 - distance)
                if similarity < MIN_SIMILARITY_FOR_MEMORY_HIT:
                    continue
                hits.append(
                    MemoryHit(
                        memory_id=mem_id,
                        content=doc,
                        similarity=round(similarity, 3),
                        source_job_id=(meta or {}).get("job_id"),
                    )
                )
            cluster.memory_hits = hits

        return clusters

    def store_validated_evidence(self, job_id: str, evidence_list: list[EvidenceRecord]) -> None:
        """
        Persists this job's validated, non-duplicate evidence into memory
        so future jobs can retrieve it. Call this once, at the end of a
        completed job -- not mid-pipeline.
        """
        supported = [e for e in evidence_list if e.is_supported]
        if not supported:
            return

        self.store.add_evidence(
            evidence_ids=[e.evidence_id for e in supported],
            claims=[e.claim for e in supported],
            metadatas=[
                {
                    "job_id": job_id,
                    "entity": e.entity or "",
                    "topic": e.topic or "",
                    "source_id": e.source_id,
                }
                for e in supported
            ],
        )


def aggregate(job_id: str, evidence_list: list[EvidenceRecord], retriever: MemoryRetriever) -> list[ThemeCluster]:
    """
    Full Stage 6 entry point: cluster validated evidence into themes,
    enrich each theme with relevant prior memory, and persist this job's
    evidence back into memory for future jobs.
    """
    validated = [e for e in evidence_list if e.is_supported]
    clusters = build_theme_clusters(validated)
    clusters = retriever.attach_memory_hits(clusters)
    retriever.store_validated_evidence(job_id, validated)
    return clusters


if __name__ == "__main__":
    # Manual smoke test. Requires GEMINI_API_KEY in the environment.
    # Run from the project root: python -m ai.memory.retriever
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
            claim="VinFast announced a joint venture with ChargePoint",
            excerpt="VinFast and ChargePoint announced a joint venture",
            entity="VinFast",
            topic="competitor move",
            is_supported=True,
        ),
    ]

    retriever = MemoryRetriever()
    clusters = aggregate("job_demo_001", evidence, retriever)
    for c in clusters:
        print(f"- theme: {c.label}")
        print(f"  evidence_ids: {c.evidence_ids}")
        print(f"  memory_hits: {[h.content for h in c.memory_hits]}")