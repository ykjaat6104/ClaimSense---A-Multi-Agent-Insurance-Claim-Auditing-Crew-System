from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.db.models import Claim


def build_pdf_report(claim: Claim, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(dest), pagesize=letter)
    styles = getSampleStyleSheet()
    story: list = []
    story.append(Paragraph("<b>ClaimSense — Claim Decision Support Report</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"<b>Claim ID:</b> {claim.id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Status:</b> {claim.status}", styles["Normal"]))
    story.append(Paragraph(f"<b>Decision:</b> {claim.decision or 'N/A'}", styles["Normal"]))
    story.append(Paragraph(f"<b>Risk score:</b> {claim.risk_score}", styles["Normal"]))
    story.append(Paragraph(f"<b>Fraud probability:</b> {claim.fraud_probability}", styles["Normal"]))
    story.append(Spacer(1, 12))

    def _para(title: str, body: str) -> None:
        story.append(Paragraph(f"<b>{title}</b>", styles["Heading3"]))
        safe = (body or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(safe.replace("\n", "<br/>"), styles["BodyText"]))
        story.append(Spacer(1, 8))

    _para("Approve agent", claim.approve_argument or "")
    _para("Reject / risk agent", claim.reject_argument or "")
    _para("Mediator JSON", json.dumps(claim.mediator_output or {}, indent=2))
    if claim.rag_chunks:
        _para("Retrieved policy clauses (RAG)", "\n\n".join(claim.rag_chunks[:12]))

    doc.build(story)
    return str(dest.resolve())
