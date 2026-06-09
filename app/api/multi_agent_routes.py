"""
Enhanced API routes for the multi-agent claim auditing system.
Integrates LangGraph orchestrator with FastAPI endpoints and Celery task queue.
"""

import uuid
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.api.deps import get_current_username, get_db
from app.db import crud
from app.db.models import claim_to_public_dict
from app.schemas.api import ProcessResponse
from app.services import gemini_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/audit", tags=["multi-agent-audit"])


# ========== SCHEMAS ==========

class MultiAgentAuditRequest:
    """Request model for triggering multi-agent audit."""
    pass


class MultiAgentAuditResponse:
    """Response model for multi-agent audit initiation."""
    claim_id: str
    status: str
    task_id: str | None = None
    message: str


# ========== HELPER FUNCTIONS ==========

def _trigger_multi_agent_audit_background(
    claim_id: str,
    db: Session,
) -> None:
    """
    Background task function to execute the multi-agent audit workflow.
    Can be called via BackgroundTasks or Celery.
    """
    try:
        from app.agents.orchestrator import run_claim_audit_workflow
        
        logger.info(f"[API] Starting multi-agent audit for claim {claim_id}")
        
        # Fetch claim and structured data from database
        claim = crud.get_claim(db, claim_id)
        if not claim:
            logger.error(f"[API] Claim {claim_id} not found")
            return
        
        # Extract required data
        user_id = str(claim.id)  # Would be mapped from actual user
        policy_id = claim.structured_policy.get("policy_id", "") if claim.structured_policy else ""
        
        # Run the audit workflow
        audit_result = run_claim_audit_workflow(
            claim_id=claim_id,
            user_id=user_id,
            policy_id=policy_id,
            structured_claim=claim.structured_claim or {},
            structured_invoice=claim.structured_invoice or {},
            structured_policy=claim.structured_policy or {},
            raw_claim_text=claim.raw_texts.get("claim_text", "") if claim.raw_texts else "",
            raw_invoice_text=claim.raw_texts.get("invoice_text", "") if claim.raw_texts else "",
            raw_policy_text=claim.raw_texts.get("policy_text", "") if claim.raw_texts else "",
            past_claims_meta=claim.past_claims_meta,
            evidence_files=claim.evidence_file_paths,
        )
        
        # Map results back to claim model
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
        
        claim.status = "completed"
        claim.processing_logs = claim.processing_logs or []
        claim.processing_logs.append("[Multi-Agent Audit] Workflow completed successfully")
        
        db.add(claim)
        db.commit()
        
        logger.info(f"[API] Multi-agent audit completed for claim {claim_id}. Verdict: {claim.decision}")
        
    except Exception as e:
        logger.error(f"[API] Error in multi-agent audit: {e}", exc_info=True)
        try:
            claim = crud.get_claim(db, claim_id)
            if claim:
                claim.status = "failed"
                claim.error_message = f"Multi-agent audit failed: {str(e)}"
                claim.processing_logs = claim.processing_logs or []
                claim.processing_logs.append(f"[Error] {str(e)}")
                db.add(claim)
                db.commit()
        except Exception as db_error:
            logger.error(f"[API] Failed to update claim status: {db_error}")


def _trigger_celery_audit(claim_id: str, db: Session) -> str:
    """
    Trigger the multi-agent audit via Celery task queue.
    Returns the task ID for tracking.
    """
    try:
        from app.services.celery_tasks import process_claim_audit_task
        
        claim = crud.get_claim(db, claim_id)
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Queue the audit task
        task = process_claim_audit_task.delay(
            claim_id=str(claim_id),
            user_id=str(claim.id),
            policy_id=claim.structured_policy.get("policy_id", "") if claim.structured_policy else "",
            structured_claim=claim.structured_claim or {},
            structured_invoice=claim.structured_invoice or {},
            structured_policy=claim.structured_policy or {},
            raw_claim_text=claim.raw_texts.get("claim_text", "") if claim.raw_texts else "",
            raw_invoice_text=claim.raw_texts.get("invoice_text", "") if claim.raw_texts else "",
            raw_policy_text=claim.raw_texts.get("policy_text", "") if claim.raw_texts else "",
            past_claims_meta=claim.past_claims_meta,
            evidence_files=claim.evidence_file_paths,
        )
        
        logger.info(f"[API] Queued multi-agent audit for claim {claim_id}. Task ID: {task.id}")
        return task.id
        
    except Exception:
        logger.warning("[API] Celery/Redis not available, using sync fallback")
        return None


# ========== ENDPOINTS ==========

@router.post("/trigger", response_model=dict)
def trigger_multi_agent_audit(
    claim_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
    use_celery: bool = True,
) -> dict[str, Any]:
    """
    Trigger the multi-agent claim auditing workflow for a specific claim.
    
    This endpoint:
    1. Validates the claim exists and is ready for processing
    2. Triggers the multi-agent audit asynchronously (via Celery or BackgroundTasks)
    3. Returns immediately with task tracking information
    
    Args:
        claim_id: UUID of the claim to audit
        use_celery: Whether to use Celery task queue (requires Redis)
        background_tasks: FastAPI background task manager
        db: Database session
        _username: Authenticated username
    
    Returns:
        {
            "status": "queued" | "processing" | "error",
            "claim_id": str,
            "task_id": str (if using Celery),
            "message": str,
        }
    """
    
    try:
        # Validate claim exists
        claim = crud.get_claim(db, uuid.UUID(claim_id))
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        # Check if already processing
        if claim.status == "processing":
            return {
                "status": "processing",
                "claim_id": claim_id,
                "message": "Claim audit already in progress"
            }
        
        # Check if already completed
        if claim.status == "completed":
            return {
                "status": "completed",
                "claim_id": claim_id,
                "message": "Claim has already been audited. Use /get-result endpoint to retrieve results."
            }
        
        # Mark as processing
        claim.status = "processing"
        claim.processing_logs = claim.processing_logs or []
        claim.processing_logs.append("[Multi-Agent Audit] Workflow triggered")
        db.add(claim)
        db.commit()
        
        # Trigger audit workflow
        task_id = None
        
        if use_celery:
            task_id = _trigger_celery_audit(claim_id, db)
        
        if not task_id and background_tasks:
            # Fallback to background task
            background_tasks.add_task(_trigger_multi_agent_audit_background, claim_id, db)
        
        return {
            "status": "queued",
            "claim_id": claim_id,
            "task_id": task_id,
            "message": "Multi-agent audit workflow initiated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error triggering multi-agent audit: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error triggering audit: {str(e)}")


@router.get("/status/{claim_id}", response_model=dict)
def get_audit_status(
    claim_id: str,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> dict[str, Any]:
    """
    Get the current status of a multi-agent audit workflow.
    
    Returns:
        {
            "claim_id": str,
            "status": "pending" | "queued" | "processing" | "completed" | "failed",
            "verdict": str (if completed),
            "risk_score": int (if completed),
            "fraud_probability": int (if completed),
            "processing_logs": list[str],
            "error_message": str (if failed),
        }
    """
    
    try:
        claim = crud.get_claim(db, uuid.UUID(claim_id))
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        response = {
            "claim_id": claim_id,
            "status": claim.status,
            "processing_logs": claim.processing_logs or [],
        }
        
        if claim.status == "completed":
            response.update({
                "verdict": claim.decision,
                "risk_score": claim.risk_score,
                "fraud_probability": claim.fraud_probability,
                "mediator_output": claim.mediator_output,
            })
        
        if claim.status == "failed":
            response["error_message"] = claim.error_message
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting audit status: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving status: {str(e)}")


@router.get("/result/{claim_id}")
def get_audit_result(
    claim_id: str,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> dict[str, Any]:
    """
    Get the full result of a completed multi-agent audit.
    
    Returns the complete claim details including all agent outputs.
    """
    
    try:
        claim = crud.get_claim(db, uuid.UUID(claim_id))
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        
        if claim.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Claim audit is not completed. Current status: {claim.status}"
            )
        
        return claim_to_public_dict(claim)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error getting audit result: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving result: {str(e)}")


@router.post("/compare/{claim_id}/with/{reference_claim_id}")
def compare_audits(
    claim_id: str,
    reference_claim_id: str,
    db: Session = Depends(get_db),
    _username: str = Depends(get_current_username),
) -> dict[str, Any]:
    """
    Compare audit results between two claims.
    Useful for detecting patterns or similar fraud indicators.
    """
    
    try:
        claim1 = crud.get_claim(db, uuid.UUID(claim_id))
        claim2 = crud.get_claim(db, uuid.UUID(reference_claim_id))
        
        if not claim1 or not claim2:
            raise HTTPException(status_code=404, detail="One or both claims not found")
        
        return {
            "claim1": claim_to_public_dict(claim1),
            "claim2": claim_to_public_dict(claim2),
            "comparison": {
                "decision_match": claim1.decision == claim2.decision,
                "risk_score_diff": abs((claim1.risk_score or 0) - (claim2.risk_score or 0)),
                "fraud_probability_diff": abs((claim1.fraud_probability or 0) - (claim2.fraud_probability or 0)),
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error comparing audits: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing audits: {str(e)}")
