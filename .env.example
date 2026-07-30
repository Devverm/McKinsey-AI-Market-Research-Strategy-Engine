"""
ai/memory/chroma_store.py

Thin wrapper around a local Chroma collection. Embeddings are generated
via Gemini's embedding API and passed to Chroma explicitly, rather than
relying on Chroma's default embedding function -- that default downloads
an ONNX model from an external host on first use, which can fail on
restricted networks. Generating embeddings ourselves also keeps the whole
stack on one LLM provider (Gemini), consistent with the rest of the agents.
"""

from __future__ import annotations

import chromadb
from google import genai
from google.genai import types

from backend.core.config import settings

DEFAULT_DB_PATH = settings.CHROMA_DB_PATH
DEFAULT_COLLECTION = "research_evidence_memory"
EMBEDDING_MODEL = settings.GEMINI_EMBEDDING_MODEL


class ChromaStore:
    """
    Instantiate once (e.g. at app startup) and reuse. Wraps a persistent
    local Chroma collection plus a Gemini client for embedding text.
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        collection_name: str = DEFAULT_COLLECTION,
        api_key: str | None = None,
    ):
        self.client = chromadb.PersistentClient(path=db_path)
        # embedding_function=None: we always supply embeddings explicitly,
        # so Chroma never tries to load/download one itself.
        self.collection = self.client.get_or_create_collection(
            name=collection_name, embedding_function=None
        )
        self.genai_client = genai.Client(api_key=api_key or settings.GEMINI_API_KEY)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.genai_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texts,
        )
        return [e.values for e in response.embeddings]

    def add_evidence(
        self,
        evidence_ids: list[str],
        claims: list[str],
        metadatas: list[dict],
    ) -> None:
        """
        Persists validated evidence into memory so future research jobs can
        retrieve it. Caller is responsible for only passing evidence that
        passed validation (is_supported=True) -- this store does not
        re-check that itself.
        """
        if not evidence_ids:
            return
        embeddings = self._embed(claims)
        self.collection.upsert(
            ids=evidence_ids,
            documents=claims,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(self, text: str, top_k: int = 5) -> dict:
        """Raw Chroma query result for a single text query."""
        query_embedding = self._embed([text])[0]
        return self.collection.query(query_embeddings=[query_embedding], n_results=top_k)