"""
LangChain embeddings adapter backed by the project OpenAI-compatible client.
"""

from __future__ import annotations

from typing import List

from clients.openai_client import OpenAIClientWrapper
from utils.embedding_text import split_text_for_embedding


class OpenAIEmbeddingAdapter:
    """Adapt OpenAIClientWrapper to the LangChain Embeddings interface."""

    def __init__(self, client_wrapper: OpenAIClientWrapper) -> None:
        self._client_wrapper = client_wrapper

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._client_wrapper.embed_texts(texts)

    def embed_query(self, text: str) -> List[float]:
        chunks = split_text_for_embedding(text)
        vectors = self._client_wrapper.embed_texts(chunks)
        return _average_vectors(vectors)

    def __call__(self, text: str) -> List[float]:
        """Compatibility for LangChain FAISS versions expecting a callable."""
        return self.embed_query(text)


def _average_vectors(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        return []

    vector_count = len(vectors)
    dimension = len(vectors[0])
    return [
        sum(vector[index] for vector in vectors) / vector_count
        for index in range(dimension)
    ]
