from __future__ import annotations

import logging
from typing import Any

from app.services.policy_graph import PolicyKnowledgeGraph
from app.services.rag_service import SimpleVectorIndex, build_rag_query

logger = logging.getLogger(__name__)


class HybridRAGResult:
    def __init__(
        self,
        chunks: list[str],
        method_used: str,
        clause_relationships: dict[str, Any] | None = None,
        graph_nodes_used: int = 0,
    ):
        self.chunks = chunks
        self.method_used = method_used
        self.clause_relationships = clause_relationships
        self.graph_nodes_used = graph_nodes_used

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunks": self.chunks,
            "method_used": self.method_used,
            "clause_relationships": self.clause_relationships,
            "graph_nodes_used": self.graph_nodes_used,
        }


def retrieve_policy_context(
    policy_text: str,
    claim_context: str,
    structured_claim: dict[str, Any] | None = None,
    structured_invoice: dict[str, Any] | None = None,
    k: int = 6,
) -> HybridRAGResult:
    if structured_claim is not None and structured_invoice is not None:
        query = build_rag_query(structured_claim, structured_invoice)
    else:
        query = claim_context.strip() or "insurance coverage limits deductible exclusions"

    graph = PolicyKnowledgeGraph(policy_text, min_clauses=2)

    if graph.parsed and len(graph.nodes) >= 3:
        logger.info(
            f"[HybridRAG] Graph parsed successfully: {len(graph.nodes)} nodes, "
            f"{len(graph.edges)} edges — using graph-aware hybrid retrieval"
        )
        try:
            graph_results = graph.query(query, k=k)
            graph_chunks = []
            clause_relationships: dict[str, Any] = {"nodes": [], "edges": [], "coverage_exclusion_pairs": []}

            for r in graph_results:
                graph_chunks.append(r["text"])
                clause_relationships["nodes"].append(
                    {"id": r["clause_id"], "type": r["clause_type"], "title": r["title"]}
                )
                for rel in r.get("related_clauses", []):
                    clause_relationships["edges"].append(
                        {"source": r["clause_id"], "target": rel["clause_id"], "type": "RELATED_TO"}
                    )

            pairs = graph.get_coverage_exclusion_pairs()
            for p in pairs:
                clause_relationships["coverage_exclusion_pairs"].append(p)

            if graph_chunks:
                vec_index = SimpleVectorIndex.from_policy_text(policy_text)
                vec_chunks = vec_index.hybrid_query(query, k=k)

                seen = set(graph_chunks)
                for c in vec_chunks:
                    if c not in seen:
                        graph_chunks.append(c)
                        seen.add(c)

                return HybridRAGResult(
                    chunks=graph_chunks[:k],
                    method_used="hybrid_graph",
                    clause_relationships=clause_relationships if clause_relationships["nodes"] else None,
                    graph_nodes_used=len(graph.nodes),
                )
        except Exception as e:
            logger.warning(f"[HybridRAG] Graph retrieval failed, falling back: {e}")

    logger.info("[HybridRAG] Graph not available — using vector+BM25 hybrid retrieval")
    try:
        index = SimpleVectorIndex.from_policy_text(policy_text)
        chunks = index.hybrid_query(query, k=k)
        if chunks:
            return HybridRAGResult(
                chunks=chunks,
                method_used="hybrid_vector",
                clause_relationships=None,
                graph_nodes_used=0,
            )
    except Exception as e:
        logger.warning(f"[HybridRAG] Hybrid retrieval failed, falling back: {e}")

    logger.info("[HybridRAG] Falling back to simple vector-only retrieval")
    try:
        index = SimpleVectorIndex.from_policy_text(policy_text)
        chunks = index.query(query, k=k)
        return HybridRAGResult(
            chunks=chunks,
            method_used="simple_fallback",
            clause_relationships=None,
            graph_nodes_used=0,
        )
    except Exception as e:
        logger.error(f"[HybridRAG] All retrieval methods failed: {e}")
        return HybridRAGResult(
            chunks=[],
            method_used="failed",
            clause_relationships=None,
            graph_nodes_used=0,
        )
