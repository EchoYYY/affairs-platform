"""Ask-the-corpus: retrieval-augmented Q&A grounded in the ingested documents.

Retrieves the most relevant chunks by semantic search, then asks Claude to answer
using only that context, with inline [n] citations mapped back to source documents.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import get_settings
from ..search.semantic import search_chunks

SYSTEM = (
    "You are a medical-device regulatory affairs assistant. Answer the user's "
    "question using ONLY the numbered context passages provided. Cite sources "
    "inline as [1], [2], etc. matching the passage numbers. If the context does "
    "not contain the answer, say so plainly rather than guessing. Be precise about "
    "obligations, actors, and any citations that appear in the text."
)


def ask(
    question: str,
    top_k: int = 8,
    authority: Optional[str] = None,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    hits = search_chunks(question, top_k=top_k, authority=authority, region=region)
    settings = get_settings()

    sources: List[Dict[str, Any]] = []
    seen = set()
    context_blocks = []
    for i, h in enumerate(hits, start=1):
        context_blocks.append(f"[{i}] (from \"{h['title']}\" — {h['authority']})\n{h['text']}")
        key = h["document_id"]
        if key not in seen:
            seen.add(key)
        sources.append({
            "n": i, "document_id": h["document_id"], "title": h["title"],
            "authority": h["authority"], "region": h["region"],
            "rel_path": h["rel_path"], "score": round(h["score"], 3),
            "snippet": h["text"][:240],
        })

    if not hits:
        return {"answer": "No relevant content found in the corpus for that question.",
                "sources": [], "grounded": False}

    if not settings.claude_enabled:
        # Degrade to extractive: return the top passages without a synthesized answer.
        return {
            "answer": "(Claude API key not set — showing the most relevant passages. "
                      "Add ANTHROPIC_API_KEY to enable synthesized answers.)",
            "sources": sources, "grounded": False,
        }

    from anthropic import Anthropic

    client = Anthropic(api_key=settings.anthropic_api_key)
    context = "\n\n".join(context_blocks)
    resp = client.messages.create(
        model=settings.model,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{
            "role": "user",
            "content": f"Context passages:\n\n{context}\n\nQuestion: {question}",
        }],
    )
    answer = "".join(b.text for b in resp.content if b.type == "text")
    return {"answer": answer, "sources": sources, "grounded": True}
