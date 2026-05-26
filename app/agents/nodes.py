"""
Individual agent node implementations for the multi-agent claim auditing system.

Node 1: RAG Policy Analyst (The Scholar)
Node 2: Data Miner Agent (The Investigator)
Node 3: Fraud Auditor Agent (The Cynic)
Node 4: Judge/Decision Node (The Final Arbitrator)
"""

import json
import logging
from typing import Any

from app.agents.state import ClaimAuditState
from app.agents.tools import (
    get_user_claims_history,
    get_payment_status,
    get_policy_recent_changes,
    check_duplicate_claims,
    search_market_price,
    search_regional_repair_rates,
    verify_invoice_authenticity,
    extract_coverage_limits_from_text,
    check_fraud_exclusions,
)
from app.services import gemini_client

logger = logging.getLogger(__name__)


# ========== NODE 1: RAG POLICY ANALYST ==========

def policy_analyst_node(state: ClaimAuditState) -> dict[str, Any]:
    """
    Node 1: The RAG Policy Analyst (The Scholar)
    
    Role: Determine exactly what the customer's insurance contract covers.
    
    Process:
    1. Takes policy_id and structured_claim from state
    2. Runs similarity search against vector database using localized embeddings
    3. Extracts coverage limits, deductibles, exclusions
    4. Returns structured clause data
    
    Output fields:
    - extracted_clauses
    - policy_coverage_limits
    - policy_exclusions
    - applicable_deductibles
    - rag_chunks
    """
    logger.info(f"[Policy Analyst] Processing claim {state.get('claim_id')}")
    
    try:
        # Build RAG query from structured claim and invoice
        claim_details = state.get("structured_claim", {})
        invoice_details = state.get("structured_invoice", {})
        policy_text = state.get("raw_policy_text", "")
        
        # Construct search query
        damage_type = claim_details.get("damage_type") or claim_details.get("incident_type") or ""
        claimed_amount = claim_details.get("claimed_amount", "")
        coverage_requested = claim_details.get("coverage_requested", "")
        
        rag_query = f"{damage_type} {claimed_amount} {coverage_requested}".strip()
        
        # In production, this would query ChromaDB/FAISS
        # For now, using the existing SimpleVectorIndex
        from app.services.rag_service import ingest_policy, retrieve_relevant
        
        vector_index = ingest_policy(state.get("claim_id"), policy_text)
        rag_chunks = retrieve_relevant(vector_index, rag_query, k=6)
        
        # Extract coverage limits using LLM
        extraction_prompt = f"""Analyze this insurance policy and extract key coverage details for a {damage_type} claim.

Policy excerpts:
{chr(10).join(rag_chunks)}

Provide structured JSON with:
- coverage_limit (float)
- deductible (float)
- coverage_percentage (0-100)
- exclusions (list of strings)
- conditions (list of strings)
- is_covered (boolean)
"""
        
        coverage_data = gemini_client.generate_json(extraction_prompt, temperature=0.2)
        
        # Check for fraud/misrepresentation exclusions
        fraud_check_prompt = f"""Does this insurance policy contain fraud or misrepresentation exclusions?

Policy excerpts:
{chr(10).join(rag_chunks)}

Provide JSON:
- has_fraud_exclusion (boolean)
- fraud_clause_text (string)
- timeline_days (int, days within which fraud voids coverage)
"""
        
        fraud_data = gemini_client.generate_json(fraud_check_prompt, temperature=0.1)
        
        output = {
            "extracted_clauses": coverage_data,
            "policy_coverage_limits": coverage_data.get("coverage_limit", 0),
            "policy_exclusions": coverage_data.get("exclusions", []),
            "applicable_deductibles": coverage_data.get("deductible", 0),
            "rag_chunks": rag_chunks,
        }
        
        logger.info(f"[Policy Analyst] Completed analysis. Found {len(rag_chunks)} relevant chunks.")
        return output
        
    except Exception as e:
        logger.error(f"[Policy Analyst] Error: {e}", exc_info=True)
        return {
            "extracted_clauses": {},
            "policy_coverage_limits": 0,
            "policy_exclusions": [],
            "applicable_deductibles": 0,
            "rag_chunks": [],
        }


# ========== NODE 2: DATA MINER AGENT ==========

def data_miner_node(state: ClaimAuditState) -> dict[str, Any]:
    """
    Node 2: The Data Miner Agent (The Investigator)
    
    Role: Uncover the user's operational and financial history.
    
    Process:
    1. Executes deterministic Python functions connected to PostgreSQL
    2. Retrieves: claims history, payment status, policy changes
    3. Analyzes temporal patterns (policy date vs claim date)
    4. Returns customer profile digest
    
    Output fields:
    - customer_history
    - claims_frequency
    - payment_status
    - policy_active_date
    - previous_claims
    - database_alerts
    """
    logger.info(f"[Data Miner] Processing claim {state.get('claim_id')}")
    
    try:
        user_id = state.get("user_id", "")
        policy_id = state.get("policy_id", "")
        claim_incident_date = state.get("structured_claim", {}).get("incident_date", "")
        
        # Execute database queries in parallel conceptually (could use ThreadPoolExecutor)
        claims_history = get_user_claims_history(user_id, days_back=365)
        payment_status = get_payment_status(user_id, policy_id)
        policy_changes = get_policy_recent_changes(policy_id)
        
        # Check for duplicates
        claim_desc = state.get("structured_claim", {}).get("claim_description", "")
        duplicates = check_duplicate_claims(user_id, claim_desc)
        
        # Compile alerts
        database_alerts = []
        
        # Alert on high frequency
        if claims_history.get("claims_last_30_days", 0) > 1:
            database_alerts.append(f"Multiple claims filed in last 30 days: {claims_history['claims_last_30_days']}")
        
        # Alert on lapsed payments
        if payment_status.get("current_status") != "ACTIVE":
            database_alerts.append(f"Policy status: {payment_status.get('current_status')}")
        
        # Alert on recent policy changes
        if policy_changes.get("suspicious_timing"):
            time_since = policy_changes.get("time_since_last_change_days", 999)
            database_alerts.append(f"Policy modified {time_since} days ago, just before claim")
        
        # Alert on potential duplicates
        if duplicates.get("flagged_as_duplicate"):
            database_alerts.append(f"Similar claim detected with {duplicates.get('matching_score', 0):.1%} match score")
        
        output = {
            "customer_history": {
                "user_id": user_id,
                "policy_id": policy_id,
                "claims_frequency": claims_history.get("total_claims_12m", 0),
                "payment_status": payment_status.get("current_status", "UNKNOWN"),
                "policy_active_since": payment_status.get("policy_active_since", ""),
            },
            "claims_frequency": claims_history.get("total_claims_12m", 0),
            "payment_status": payment_status.get("current_status", "UNKNOWN"),
            "policy_active_date": payment_status.get("policy_active_since", ""),
            "previous_claims": claims_history.get("claim_ids", []),
            "database_alerts": database_alerts,
        }
        
        logger.info(f"[Data Miner] Found {len(database_alerts)} alerts for user {user_id}")
        return output
        
    except Exception as e:
        logger.error(f"[Data Miner] Error: {e}", exc_info=True)
        return {
            "customer_history": {},
            "claims_frequency": 0,
            "payment_status": "UNKNOWN",
            "policy_active_date": "",
            "previous_claims": [],
            "database_alerts": [],
        }


# ========== NODE 3: FRAUD AUDITOR AGENT ==========

def fraud_auditor_node(state: ClaimAuditState) -> dict[str, Any]:
    """
    Node 3: The Fraud Auditor Agent (The Cynic)
    
    Role: Critique the information and look for anomalies using ML-based fraud detection.
    
    Process:
    1. Ingests Policy Analyst and Data Miner outputs
    2. Executes web searches for market prices and vendor verification
    3. Runs ML-based fraud detection (isolation forest, pattern recognition)
    4. Compiles suspicious flags with ML signals
    5. Assigns risk scores to different dimensions
    
    Output fields:
    - risk_assessment
    - suspicious_flags
    - web_search_results
    - market_price_analysis
    - anomaly_detection
    - ml_fraud_signals (NEW)
    - fraud_detection_result (NEW)
    """
    logger.info(f"[Fraud Auditor] Processing claim {state.get('claim_id')}")
    
    try:
        from pathlib import Path
        from app.services.fraud_detection_v2 import FraudDetectionEngine
        
        suspicious_flags = list(state.get("database_alerts", []))  # Start with DB alerts
        web_search_results = []
        market_price_analysis = {}
        ml_fraud_signals = []
        
        # Get invoice and claim details
        invoice = state.get("structured_invoice", {})
        claim = state.get("structured_claim", {})
        policy_limits = state.get("policy_coverage_limits", 0)
        
        claimed_amount = float(claim.get("claimed_amount") or 0)
        invoice_total = float(invoice.get("total_amount") or 0)
        
        # Flag 1: Amount discrepancy
        if claimed_amount and invoice_total:
            discrepancy = abs(claimed_amount - invoice_total) / max(claimed_amount, invoice_total)
            if discrepancy > 0.15:
                suspicious_flags.append(f"Claimed amount (${claimed_amount}) vs invoice (${invoice_total}) differ by {discrepancy:.1%}")
        
        # Flag 2: Exceeds coverage limit
        if claimed_amount > policy_limits > 0:
            suspicious_flags.append(f"Claim amount (${claimed_amount}) exceeds policy limit (${policy_limits})")
        
        # Flag 3: Web search for market price verification
        if "item_name" in invoice:
            item = invoice["item_name"]
            market_data = search_market_price(item)
            if market_data.get("data_quality") != "ERROR":
                web_search_results.append(market_data)
                
                fair_value = market_data.get("fair_market_value", 0)
                if fair_value and claimed_amount > fair_value * 1.5:
                    suspicious_flags.append(
                        f"Claimed value (${claimed_amount}) significantly exceeds fair market value (${fair_value})"
                    )
                    market_price_analysis[item] = {
                        "claimed": claimed_amount,
                        "fair_market": fair_value,
                        "inflation_ratio": claimed_amount / fair_value if fair_value > 0 else 0,
                    }
        
        # Flag 4: Vendor verification
        if "vendor_name" in invoice:
            vendor_check = verify_invoice_authenticity(invoice["vendor_name"])
            if vendor_check.get("red_flags"):
                suspicious_flags.extend(vendor_check["red_flags"])
            web_search_results.append(vendor_check)
        
        # Flag 5: Repair cost reasonableness
        if "repair_description" in claim:
            repair_rates = search_regional_repair_rates(claim["repair_description"])
            if repair_rates.get("average_cost"):
                web_search_results.append(repair_rates)
                avg_cost = repair_rates["average_cost"]
                if claimed_amount > avg_cost * 2:
                    suspicious_flags.append(
                        f"Repair quote (${claimed_amount}) is 2x regional average (${avg_cost})"
                    )
        
        # NEW: ML-Based Fraud Detection
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "fraud_detection_config.yaml"
            fraud_engine = FraudDetectionEngine(config_path)
            
            # Prepare claim data for fraud detection
            claim_data = {
                "claim_id": state.get("claim_id", "unknown"),
                "claimed_amount": claimed_amount,
                "invoice_amount": invoice_total,
                "incident_date": claim.get("incident_date", ""),
                "policy_start": claim.get("policy_start", ""),
                "policy_end": claim.get("policy_end", ""),
                "vendor_issues": invoice.get("vendor_issues", []),
                "avg_claim_amount": 5000.0,  # Default average
            }
            
            # Prepare market data
            market_data_for_fraud = None
            if market_price_analysis:
                market_data_for_fraud = {
                    "market_price": float(list(market_price_analysis.values())[0].get("fair_market", 0)) if market_price_analysis else 0,
                }
            
            # Run fraud detection
            fraud_result = fraud_engine.analyze_claim(
                claim_data=claim_data,
                market_data=market_data_for_fraud,
                historical_claims=None,  # Would come from state if available
                adjuster_data=None,
            )
            
            # Convert fraud signals to suspicious flags
            for signal in fraud_result.signals:
                ml_fraud_signals.append(signal.to_dict())
                suspicious_flags.append(f"[ML] {signal.description} (confidence: {signal.confidence:.1%})")
            
        except Exception as e:
            logger.warning(f"[Fraud Auditor] ML fraud detection error: {e}")
            fraud_result = None
        
        # Compile anomaly detection
        anomaly_detection = {
            "total_flags_raised": len(suspicious_flags),
            "flag_severity_distribution": {
                "high": sum(1 for f in suspicious_flags if any(x in f for x in ["significantly", "exceeds", "void"])),
                "medium": sum(1 for f in suspicious_flags if any(x in f for x in ["differ", "unusual", "differ"])),
                "low": sum(1 for f in suspicious_flags if any(x in f for x in ["pattern", "frequency"])),
            },
            "ml_signals_detected": len(ml_fraud_signals),
        }
        
        output = {
            "suspicious_flags": suspicious_flags,
            "web_search_results": web_search_results,
            "market_price_analysis": market_price_analysis,
            "anomaly_detection": anomaly_detection,
            "ml_fraud_signals": ml_fraud_signals,
            "fraud_detection_result": fraud_result.to_dict() if fraud_result else None,
            "risk_assessment": {
                "invoice_anomaly": min(len(suspicious_flags) * 0.15, 1.0),
                "pricing_verification_status": "COMPLETED" if web_search_results else "PENDING",
                "ml_fraud_probability": fraud_result.fraud_probability if fraud_result else 0.0,
                "ml_risk_score": fraud_result.risk_score if fraud_result else 0,
            },
        }
        
        logger.info(f"[Fraud Auditor] Raised {len(suspicious_flags)} suspicious flags, {len(ml_fraud_signals)} ML signals")
        return output
        
    except Exception as e:
        logger.error(f"[Fraud Auditor] Error: {e}", exc_info=True)
        return {
            "suspicious_flags": [],
            "web_search_results": [],
            "market_price_analysis": {},
            "anomaly_detection": {},
            "ml_fraud_signals": [],
            "fraud_detection_result": None,
            "risk_assessment": {},
        }


# ========== NODE 4: JUDGE/DECISION NODE ==========

def judge_node(state: ClaimAuditState) -> dict[str, Any]:
    """
    Node 4: The Judge Node (The Final Arbitrator)
    
    Role: Issue final verdict based on compiled evidence, including ML fraud detection.
    
    Process:
    1. Reads complete trace history from state
    2. Incorporates ML fraud detection results and risk scores
    3. Applies decision logic using LLM with structured output
    4. Calculates final payout amount
    5. Generates justification matrix
    6. Returns APPROVED/DENIED/ESCALATED decision
    
    Output fields:
    - final_verdict
    - payout_amount
    - risk_score
    - fraud_probability
    - justification_matrix
    - decision_rationale
    """
    logger.info(f"[Judge] Issuing verdict for claim {state.get('claim_id')}")
    
    try:
        # Compile evidence for final decision
        claim = state.get("structured_claim", {})
        invoice = state.get("structured_invoice", {})
        extracted_clauses = state.get("extracted_clauses", {})
        suspicious_flags = state.get("suspicious_flags", [])
        database_alerts = state.get("database_alerts", [])
        ml_fraud_result = state.get("fraud_detection_result")
        
        claimed_amount = float(claim.get("claimed_amount") or 0)
        policy_limit = float(state.get("policy_coverage_limits") or 0)
        deductible = float(state.get("applicable_deductibles") or 0)
        
        # Get ML fraud scores if available
        ml_fraud_prob = 0.0
        ml_risk_score = 0
        ml_signals_summary = ""
        
        if ml_fraud_result:
            ml_fraud_prob = ml_fraud_result.get("fraud_probability", 0.0)
            ml_risk_score = ml_fraud_result.get("risk_score", 0)
            signals = ml_fraud_result.get("signals", [])
            ml_signals_summary = f"ML detected {len(signals)} fraud signals with risk score {ml_risk_score}/100"
        
        # Build comprehensive decision prompt with ML signals
        decision_prompt = f"""You are the final judge in an insurance claim review process.

CLAIM DETAILS:
Claimed Amount: ${claimed_amount}
Incident Date: {claim.get('incident_date', 'N/A')}
Incident Type: {claim.get('incident_type', 'N/A')}

POLICY DETAILS:
Coverage Limit: ${policy_limit}
Deductible: ${deductible}
Is Covered: {extracted_clauses.get('is_covered', 'UNKNOWN')}

EXTRACTED CLAUSES:
{json.dumps(extracted_clauses, indent=2)}

SUSPICIOUS FLAGS ({len(suspicious_flags)} raised):
{chr(10).join('- ' + f for f in suspicious_flags[:10])}

DATABASE ALERTS ({len(database_alerts)} raised):
{chr(10).join('- ' + f for f in database_alerts[:5])}

ML FRAUD DETECTION ANALYSIS:
{ml_signals_summary}
ML Fraud Probability: {ml_fraud_prob:.1%}
ML Risk Score: {ml_risk_score}/100

Make a FINAL DECISION. Return ONLY valid JSON with:
{{
    "verdict": "APPROVED" | "DENIED" | "ESCALATED",
    "payout_amount": float (0 to claim amount),
    "risk_score": float (0-100),
    "fraud_probability": int (0-100),
    "justification": "Brief 2-3 sentence explanation",
    "decision_factors": {{
        "coverage_match": float (0-1),
        "invoice_validity": float (0-1),
        "customer_history": float (0-1),
        "timing_suspicion": float (0-1),
        "documentation_quality": float (0-1),
        "ml_fraud_assessment": float (0-1)
    }}
}}"""
        
        decision_data = gemini_client.generate_json(decision_prompt, temperature=0.2)
        
        output = {
            "final_verdict": decision_data.get("verdict", "ESCALATED"),
            "payout_amount": decision_data.get("payout_amount", 0),
            "risk_score": decision_data.get("risk_score", 50),
            "fraud_probability": decision_data.get("fraud_probability", 0),
            "justification_matrix": decision_data.get("decision_factors", {}),
            "decision_rationale": decision_data.get("justification", ""),
            "processing_timestamp": state.get("created_at", ""),
            "ml_fraud_assessment": {
                "fraud_probability": ml_fraud_prob,
                "risk_score": ml_risk_score,
                "included_in_decision": bool(ml_fraud_result),
            }
        }
        
        logger.info(f"[Judge] Verdict: {output['final_verdict']} - Payout: ${output['payout_amount']} - ML Risk: {ml_risk_score}/100")
        return output
        
    except Exception as e:
        logger.error(f"[Judge] Error: {e}", exc_info=True)
        return {
            "final_verdict": "ESCALATED",
            "payout_amount": 0,
            "risk_score": 50,
            "fraud_probability": 0,
            "justification_matrix": {},
            "decision_rationale": f"Error during judgment: {str(e)}",
            "processing_timestamp": state.get("created_at", ""),
            "ml_fraud_assessment": {"fraud_probability": 0.0, "risk_score": 0, "included_in_decision": False}
        }
