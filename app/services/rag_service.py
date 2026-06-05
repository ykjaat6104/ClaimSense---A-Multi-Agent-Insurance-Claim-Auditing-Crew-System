from __future__ import annotations

import collections
import math
import re
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.services import gemini_client


@dataclass
class _BM25Index:
    corpus: list[str] = field(default_factory=list)
    avg_doc_len: float = 0.0
    doc_count: int = 0
    idf: dict[str, float] = field(default_factory=dict)
    doc_term_counts: list[collections.Counter[str]] = field(default_factory=list)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z]{2,}", text.lower())

    @classmethod
    def build(cls, documents: list[str]) -> _BM25Index:
        tokenized: list[list[str]] = [cls._tokenize(d) for d in documents]
        doc_count = len(tokenized)
        doc_term_counts: list[collections.Counter[str]] = [collections.Counter(t) for t in tokenized]
        doc_lens = [len(t) for t in tokenized]
        avg_doc_len = sum(doc_lens) / max(doc_count, 1)

        df: collections.Counter[str] = collections.Counter()
        for counter in doc_term_counts:
            for term in counter:
                df[term] += 1

        idf: dict[str, float] = {}
        for term, doc_freq in df.items():
            idf[term] = math.log(1 + (doc_count - doc_freq + 0.5) / (doc_freq + 0.5))
        idf["__UNKNOWN__"] = 0.0

        return cls(
            corpus=documents,
            avg_doc_len=avg_doc_len,
            doc_count=doc_count,
            idf=idf,
            doc_term_counts=doc_term_counts,
        )

    def score(self, query: str, doc_idx: int, k1: float = 1.5, b: float = 0.75) -> float:
        query_terms = self._tokenize(query)
        if not query_terms:
            return 0.0
        counter = self.doc_term_counts[doc_idx]
        doc_len = sum(counter.values())
        score = 0.0
        for term in query_terms:
            tf = counter.get(term, 0)
            if tf == 0:
                continue
            idf_val = self.idf.get(term, self.idf["__UNKNOWN__"])
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / max(self.avg_doc_len, 1))
            score += idf_val * numerator / max(denominator, 1e-10)
        return score


def _reciprocal_rank_fuse(
    vector_scores: list[tuple[float, int]],
    bm25_scores: list[tuple[float, int]],
    k: int = 6,
    k_constant: int = 60,
) -> list[int]:
    vector_ranked = {idx: rank for rank, (_, idx) in enumerate(sorted(vector_scores, key=lambda x: x[0], reverse=True))}
    bm25_ranked = {idx: rank for rank, (_, idx) in enumerate(sorted(bm25_scores, key=lambda x: x[0], reverse=True))}

    all_indices = set(vector_ranked.keys()) | set(bm25_ranked.keys())
    fused: list[tuple[float, int]] = []
    for idx in all_indices:
        vec_rrf = 1.0 / (k_constant + vector_ranked.get(idx, len(all_indices)))
        bm25_rrf = 1.0 / (k_constant + bm25_ranked.get(idx, len(all_indices)))
        fused.append((vec_rrf + bm25_rrf, idx))

    fused.sort(key=lambda x: x[0], reverse=True)
    return [idx for _, idx in fused[:k]]


@dataclass
class SimpleVectorIndex:
    """In-memory chunk store with Gemini embeddings (no Chroma — portable on Windows/py313).
    Supports vector-only, BM25, and hybrid (RRF-fused) retrieval.
    """

    chunks: list[str] = field(default_factory=list)
    vectors: list[list[float]] = field(default_factory=list)
    bm25_index: _BM25Index | None = None

    @classmethod
    def from_policy_text(cls, policy_text: str) -> SimpleVectorIndex:
        chunks = _chunk_text(policy_text)
        if not chunks:
            chunks = ["(empty policy document)"]
        vecs = gemini_client.embed_documents(chunks)
        bm25 = _BM25Index.build(chunks)
        return cls(chunks=chunks, vectors=vecs, bm25_index=bm25)

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

    def hybrid_query(self, query_text: str, k: int = 6) -> list[str]:
        q = query_text.strip() or "insurance coverage limits deductible exclusions"
        qv = gemini_client.embed_query(q[:4000])
        vector_scores: list[tuple[float, int]] = []
        for i, v in enumerate(self.vectors):
            vector_scores.append((_cosine(qv, v), i))

        bm25_scores: list[tuple[float, int]] = []
        if self.bm25_index:
            for i in range(len(self.chunks)):
                bm25_scores.append((self.bm25_index.score(q, i), i))
        else:
            bm25_scores = vector_scores

        fused_indices = _reciprocal_rank_fuse(vector_scores, bm25_scores, k=k)
        out: list[str] = []
        for idx in fused_indices:
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
