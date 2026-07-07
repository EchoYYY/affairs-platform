"""Split extracted document text into overlapping chunks for embedding.

Word-based sliding window keeps chunks within the embedding model's context
while overlap preserves cross-boundary meaning. Good enough for retrieval; we
are not trying to respect semantic section boundaries at this stage.
"""
from __future__ import annotations

import re
from typing import List

# ~350 words ≈ 450-500 tokens, comfortably within bge-small's 512-token window.
DEFAULT_CHUNK_WORDS = 350
DEFAULT_OVERLAP_WORDS = 60


def normalize(text: str) -> str:
    # collapse runs of whitespace but keep paragraph breaks meaningful
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> List[str]:
    text = normalize(text)
    if not text:
        return []
    words = text.split()
    if len(words) <= chunk_words:
        return [" ".join(words)]

    step = max(1, chunk_words - overlap_words)
    chunks: List[str] = []
    for start in range(0, len(words), step):
        window = words[start : start + chunk_words]
        if not window:
            break
        chunks.append(" ".join(window))
        if start + chunk_words >= len(words):
            break
    return chunks
