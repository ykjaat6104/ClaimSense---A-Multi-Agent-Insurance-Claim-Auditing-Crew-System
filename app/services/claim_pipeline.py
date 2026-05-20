from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import crud
from app.db.models import Claim
from app.services import extraction, rag_service, report_pdf, risk_scoring
from app.services.document_parser import extract_text_auto
from app.agents.graph import run_agent_graph


def _log(db: Session, claim: Claim, msg: str) -> None:
    crud.append_log(db, claim, msg)


def process_claim(db: Session, claim_id: uuid.UUID) -> Claim:
    settings = get_settings()
    claim = crud.get_claim(db, claim_id)
    if claim is None:
        raise ValueError("Claim not found")

    claim.status = "processing"
    claim.error_message = None
    db.add(claim)
    db.commit()
    db.refresh(claim)

    try:
        _log(db, claim, "Extracting document data…")
        claim_p = Path(claim.claim_file_path) if claim.claim_file_path else None
        invoice_p = Path(claim.invoice_file_path) if claim.invoice_file_path else None
        policy_p = Path(claim.policy_file_path) if claim.policy_file_path else None
        for label, p in ("claim", claim_p), ("invoice", invoice_p), ("policy", policy_p):
            if p is None or not p.exists():
                raise FileNotFoundError(f"Missing or invalid file for {label}")

        claim_text_raw = extract_text_auto(claim_p)  # type: ignore[arg-type]
        invoice_text = extract_text_auto(invoice_p)  # type: ignore[arg-type]
        policy_text = extract_text_auto(policy_p)  # type: ignore[arg-type]
        evidence_chunks: list[str] = []
        for ep in claim.evidence_file_paths or []:
            pth = Path(ep)
            if pth.exists():
                evidence_chunks.append(
                    f"--- Evidence: {pth.name} ---\n{extract_text_auto(pth)}"
                )
        evidence_blob = "\n\n".join(evidence_chunks) if evidence_chunks else ""
        claim_text = claim_text_raw + (f"\n\n{evidence_blob}" if evidence_blob else "")
        claim.raw_texts = {
            "claim": claim_text_raw,
            "invoice": invoice_text,
            "policy": policy_text,
            "evidence": evidence_blob or None,
        }
        if claim.past_claims_csv_path and Path(claim.past_claims_csv_path).exists():
            claim.past_claims_meta = crud.summarize_past_claims_csv(Path(claim.past_claims_csv_path))
            db.add(claim)
            db.commit()
            n = (claim.past_claims_meta or {}).get("row_count", 0)
            _log(db, claim, f"Past claims CSV indexed ({n} rows) for reference.")
        db.add(claim)
        db.commit()
        _log(db, claim, "Document text extraction complete.")

        _log(db, claim, "Structuring claim, invoice, and policy data…")
        claim.structured_claim = extraction.extract_claim_json(claim_text)
        claim.structured_invoice = extraction.extract_invoice_json(invoice_text)
        claim.structured_policy = extraction.extract_policy_json(policy_text)
        db.add(claim)
        db.commit()

        _log(db, claim, "Matching policy clauses…")
        index = rag_service.ingest_policy(claim.id, policy_text)
        q = rag_service.build_rag_query(claim.structured_claim or {}, claim.structured_invoice or {})
        chunks = rag_service.retrieve_relevant(index, q)
        claim.rag_chunks = chunks
        db.add(claim)
        db.commit()
        _log(db, claim, f"Retrieved {len(chunks)} relevant policy excerpts.")

        _log(db, claim, "Running risk analysis…")
        agent_out = run_agent_graph(
            claim_id=str(claim.id),
            structured_claim=claim.structured_claim or {},
            structured_invoice=claim.structured_invoice or {},
            structured_policy=claim.structured_policy or {},
            rag_chunks=chunks,
        )
        claim.approve_argument = agent_out.get("approve_argument")
        claim.reject_argument = agent_out.get("reject_argument")
        med = agent_out.get("mediator_output") or {}
        claim.mediator_output = med

        risk = risk_scoring.compute_risk_score(med)
        fraud = risk_scoring.fraud_probability_from_mediator(med, risk)
        claim.risk_score = risk
        claim.fraud_probability = fraud
        decision = str(med.get("decision") or "REVIEW").upper()
        if decision not in {"APPROVE", "REJECT", "REVIEW"}:
            decision = "REVIEW"
        claim.decision = decision
        db.add(claim)
        db.commit()

        _log(db, claim, "Generating report PDF…")
        reports_dir = settings.reports_dir
        pdf_path = reports_dir / f"{claim.id}.pdf"
        claim.report_pdf_path = report_pdf.build_pdf_report(claim, pdf_path)
        claim.status = "completed"
        db.add(claim)
        db.commit()
        _log(db, claim, "Analysis complete — report ready.")
        db.refresh(claim)
        return claim

    except Exception as e:  # noqa: BLE001 — surface pipeline errors to API
        claim.status = "failed"
        claim.error_message = str(e)
        db.add(claim)
        db.commit()
        _log(db, claim, f"FAILED: {e}")
        db.refresh(claim)
        return claim
