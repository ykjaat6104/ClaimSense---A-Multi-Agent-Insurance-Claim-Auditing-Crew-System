from __future__ import annotations

import json
from typing import Any

from app.services import gemini_client


def _truncate(s: str, limit: int = 28000) -> str:
    s = s.strip()
    return s if len(s) <= limit else s[:limit] + "\n...[truncated]"


def extract_claim_json(claim_text: str) -> dict[str, Any]:
    prompt = f"""You are an insurance claim analyst. Extract structured fields from the claim document text.
Return ONLY valid JSON with keys:
claim_id (string or null if unknown),
policy_number (string or null),
incident_date (ISO date string or null),
claimed_amount (number or null),
damage_type (string),
incident_description (string),
coverage_requested (string),
documents_mentioned (array of strings),
notes (string).

Document text:
{_truncate(claim_text)}
"""
    return gemini_client.generate_json(prompt)


def extract_invoice_json(invoice_text: str) -> dict[str, Any]:
    prompt = f"""Extract structured invoice/repair bill fields. Return ONLY valid JSON with keys:
vendor_name (string or null),
invoice_date (ISO date string or null),
total_amount (number or null),
currency (string),
line_items_summary (string),
flags_suspicious (boolean),
notes (string).

Invoice text:
{_truncate(invoice_text)}
"""
    return gemini_client.generate_json(prompt)


def extract_policy_json(policy_text: str) -> dict[str, Any]:
    prompt = f"""Extract high-level policy metadata. Return ONLY valid JSON with keys:
policy_number (string or null),
effective_date (ISO date string or null),
expiry_date (ISO date string or null),
named_insured (string or null),
coverage_types (array of strings),
deductible_amount (number or null),
max_payout (number or null),
notes (string).

Policy text (may be partial):
{_truncate(policy_text)}
"""
    return gemini_client.generate_json(prompt)
