"""Local text embeddings via fastembed (ONNX, CPU, no PyTorch).

The model is downloaded once on first use and cached under the fastembed cache
dir. Embeddings are L2-normalized so cosine similarity reduces to a dot product.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

import numpy as np

from ..config import get_settings


@lru_cache(maxsize=1)
def _model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=get_settings().embed_model)


def embed_texts(texts: List[str]) -> np.ndarray:
    """Embed a list of texts -> (n, dim) float32 array, L2-normalized."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    vecs = np.array(list(_model().embed(texts)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vecs / norms


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string -> (dim,) float32 vector, L2-normalized."""
    return embed_texts([text])[0]


def to_blob(vec: np.ndarray) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)
