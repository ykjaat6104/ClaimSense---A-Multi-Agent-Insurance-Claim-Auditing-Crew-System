from __future__ import annotations

import json
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.services import gemini_client


class AgentState(TypedDict):
    claim_id: str
    structured_claim: dict[str, Any]
    structured_invoice: dict[str, Any]
    structured_policy: dict[str, Any]
    rag_chunks: list[str]
    approve_argument: str
    reject_argument: str
    mediator_output: dict[str, Any]


def _approve_node(state: AgentState) -> dict[str, Any]:
    rag = "\n\n".join(state["rag_chunks"] or [])
    sc = json.dumps(state["structured_claim"], indent=2)
    si = json.dumps(state["structured_invoice"], indent=2)
    sp = json.dumps(state["structured_policy"], indent=2)
    prompt = f"""You are the APPROVE agent in an insurer's claim review workflow.
Argue why this claim should be treated as VALID / COVERED / approvable from a fair underwriting perspective.
Reference retrieved policy snippets when helpful. Be concise but specific.

Structured claim JSON:
{sc}

Structured invoice JSON:
{si}

Structured policy metadata JSON:
{sp}

Retrieved policy excerpts (RAG):
{rag}

Write 2–4 short paragraphs of plain text (no JSON)."""
    text = gemini_client.generate_text(prompt, temperature=0.25)
    return {"approve_argument": text}


def _reject_node(state: AgentState) -> dict[str, Any]:
    rag = "\n\n".join(state["rag_chunks"] or [])
    sc = json.dumps(state["structured_claim"], indent=2)
    si = json.dumps(state["structured_invoice"], indent=2)
    sp = json.dumps(state["structured_policy"], indent=2)
    prompt = f"""You are the RISK / REJECT agent for fraud and leakage detection.
Argue why this claim should be denied, heavily reviewed, or escalated.
Consider inflated invoices, duplicate patterns (if hinted), coverage mismatch, suspicious timing vs policy dates, missing docs.

Structured claim JSON:
{sc}

Structured invoice JSON:
{si}

Structured policy metadata JSON:
{sp}

Retrieved policy excerpts (RAG):
{rag}

Write 2–4 short paragraphs of plain text (no JSON)."""
    text = gemini_client.generate_text(prompt, temperature=0.35)
    return {"reject_argument": text}


def _mediator_node(state: AgentState) -> dict[str, Any]:
    prompt = f"""You are the MEDIATOR. Combine the approve and reject positions into a single decision support outcome.

APPROVE agent:
{state.get("approve_argument", "")}

REJECT / RISK agent:
{state.get("reject_argument", "")}

Return ONLY valid JSON with keys:
decision (string: one of APPROVE, REJECT, REVIEW),
coverage_violation (number 0-1),
invoice_anomaly (number 0-1),
timing_suspicion (number 0-1),
missing_docs (number 0-1),
historical_pattern (number 0-1),
fraud_probability (integer 0-100),
rationale (string, 2-4 sentences).

Use REVIEW when uncertain. Numbers should reflect evidence strength."""
    out = gemini_client.generate_json(prompt, temperature=0.2)
    return {"mediator_output": out}


def build_agent_graph():
    g = StateGraph(AgentState)
    g.add_node("approve", _approve_node)
    g.add_node("reject", _reject_node)
    g.add_node("mediator", _mediator_node)
    g.set_entry_point("approve")
    g.add_edge("approve", "reject")
    g.add_edge("reject", "mediator")
    g.add_edge("mediator", END)
    return g.compile()


def run_agent_graph(
    *,
    claim_id: str,
    structured_claim: dict[str, Any],
    structured_invoice: dict[str, Any],
    structured_policy: dict[str, Any],
    rag_chunks: list[str],
) -> AgentState:
    graph = build_agent_graph()
    initial: AgentState = {
        "claim_id": claim_id,
        "structured_claim": structured_claim,
        "structured_invoice": structured_invoice,
        "structured_policy": structured_policy,
        "rag_chunks": rag_chunks,
        "approve_argument": "",
        "reject_argument": "",
        "mediator_output": {},
    }
    return graph.invoke(initial)
