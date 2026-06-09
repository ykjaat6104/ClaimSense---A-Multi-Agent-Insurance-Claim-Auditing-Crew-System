import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)

    claim_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    past_claims_csv_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_file_paths: Mapped[list | None] = mapped_column(JSON, nullable=True)
    other_file_paths: Mapped[list | None] = mapped_column(JSON, nullable=True)

    raw_texts: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_claim: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_invoice: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    past_claims_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    rag_chunks: Mapped[list | None] = mapped_column(JSON, nullable=True)
    rag_method_used: Mapped[str | None] = mapped_column(String(32), nullable=True)
    clause_relationships: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approve_argument: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_argument: Mapped[str | None] = mapped_column(Text, nullable=True)
    mediator_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fraud_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)

    adjuster_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    adjuster_action_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processing_logs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )


def derive_flags_and_insights(c: Claim) -> tuple[list[str], list[str]]:
    """Heuristic UX bullets from structured data + mediator (decision support only)."""
    flags: list[str] = []
    insights: list[str] = []
    med = c.mediator_output or {}
    sc = c.structured_claim or {}
    si = c.structured_invoice or {}
    sp = c.structured_policy or {}

    try:
        claimed = float(sc.get("claimed_amount") or 0)
        inv_total = float(si.get("total_amount") or 0)
        if claimed and inv_total and abs(claimed - inv_total) / max(claimed, inv_total) > 0.15:
            flags.append("Claimed amount and invoice total differ materially")
    except (TypeError, ValueError):
        pass

    if med.get("invoice_anomaly", 0) and float(med.get("invoice_anomaly", 0)) >= 0.45:
        flags.append("Repair / invoice pattern flagged as higher risk")
    if med.get("timing_suspicion", 0) and float(med.get("timing_suspicion", 0)) >= 0.45:
        flags.append("Incident timing is close to policy boundaries or renewal window")
    if med.get("missing_docs", 0) and float(med.get("missing_docs", 0)) >= 0.45:
        flags.append("Documentation may be incomplete vs stated requirements")
    if med.get("coverage_violation", 0) and float(med.get("coverage_violation", 0)) >= 0.45:
        flags.append("Possible coverage mismatch vs retrieved policy language")

    rationale = str(med.get("rationale") or "").strip()
    if rationale:
        insights.append(rationale)

    if si.get("flags_suspicious"):
        flags.append("Invoice metadata marked suspicious by extraction")

    meta = c.past_claims_meta or {}
    if meta.get("row_count"):
        insights.append(f"Past claims CSV on file ({meta.get('row_count')} rows) — use for duplicate / frequency checks.")

    return flags, insights


def claim_to_public_dict(c: Claim) -> dict[str, Any]:
    flags, insights = derive_flags_and_insights(c)
    return {
        "id": str(c.id),
        "status": c.status,
        "decision": c.decision,
        "risk_score": c.risk_score,
        "fraud_probability": c.fraud_probability,
        "structured_claim": c.structured_claim,
        "structured_invoice": c.structured_invoice,
        "structured_policy": c.structured_policy,
        "past_claims_meta": c.past_claims_meta,
        "evidence_file_paths": c.evidence_file_paths,
        "other_file_paths": c.other_file_paths,
        "rag_chunks": c.rag_chunks,
        "rag_method_used": c.rag_method_used,
        "clause_relationships": c.clause_relationships,
        "approve_argument": c.approve_argument,
        "reject_argument": c.reject_argument,
        "mediator_output": c.mediator_output,
        "flags": flags,
        "insights": insights,
        "processing_logs": c.processing_logs or [],
        "error_message": c.error_message,
        "report_pdf_path": c.report_pdf_path,
        "adjuster_action": c.adjuster_action,
        "adjuster_action_at": c.adjuster_action_at.isoformat() if c.adjuster_action_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def claim_summary_dict(c: Claim) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "status": c.status,
        "decision": c.decision,
        "risk_score": c.risk_score,
        "fraud_probability": c.fraud_probability,
        "adjuster_action": c.adjuster_action,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
