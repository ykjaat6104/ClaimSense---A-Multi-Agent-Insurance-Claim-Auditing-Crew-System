"""
Enhanced LangGraph orchestrator with multi-agent workflow, conditional routing,
and reflection loops for claim auditing.

Graph Flow:
    [Start] 
      ↓
    [Parallel: Policy Analyst + Data Miner]
      ↓
    [Fraud Auditor]
      ↓
    [Conditional Router]
      ├→ YES (needs clarification) → [Policy Analyst] (loop back)
      └→ NO (sufficient data) → [Judge]
      ↓
    [Judge]
      ↓
    [End]
"""

import logging
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.state import ClaimAuditState
from app.agents.nodes import (
    policy_analyst_node,
    data_miner_node,
    fraud_auditor_node,
    judge_node,
)

logger = logging.getLogger(__name__)


def conditional_route_after_audit(state: ClaimAuditState) -> Literal["policy_analyst", "judge"]:
    """
    Routing logic after Fraud Auditor completes.
    
    Determines whether to:
    1. Loop back to Policy Analyst for deeper clause clarification
    2. Proceed directly to Judge for final decision
    
    Conditions for looping:
    - Iteration count < 3 (infinite loop breaker)
    - Specific missing information flags
    - High uncertainty in coverage determination
    """
    iteration_count = state.get("iteration_count", 0)
    
    # Infinite loop breaker
    if iteration_count >= 3:
        logger.info(f"[Router] Max iterations ({iteration_count}) reached. Routing to Judge.")
        return "judge"
    
    # Check if additional clause clarification is needed
    suspicious_flags = state.get("suspicious_flags", [])
    risk_assessment = state.get("risk_assessment", {})
    extracted_clauses = state.get("extracted_clauses", {})
    
    # Flag-based routing: if many high-confidence red flags, escalate to deeper policy review
    high_severity_flags = sum(
        1 for flag in suspicious_flags 
        if any(keyword in flag.lower() for keyword in ["void", "excluded", "exceeds", "fraud"])
    )
    
    # If we found potential coverage violations but clauses are unclear, loop back
    needs_clarification = (
        high_severity_flags > 1 and 
        not extracted_clauses.get("is_covered")
    )
    
    if needs_clarification:
        logger.info(f"[Router] Found {high_severity_flags} high-severity flags. Routing back to Policy Analyst for clarification.")
        return "policy_analyst"
    
    logger.info("[Router] Sufficient evidence gathered. Routing to Judge for final decision.")
    return "judge"


def build_claim_audit_graph() -> StateGraph:
    """
    Construct the complete LangGraph workflow for claim auditing.
    
    Returns:
        Compiled StateGraph with all nodes and edges configured.
    """
    
    graph = StateGraph(ClaimAuditState)
    
    # ========== ADD NODES ==========
    graph.add_node("policy_analyst", policy_analyst_node)
    graph.add_node("data_miner", data_miner_node)
    graph.add_node("fraud_auditor", fraud_auditor_node)
    graph.add_node("judge", judge_node)
    
    # ========== ENTRY POINT ==========
    graph.set_entry_point("policy_analyst")
    
    # ========== EDGES ==========
    
    # Phase 2: Parallel execution
    # Both Policy Analyst and Data Miner run independently (no dependency)
    # They both feed into Fraud Auditor
    graph.add_edge("policy_analyst", "data_miner")
    
    # Phase 3: Convergence point
    graph.add_edge("data_miner", "fraud_auditor")
    
    # Phase 4: Conditional routing with potential reflection loop
    graph.add_conditional_edges(
        "fraud_auditor",
        conditional_route_after_audit,
        {
            "policy_analyst": "policy_analyst",
            "judge": "judge",
        }
    )
    
    # Phase 5: End
    graph.add_edge("judge", END)
    
    return graph


def build_claim_audit_graph_compiled() -> Any:
    """
    Build and compile the claim audit graph into an executable workflow.
    
    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = build_claim_audit_graph()
    return graph.compile()


def run_claim_audit_workflow(
    *,
    claim_id: str,
    user_id: str,
    policy_id: str,
    tenant_id: str = "default",
    structured_claim: dict[str, Any],
    structured_invoice: dict[str, Any],
    structured_policy: dict[str, Any],
    raw_claim_text: str = "",
    raw_invoice_text: str = "",
    raw_policy_text: str = "",
    past_claims_meta: dict[str, Any] | None = None,
    evidence_files: list[str] | None = None,
) -> ClaimAuditState:
    """
    Execute the complete claim audit workflow end-to-end.
    
    This is the main entry point for the multi-agent auditing system.
    
    Args:
        claim_id: Unique claim identifier
        user_id: Customer user ID
        policy_id: Insurance policy ID
        tenant_id: Multi-tenancy identifier
        structured_claim: Parsed claim form data
        structured_invoice: Parsed invoice/repair estimate data
        structured_policy: Parsed policy metadata
        raw_claim_text: Full raw text of claim document
        raw_invoice_text: Full raw text of invoice document
        raw_policy_text: Full raw text of policy document
        past_claims_meta: Metadata about past claims
        evidence_files: List of supporting evidence file paths
    
    Returns:
        Final ClaimAuditState with complete audit trail and decision.
    """
    
    # Initialize the state
    initial_state: ClaimAuditState = {
        # Metadata
        "claim_id": claim_id,
        "user_id": user_id,
        "policy_id": policy_id,
        "tenant_id": tenant_id,
        "created_at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
        
        # Raw texts
        "raw_claim_text": raw_claim_text,
        "raw_invoice_text": raw_invoice_text,
        "raw_policy_text": raw_policy_text,
        "evidence_files": evidence_files or [],
        
        # Structured data
        "structured_claim": structured_claim,
        "structured_invoice": structured_invoice,
        "structured_policy": structured_policy,
        "past_claims_meta": past_claims_meta or {},
        
        # Node outputs (initialized to empty)
        "extracted_clauses": {},
        "policy_coverage_limits": 0,
        "policy_exclusions": [],
        "applicable_deductibles": 0,
        "rag_chunks": [],
        
        "customer_history": {},
        "claims_frequency": 0,
        "payment_status": "UNKNOWN",
        "policy_active_date": "",
        "previous_claims": [],
        "database_alerts": [],
        
        "risk_assessment": {},
        "suspicious_flags": [],
        "web_search_results": [],
        "market_price_analysis": {},
        "anomaly_detection": {},
        
        # Reflection loop tracking
        "iteration_count": 0,
        "requires_clause_clarification": False,
        "retry_queries": [],
        "loop_history": [],
        
        # Final outputs (initialized to empty)
        "final_verdict": "PENDING",
        "payout_amount": 0,
        "risk_score": 0,
        "fraud_probability": 0,
        "justification_matrix": {},
        "decision_rationale": "",
        "processing_timestamp": "",
        
        # Error handling
        "errors": [],
        "warnings": [],
        "processing_logs": [],
    }
    
    try:
        # Compile and execute the graph
        graph = build_claim_audit_graph_compiled()
        
        logger.info(f"[Workflow] Starting claim audit for {claim_id}")
        
        # Run the workflow with streaming to track progress
        final_state = graph.invoke(initial_state)
        
        logger.info(f"[Workflow] Completed claim audit for {claim_id}. Verdict: {final_state.get('final_verdict')}")
        
        return final_state
        
    except Exception as e:
        logger.error(f"[Workflow] Error during claim audit: {e}", exc_info=True)
        initial_state["errors"] = [{"error": str(e), "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat()}]
        initial_state["final_verdict"] = "ESCALATED"
        return initial_state
