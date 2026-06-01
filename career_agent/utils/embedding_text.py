"""
Text helpers for safe embedding requests.

The helpers split long strings into smaller paragraph/sentence chunks without
dropping content. API batching is handled separately by the OpenAI client.
"""

from __future__ import annotations

import re


DEFAULT_EMBEDDING_CHUNK_CHARS = 1200


def split_text_for_embedding(
    text: str,
    max_chars: int = DEFAULT_EMBEDDING_CHUNK_CHARS,
) -> list[str]:
    """Split a long string into embedding-friendly chunks without truncation."""
    normalized_text = text.strip()
    if not normalized_text:
        return []

    chunks: list[str] = []
    current = ""

    for paragraph in _split_paragraphs(normalized_text):
        for sentence in _split_sentences(paragraph):
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_hard_split(sentence, max_chars))
                continue

            candidate = f"{current}\n{sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def _split_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n+", text) if part.strip()]


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。！？])\s+", text)
    return [part.strip() for part in parts if part.strip()]


def _hard_split(text: str, max_chars: int) -> list[str]:
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]
