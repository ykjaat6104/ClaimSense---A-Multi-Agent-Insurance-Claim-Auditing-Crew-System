from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.services import gemini_client


@dataclass
class SimpleVectorIndex:
    """In-memory chunk store with Gemini embeddings (no Chroma — portable on Windows/py313)."""

    chunks: list[str] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)

    @classmethod
    def from_policy_text(cls, policy_text: str) -> SimpleVectorIndex:
        chunks = _chunk_text(policy_text)
        if not chunks:
            chunks = ["(empty policy document)"]
        vecs = gemini_client.embed_documents(chunks)
        return cls(chunks=chunks, vectors=vecs)

    def query(self, query_text: str, k: int = 6) -> list[str]:
        q = query_text.strip() or "insurance coverage limits deductible exclusions"
        qv = gemini_client.embed_query(q[:4000])
        scores: list[tuple[float, int]] = []
        for i, v in enumerate(self.vectors):
            scores.append((_cosine(qv, v), i))
        scores.sort(key=lambda x: x[0], reverse=True)
        out: list[str] = []
        for _, idx in scores[:k]:
            t = self.chunks[idx]
            if t and t not in out:
                out.append(t)
        return out


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        piece = text[start:end]
        if piece.strip():
            chunks.append(piece.strip())
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def ingest_policy(_claim_id: uuid.UUID, policy_text: str) -> SimpleVectorIndex:
    return SimpleVectorIndex.from_policy_text(policy_text)


def retrieve_relevant(index: SimpleVectorIndex, query: str, k: int = 6) -> list[str]:
    return index.query(query, k=k)


def build_rag_query(structured_claim: dict[str, Any], structured_invoice: dict[str, Any]) -> str:
    parts = [
        str(structured_claim.get("damage_type") or structured_claim.get("incident_type") or ""),
        str(structured_claim.get("claimed_amount") or ""),
        str(structured_claim.get("incident_date") or ""),
        str(structured_invoice.get("line_items_summary") or structured_invoice.get("total_amount") or ""),
        str(structured_claim.get("coverage_requested") or ""),
    ]
    return " ".join(p for p in parts if p).strip() or "policy coverage deductible payout limits"
