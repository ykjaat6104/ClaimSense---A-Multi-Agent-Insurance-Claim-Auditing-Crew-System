"""
Celery task definitions for asynchronous claim audit processing.
Enables long-running multi-agent workflows without blocking the API.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any

from app.services.celery_config import app
from app.agents.orchestrator import run_claim_audit_workflow
from app.db import crud, session
from app.db.models import Claim

logger = logging.getLogger(__name__)


@app.task(bind=True, name="process_claim_audit")
def process_claim_audit_task(
    self,
    claim_id: str,
    user_id: str,
    policy_id: str,
    structured_claim: dict[str, Any],
    structured_invoice: dict[str, Any],
    structured_policy: dict[str, Any],
    raw_claim_text: str = "",
    raw_invoice_text: str = "",
    raw_policy_text: str = "",
    past_claims_meta: dict[str, Any] | None = None,
    evidence_files: list[str] | None = None,
) -> dict[str, Any]:
    """
    Asynchronous task to execute the complete claim audit workflow.
    
    This runs in a Celery worker process, allowing the FastAPI endpoint to return
    immediately while the multi-agent system processes the claim in the background.
    
    Args:
        self: Celery task instance (for retry/retry_count)
        claim_id: Unique claim identifier
        user_id: Customer user ID
        policy_id: Insurance policy ID
        structured_claim: Parsed claim form data
        structured_invoice: Parsed invoice/repair estimate data
        structured_policy: Parsed policy metadata
        raw_claim_text: Full raw text of claim document
        raw_invoice_text: Full raw text of invoice document
        raw_policy_text: Full raw text of policy document
        past_claims_meta: Metadata about past claims
        evidence_files: List of supporting evidence file paths
    
    Returns:
        Dictionary with task status and results
    """
    
    db = session.SessionLocal()
    
    try:
        logger.info(f"[Celery Task] Starting claim audit for {claim_id} (attempt {self.request.retries})")
        
        # Update claim status to processing
        claim: Claim | None = crud.get_claim(db, claim_id)
        if not claim:
            logger.error(f"[Celery Task] Claim {claim_id} not found")
            return {"status": "error", "message": "Claim not found"}
        
        claim.status = "processing"
        claim.processing_logs = claim.processing_logs or []
        claim.processing_logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Starting audit workflow")
        db.add(claim)
        db.commit()
        
        # Execute the multi-agent workflow
        logger.info(f"[Celery Task] Running audit workflow...")
        
        audit_result = run_claim_audit_workflow(
            claim_id=claim_id,
            user_id=user_id,
            policy_id=policy_id,
            tenant_id="default",
            structured_claim=structured_claim,
            structured_invoice=structured_invoice,
            structured_policy=structured_policy,
            raw_claim_text=raw_claim_text,
            raw_invoice_text=raw_invoice_text,
            raw_policy_text=raw_policy_text,
            past_claims_meta=past_claims_meta,
            evidence_files=evidence_files,
        )
        
        # Map audit results back to claim model
        logger.info(f"[Celery Task] Audit complete. Verdict: {audit_result.get('final_verdict')}")
        
        claim.decision = audit_result.get("final_verdict")
        claim.risk_score = int(audit_result.get("risk_score", 0))
        claim.fraud_probability = int(audit_result.get("fraud_probability", 0))
        claim.mediator_output = {
            "verdict": audit_result.get("final_verdict"),
            "payout_amount": audit_result.get("payout_amount"),
            "risk_score": audit_result.get("risk_score"),
            "fraud_probability": audit_result.get("fraud_probability"),
            "rationale": audit_result.get("decision_rationale"),
            "justification_matrix": audit_result.get("justification_matrix"),
        }
        
        # Store additional audit data
        claim.extracted_clauses_data = audit_result.get("extracted_clauses", {})
        claim.suspicious_flags = audit_result.get("suspicious_flags", [])
        claim.database_alerts = audit_result.get("database_alerts", [])
        claim.market_price_analysis = audit_result.get("market_price_analysis", {})
        
        claim.status = "completed"
        claim.processing_logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Audit workflow completed")
        
        db.add(claim)
        db.commit()
        
        logger.info(f"[Celery Task] Claim {claim_id} audit completed successfully")
        
        return {
            "status": "success",
            "claim_id": claim_id,
            "verdict": audit_result.get("final_verdict"),
            "payout_amount": audit_result.get("payout_amount"),
        }
        
    except Exception as e:
        logger.error(f"[Celery Task] Error processing claim {claim_id}: {e}", exc_info=True)
        
        try:
            claim: Claim | None = crud.get_claim(db, claim_id)
            if claim:
                claim.status = "failed"
                claim.error_message = str(e)
                claim.processing_logs = claim.processing_logs or []
                claim.processing_logs.append(
                    f"[{datetime.now(timezone.utc).isoformat()}] ERROR: {str(e)}"
                )
                db.add(claim)
                db.commit()
        except Exception as db_error:
            logger.error(f"[Celery Task] Failed to update claim status: {db_error}")
        
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
    
    finally:
        db.close()


@app.task(name="generate_claim_report")
def generate_claim_report_task(claim_id: str) -> dict[str, Any]:
    """
    Generate a PDF report for a processed claim.
    
    This is a separate task to allow report generation to happen independently.
    """
    db = session.SessionLocal()
    
    try:
        logger.info(f"[Report Task] Generating report for claim {claim_id}")
        
        claim: Claim | None = crud.get_claim(db, claim_id)
        if not claim:
            return {"status": "error", "message": "Claim not found"}
        
        # TODO: Implement actual report generation
        # from app.services.report_pdf import generate_claim_report
        # report_path = generate_claim_report(claim)
        
        logger.info(f"[Report Task] Report generated for claim {claim_id}")
        
        return {
            "status": "success",
            "claim_id": claim_id,
            "report_path": claim.report_pdf_path,
        }
        
    except Exception as e:
        logger.error(f"[Report Task] Error generating report for claim {claim_id}: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
    
    finally:
        db.close()


@app.task(name="bulk_claim_audit")
def bulk_claim_audit_task(claim_ids: list[str]) -> dict[str, Any]:
    """
    Process multiple claims in bulk for batch operations.
    """
    logger.info(f"[Bulk Task] Starting audit for {len(claim_ids)} claims")
    
    results = {
        "total": len(claim_ids),
        "completed": 0,
        "failed": 0,
        "claims": []
    }
    
    for claim_id in claim_ids:
        try:
            # Trigger individual audit task for each claim
            task = process_claim_audit_task.delay(
                claim_id=claim_id,
                user_id="",  # Would need to fetch from DB
                policy_id="",  # Would need to fetch from DB
                structured_claim={},
                structured_invoice={},
                structured_policy={},
            )
            results["claims"].append({
                "claim_id": claim_id,
                "task_id": task.id,
                "status": "queued"
            })
            results["completed"] += 1
        except Exception as e:
            logger.error(f"[Bulk Task] Failed to queue audit for {claim_id}: {e}")
            results["failed"] += 1
    
    logger.info(f"[Bulk Task] Queued {results['completed']} claims for audit")
    return results
