from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class ClauseType:
    COVERAGE = "coverage"
    EXCLUSION = "exclusion"
    LIMIT = "limit"
    DEDUCTIBLE = "deductible"
    CONDITION = "condition"
    DEFINITION = "definition"
    ENDORSEMENT = "endorsement"


class RelationshipType:
    EXCLUDES = "EXCLUDES"
    LIMITS = "LIMITS"
    REQUIRES = "REQUIRES"
    DEFINES = "DEFINES"
    MODIFIES = "MODIFIES"
    SUBSUMES = "SUBSUMES"


@dataclass
class ClauseNode:
    clause_id: str
    clause_type: str
    title: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RelationshipEdge:
    source_id: str
    target_id: str
    rel_type: str
    metadata: dict[str, Any] = field(default_factory=dict)


_SECTION_HEADING_RE = re.compile(
    r"^(?:Section|Article|Part|SCHEDULE)\s+[IVXLCDM\d]+[\.\-\)–\s]+(.+)$"
    r"|^([A-Z][A-Z\s]{2,50}?(?:COVERAGE|EXCLUSION|LIMIT|DEDUCTIBLE|CONDITION|DEFINITION|LIABILITY|PROPERTY)[A-Z\s]{0,50})$"
    r"|^(?:COVERAGE|EXCLUSION|LIMIT|DEDUCTIBLE|CONDITION|DEFINITION|LIABILITY|PROPERTY)[A-Z\s]{0,50}$",
    re.MULTILINE | re.IGNORECASE,
)

_CLAUSE_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    (
        ClauseType.DEDUCTIBLE,
        "deductible",
        re.compile(
            r"^(?:DEDUCTIBLE|EXCESS|AMOUNTS\s+NOT\s+COVERED|YOU\s+PAY)",
            re.IGNORECASE,
        ),
    ),
    (
        ClauseType.EXCLUSION,
        "exclusion",
        re.compile(
            r"^(?:EXCLUSION|WE\s+DO\s+NOT\s+COVER|WHAT\s+WE\s+DO\s+NOT\s+COVER|LOSSES\s+NOT\s+COVERED|THIS\s+INSURANCE\s+DOES\s+NOT\s+COVER)",
            re.IGNORECASE,
        ),
    ),
    (
        ClauseType.LIMIT,
        "limit",
        re.compile(
            r"^(?:LIMIT\s+OF\s+LIABILITY|COVERAGE\s+LIMIT|POLICY\s+LIMIT|MAXIMUM\s+PAYOUT|LIMITS)",
            re.IGNORECASE,
        ),
    ),
    (
        ClauseType.COVERAGE,
        "coverage",
        re.compile(
            r"^(?:COVERAGE|WE\s+COVER|WE\s+PAY|INSURING\s+AGREEMENT|WHAT\s+WE\s+COVER|DWELLING|PROPERTY)",
            re.IGNORECASE,
        ),
    ),
    (
        ClauseType.CONDITION,
        "condition",
        re.compile(
            r"^(?:CONDITION|DUTY|YOU\s+MUST|REQUIREMENT|REPORTING|NOTICE|COOPERATION|SUBROGATION)",
            re.IGNORECASE,
        ),
    ),
    (
        ClauseType.DEFINITION,
        "definition",
        re.compile(
            r"^(?:DEFINITION|MEANS|TERMS?\s+USED|DEFINED\s+TERMS)",
            re.IGNORECASE,
        ),
    ),
]

_RELATIONSHIP_RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (re.compile(r"exclud|exclus|not\s+cover", re.IGNORECASE), ClauseType.EXCLUSION, "source", RelationshipType.EXCLUDES),
    (re.compile(r"limit|maximum|caps?\s+at|limit\s+of\s+liability", re.IGNORECASE), ClauseType.LIMIT, "source", RelationshipType.LIMITS),
    (re.compile(r"must|required|shall|condition|duty|requirement", re.IGNORECASE), ClauseType.CONDITION, "source", RelationshipType.REQUIRES),
    (re.compile(r"defin|means\s*:|shall\s*mean|shall\s+include", re.IGNORECASE), ClauseType.DEFINITION, "source", RelationshipType.DEFINES),
    (re.compile(r"endorsement|amendment|rider|modification", re.IGNORECASE), ClauseType.ENDORSEMENT, "source", RelationshipType.MODIFIES),
]


def _extract_sections(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue

        heading_match = _SECTION_HEADING_RE.match(stripped)
        if heading_match:
            title = (heading_match.group(1) or heading_match.group(2) or heading_match.group(0)).strip()
            if current_section:
                current_section["text"] = current_section["text"].strip()
                sections.append(current_section)
            current_section = {
                "title": title,
                "text": "",
                "start_line": i,
            }
        elif current_section is not None:
            current_section["text"] += stripped + "\n"

    if current_section:
        current_section["text"] = current_section["text"].strip()
        sections.append(current_section)

    if not sections:
        fallback = _fallback_split(text)
        sections = [{"title": title, "text": t.strip(), "start_line": 0} for title, t in fallback]

    return sections


def _fallback_split(text: str) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []
    current_label = "Policy Document"
    current_lines: list[str] = []
    for p in paragraphs:
        label = _detect_label(p)
        if label:
            if current_lines:
                chunks.append((current_label, "\n\n".join(current_lines)))
            current_label = label
            current_lines = [p]
        else:
            current_lines.append(p)
    if current_lines:
        chunks.append((current_label, "\n\n".join(current_lines)))
    return chunks


_DETECT_LABEL_RE = re.compile(
    r"^(?:Section|Article|Part|SCHEDULE|COVERAGE|EXCLUSION|DEDUCTIBLE|LIMIT|CONDITION|DEFINITION)",
    re.IGNORECASE,
)


def _detect_label(text: str) -> str | None:
    m = _DETECT_LABEL_RE.match(text.strip())
    if m:
        return m.group(0).capitalize()
    return None


def _classify_clause(title: str, text: str) -> str:
    for clause_type, _keyword, pattern in _CLAUSE_PATTERNS:
        if pattern.search(title.strip()):
            return clause_type
    combined = f"{title} {text[:200]}"
    for clause_type, _keyword, pattern in _CLAUSE_PATTERNS:
        if pattern.search(combined):
            return clause_type
    return ClauseType.CONDITION


def _normalize_id(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")
    return slug[:60] or "clause"


class PolicyKnowledgeGraph:
    def __init__(self, policy_text: str, min_clauses: int = 2):
        self.nodes: dict[str, ClauseNode] = {}
        self.edges: list[RelationshipEdge] = []
        self.parsed: bool = False
        self._build(policy_text, min_clauses)

    def _build(self, text: str, min_clauses: int) -> None:
        if not text or not text.strip():
            logger.warning("[PolicyGraph] Empty policy text — graph not built")
            return

        sections = _extract_sections(text)
        if len(sections) < min_clauses:
            logger.warning(
                f"[PolicyGraph] Only {len(sections)} section(s) found (need {min_clauses}) — graph not built"
            )
            return

        for s in sections:
            clause_type = _classify_clause(s["title"], s["text"])
            cid = _normalize_id(s["title"])
            dedup_key = f"{clause_type}::{cid}"
            if dedup_key not in self.nodes:
                node = ClauseNode(
                    clause_id=dedup_key,
                    clause_type=clause_type,
                    title=s["title"],
                    text=s["text"][:2000],
                    metadata={"char_count": len(s["text"])},
                )
                self.nodes[dedup_key] = node

        self._infer_relationships()
        self.parsed = len(self.nodes) >= min_clauses
        logger.info(
            f"[PolicyGraph] Built graph with {len(self.nodes)} nodes, {len(self.edges)} edges"
        )

    def _infer_relationships(self) -> None:
        coverage_nodes = [n for n in self.nodes.values() if n.clause_type == ClauseType.COVERAGE]
        other_nodes = [
            n
            for n in self.nodes.values()
            if n.clause_type != ClauseType.COVERAGE
        ]

        for cov_node in coverage_nodes:
            for other in other_nodes:
                matched_rel = self._match_relationship(other, cov_node)
                if matched_rel:
                    self.edges.append(
                        RelationshipEdge(
                            source_id=cov_node.clause_id,
                            target_id=other.clause_id,
                            rel_type=matched_rel,
                            metadata={"inferred": True},
                        )
                    )

        for i, node_a in enumerate(list(self.nodes.values())):
            for node_b in list(self.nodes.values())[i + 1 :]:
                if self._is_same_type_group(node_a, node_b):
                    self.edges.append(
                        RelationshipEdge(
                            source_id=node_a.clause_id,
                            target_id=node_b.clause_id,
                            rel_type=RelationshipType.SUBSUMES,
                            metadata={"sibling": True},
                        )
                    )

    def _match_relationship(self, clause: ClauseNode, coverage: ClauseNode) -> str | None:
        combined = f"{clause.title} {clause.text[:300]}"
        for pattern, clause_type, _direction, rel_type in _RELATIONSHIP_RULES:
            if clause.clause_type == clause_type and pattern.search(combined):
                return rel_type
        return None

    @staticmethod
    def _is_same_type_group(a: ClauseNode, b: ClauseNode) -> bool:
        return a.clause_type == b.clause_type

    def query(
        self, claim_context: str, k: int = 6
    ) -> list[dict[str, Any]]:
        search_terms = set(
            w.lower()
            for w in re.findall(r"[a-zA-Z]{3,}", claim_context)
            if w.lower()
            not in {
                "the",
                "and",
                "for",
                "with",
                "from",
                "that",
                "this",
                "what",
                "was",
                "are",
                "has",
                "had",
                "not",
            }
        )

        scored: list[tuple[float, ClauseNode]] = []
        for node in self.nodes.values():
            score = self._score_node(node, search_terms)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_nodes = [node for _score, node in scored[:k]]

        results: list[dict[str, Any]] = []
        for node in top_nodes:
            related = self.get_related_clauses(node.clause_id, max_depth=1)
            results.append(
                {
                    "clause_id": node.clause_id,
                    "clause_type": node.clause_type,
                    "title": node.title,
                    "text": node.text[:1000],
                    "score": round(scored[[n.clause_id for _, n in scored].index(node.clause_id)][0], 4)
                    if any(n.clause_id == node.clause_id for _, n in scored)
                    else 0.0,
                    "related_clauses": [
                        {"clause_id": r.clause_id, "clause_type": r.clause_type, "title": r.title}
                        for r in related
                    ],
                }
            )

        return results

    def _score_node(self, node: ClauseNode, terms: set[str]) -> float:
        text_lower = f"{node.title} {node.text}".lower()
        term_matches = sum(1 for t in terms if t in text_lower)
        if term_matches == 0:
            return 0.0
        base = term_matches / max(len(terms), 1)
        type_boost = {
            ClauseType.COVERAGE: 1.3,
            ClauseType.EXCLUSION: 1.2,
            ClauseType.DEDUCTIBLE: 1.1,
            ClauseType.LIMIT: 1.1,
            ClauseType.CONDITION: 1.0,
            ClauseType.DEFINITION: 0.9,
            ClauseType.ENDORSEMENT: 1.0,
        }.get(node.clause_type, 1.0)
        return base * type_boost

    def get_related_clauses(
        self, clause_id: str, max_depth: int = 2
    ) -> list[ClauseNode]:
        visited: set[str] = set()
        result: list[ClauseNode] = []
        queue = [(clause_id, 0)]

        while queue:
            cid, depth = queue.pop(0)
            if cid in visited or depth > max_depth:
                continue
            visited.add(cid)
            if cid != clause_id and cid in self.nodes:
                result.append(self.nodes[cid])
            for edge in self.edges:
                if edge.source_id == cid and edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1))
                if edge.target_id == cid and edge.source_id not in visited:
                    queue.append((edge.source_id, depth + 1))

        return result

    def get_coverage_exclusion_pairs(self) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        for edge in self.edges:
            if edge.rel_type == RelationshipType.EXCLUDES:
                source = self.nodes.get(edge.source_id)
                target = self.nodes.get(edge.target_id)
                if source and target:
                    pairs.append(
                        {
                            "coverage": {"title": source.title, "text": source.text[:500]},
                            "exclusion": {"title": target.title, "text": target.text[:500]},
                        }
                    )
        return pairs

    def to_dict(self) -> dict[str, Any]:
        return {
            "parsed": self.parsed,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [
                {"id": n.clause_id, "type": n.clause_type, "title": n.title} for n in self.nodes.values()
            ],
            "edges": [
                {"source": e.source_id, "target": e.target_id, "type": e.rel_type} for e in self.edges
            ],
        }
