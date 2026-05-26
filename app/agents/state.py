"""
Shared state management for the multi-agent claim auditing system.
Defines ClaimAuditState TypedDict and supporting data models.
"""

from datetime import datetime
from typing import Any, TypedDict


class ClaimAuditState(TypedDict, total=False):
    """
    Shared state dictionary that flows through all agents in the LangGraph workflow.
    Follows the Single State Object pattern for stateful agent execution.
    
    Phase 1: Ingestion
    - claim_id, raw_claim_text, raw_invoice_text, raw_policy_text
    
    Phase 2: Parallel Execution (Policy Analyst & Data Miner)
    - extracted_clauses, customer_history
    
    Phase 3: Synthesis (Fraud Auditor)
    - risk_assessment, suspicious_flags, web_search_results
    
    Phase 4: Reflection (Conditional Routing)
    - iteration_count, requires_clause_clarification
    
    Phase 5: Judgment & Resolution
    - final_decision, payout_amount, justification_matrix
    """
    
    # ========== METADATA ==========
    claim_id: str
    user_id: str
    policy_id: str
    tenant_id: str
    created_at: str
    
    # ========== PHASE 1: INGESTION ==========
    raw_claim_text: str
    raw_invoice_text: str
    raw_policy_text: str
    evidence_files: list[str]  # paths or text summaries
    
    # ========== PHASE 1: STRUCTURED EXTRACTION ==========
    structured_claim: dict[str, Any]
    structured_invoice: dict[str, Any]
    structured_policy: dict[str, Any]
    past_claims_meta: dict[str, Any]
    
    # ========== PHASE 2: POLICY ANALYST OUTPUT ==========
    extracted_clauses: dict[str, Any]
    policy_coverage_limits: dict[str, Any]
    policy_exclusions: list[str]
    applicable_deductibles: dict[str, Any]
    rag_chunks: list[str]
    
    # ========== PHASE 2: DATA MINER OUTPUT ==========
    customer_history: dict[str, Any]
    claims_frequency: int
    payment_status: str
    policy_active_date: str
    previous_claims: list[dict[str, Any]]
    database_alerts: list[str]
    
    # ========== PHASE 3: FRAUD AUDITOR OUTPUT ==========
    risk_assessment: dict[str, Any]
    suspicious_flags: list[str]
    web_search_results: list[dict[str, Any]]
    market_price_analysis: dict[str, Any]
    anomaly_detection: dict[str, Any]
    
    # ========== PHASE 4: REFLECTION & ROUTING ==========
    iteration_count: int
    requires_clause_clarification: bool
    retry_queries: list[str]
    loop_history: list[dict[str, Any]]
    
    # ========== PHASE 5: JUDGE OUTPUT ==========
    final_verdict: str  # APPROVED, DENIED, ESCALATED
    payout_amount: float
    risk_score: float
    fraud_probability: int
    justification_matrix: dict[str, Any]
    decision_rationale: str
    processing_timestamp: str
    
    # ========== ERROR HANDLING ==========
    errors: list[dict[str, Any]]
    warnings: list[str]
    processing_logs: list[str]
