import hashlib
import json
import math
import re
from collections import Counter
from typing import Any

import google.generativeai as genai

from app.config import get_settings


_VECTOR_SIZE = 128


def configure_genai() -> None:
    settings = get_settings()
    if not settings.gemini_api_key:
        return
    genai.configure(api_key=settings.gemini_api_key)


def _section_after(prompt: str, marker: str) -> str:
    if marker not in prompt:
        return ""
    return prompt.split(marker, 1)[1].strip()


def _first_match(pattern: str, text: str, *, flags: int = re.IGNORECASE) -> str | None:
    m = re.search(pattern, text, flags)
    if not m:
        return None
    return m.group(1).strip()


def _first_amount(text: str) -> float | None:
    amounts = re.findall(r"(?:\$|USD\s*)?([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE)
    if not amounts:
        return None
    values = []
    for raw in amounts:
        try:
            values.append(float(raw.replace(",", "")))
        except ValueError:
            continue
    if not values:
        return None
    return max(values)


def _first_date(text: str) -> str | None:
    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)
    m = re.search(r"\b(\d{1,2}/\d{1,2}/\d{4})\b", text)
    if m:
        return m.group(1)
    return None


def _normalize_claim_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _keywords(text: str, terms: list[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def _fallback_claim_json(claim_text: str) -> dict[str, Any]:
    text = _normalize_claim_text(claim_text)
    incident_description = text[:280] if text else "No claim narrative detected."
    damage_terms = [
        "water damage",
        "fire damage",
        "theft",
        "collision",
        "hail",
        "storm",
        "wind",
        "roof",
        "glass",
        "burst pipe",
        "flood",
        "mold",
        "vandalism",
        "accident",
        "liability",
        "injury",
    ]
    detected_damage = next((term for term in damage_terms if term in text.lower()), "unknown")
    documents = _keywords(text, ["invoice", "receipt", "estimate", "photos", "photo", "policy", "police report", "report", "repair", "statement"])
    return {
        "claim_id": _first_match(r"claim\s*(?:id|number|no\.?|#)[:\s]*([A-Za-z0-9._/-]+)", text),
        "policy_number": _first_match(r"policy\s*(?:number|no\.?|#)[:\s]*([A-Za-z0-9._/-]+)", text),
        "incident_date": _first_date(text),
        "claimed_amount": _first_amount(text),
        "damage_type": detected_damage,
        "incident_description": incident_description,
        "coverage_requested": _first_match(r"coverage\s*(?:requested|type)?[:\s]*([A-Za-z0-9 ,/&-]+)", text) or "unspecified",
        "documents_mentioned": sorted(set(documents)),
        "notes": "Fallback extraction used because Gemini was unavailable or returned an invalid API response.",
    }


def _fallback_invoice_json(invoice_text: str) -> dict[str, Any]:
    text = _normalize_claim_text(invoice_text)
    suspicious_terms = ["suspicious", "estimate", "rounded", "duplicate", "fake", "missing", "no receipt", "handwritten", "cash only"]
    flags_suspicious = any(term in text.lower() for term in suspicious_terms)
    currency = "USD" if "$" in text or "usd" in text.lower() else "unknown"
    vendor = _first_match(r"(?:vendor|supplier|provider|shop|garage|repair(?:\s+shop)?)[:\s]*([A-Za-z0-9 &.'/-]{2,80})", text)
    if not vendor:
        first_line = next((line.strip() for line in invoice_text.splitlines() if line.strip()), "")
        vendor = first_line[:80] if first_line else None
    return {
        "vendor_name": vendor,
        "invoice_date": _first_date(text),
        "total_amount": _first_amount(text),
        "currency": currency,
        "line_items_summary": "; ".join(line.strip() for line in invoice_text.splitlines() if line.strip())[:400] or "No line items detected.",
        "flags_suspicious": flags_suspicious,
        "notes": "Fallback invoice extraction used because Gemini was unavailable or returned an invalid API response.",
    }


def _fallback_policy_json(policy_text: str) -> dict[str, Any]:
    text = _normalize_claim_text(policy_text)
    coverage_terms = [
        "property",
        "auto",
        "liability",
        "collision",
        "comprehensive",
        "theft",
        "fire",
        "water",
        "flood",
        "wind",
        "hail",
        "medical",
        "injury",
        "damage",
    ]
    coverage_types = sorted(set(_keywords(text, coverage_terms)))
    return {
        "policy_number": _first_match(r"policy\s*(?:number|no\.?|#)[:\s]*([A-Za-z0-9._/-]+)", text),
        "effective_date": _first_date(text),
        "expiry_date": _first_match(r"(?:expiry|expiration|expires?)[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2}|[0-9]{1,2}/[0-9]{1,2}/[0-9]{4})", text),
        "named_insured": _first_match(r"(?:named insured|insured|policyholder)[:\s]*([A-Za-z0-9 ,.'&/-]{2,80})", text),
        "coverage_types": coverage_types,
        "deductible_amount": _first_amount(re.search(r"(?:deductible|excess)[:\s\$]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE).group(1) if re.search(r"(?:deductible|excess)[:\s\$]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE) else text),
        "max_payout": _first_amount(re.search(r"(?:max(?:imum)? payout|limit|coverage limit|policy limit)[:\s\$]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE).group(1) if re.search(r"(?:max(?:imum)? payout|limit|coverage limit|policy limit)[:\s\$]*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.IGNORECASE) else text),
        "notes": "Fallback policy extraction used because Gemini was unavailable or returned an invalid API response.",
    }


def _fallback_mediator_json(prompt: str) -> dict[str, Any]:
    approve = _section_after(prompt, "APPROVE agent:").split("REJECT / RISK agent:", 1)[0].strip()
    reject = _section_after(prompt, "REJECT / RISK agent:").split("Return ONLY valid JSON", 1)[0].strip()
    positive_terms = ["covered", "valid", "align", "consistent", "support", "reasonable", "approve", "pay", "legitimate"]
    negative_terms = ["suspicious", "mismatch", "missing", "denied", "fraud", "inconsistent", "exceeds", "concern", "reject", "escalat"]
    pos = sum(1 for term in positive_terms if term in approve.lower()) + sum(1 for term in positive_terms if term in reject.lower())
    neg = sum(1 for term in negative_terms if term in approve.lower()) + sum(1 for term in negative_terms if term in reject.lower())
    if neg >= pos + 2:
        decision = "REJECT"
    elif pos >= neg + 2:
        decision = "APPROVE"
    else:
        decision = "REVIEW"
    scale = max(1, pos + neg)
    coverage_violation = min(1.0, neg / scale)
    invoice_anomaly = min(1.0, (neg + (1 if "invoice" in reject.lower() else 0)) / (scale + 1))
    timing_suspicion = min(1.0, (1 if "timing" in reject.lower() or "date" in reject.lower() else 0) + (0.25 if "policy" in reject.lower() else 0))
    missing_docs = min(1.0, (1 if "missing" in reject.lower() else 0) + (0.25 if "doc" in reject.lower() else 0))
    historical_pattern = min(1.0, 0.2 if "past" in reject.lower() else 0.0)
    fraud_probability = int(max(0, min(100, round((coverage_violation * 30 + invoice_anomaly * 25 + timing_suspicion * 20 + missing_docs * 15 + historical_pattern * 10) * 1.2))))
    rationale = "Fallback mediator used because Gemini was unavailable."
    if decision == "APPROVE":
        rationale = "The claim appears reasonably aligned with the provided policy and claim details, so approval or straight-through handling is plausible."
    elif decision == "REJECT":
        rationale = "The claim shows stronger risk signals or mismatches, so it should be escalated or denied pending review."
    else:
        rationale = "The evidence is mixed, so manual review is the safest fallback decision."
    return {
        "decision": decision,
        "coverage_violation": round(coverage_violation, 2),
        "invoice_anomaly": round(invoice_anomaly, 2),
        "timing_suspicion": round(timing_suspicion, 2),
        "missing_docs": round(missing_docs, 2),
        "historical_pattern": round(historical_pattern, 2),
        "fraud_probability": fraud_probability,
        "rationale": rationale,
    }


def _fallback_generate_json(prompt: str) -> dict[str, Any]:
    if "Extract structured fields from the claim document text" in prompt:
        return _fallback_claim_json(_section_after(prompt, "Document text:"))
    if "Extract structured invoice/repair bill fields" in prompt:
        return _fallback_invoice_json(_section_after(prompt, "Invoice text:"))
    if "Extract high-level policy metadata" in prompt:
        return _fallback_policy_json(_section_after(prompt, "Policy text (may be partial):"))
    if "Return ONLY valid JSON" in prompt and "fraud_probability" in prompt:
        return _fallback_mediator_json(prompt)
    return {}


def _fallback_generate_text(prompt: str) -> str:
    if "You are the APPROVE agent" in prompt:
        return (
            "The claim can be treated as supportable if the supplied policy excerpts cover the described loss and the documentation is internally consistent. "
            "In fallback mode, treat this as a provisional approve-side summary rather than a definitive coverage opinion."
        )
    if "You are the RISK / REJECT agent" in prompt:
        return (
            "The claim should be reviewed carefully for coverage gaps, date mismatches, incomplete evidence, or invoice irregularities. "
            "In fallback mode, this is a conservative reject-side summary for manual review."
        )
    return "Gemini fallback was used, so the response is generated locally from the available claim context."


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9]+", text.lower())


def _hash_token(token: str) -> int:
    return int(hashlib.blake2b(token.encode("utf-8"), digest_size=4).hexdigest(), 16)


def _fallback_embed(text: str) -> list[float]:
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * _VECTOR_SIZE
    counts = Counter(tokens)
    vector = [0.0] * _VECTOR_SIZE
    for token, count in counts.items():
        idx = _hash_token(token) % _VECTOR_SIZE
        vector[idx] += float(count)
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


def generate_json(prompt: str, *, temperature: float = 0.2) -> dict[str, Any]:
    try:
        configure_genai()
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini disabled")
        model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group(0))
            raise
    except Exception:
        return _fallback_generate_json(prompt)


def generate_text(prompt: str, *, temperature: float = 0.3) -> str:
    try:
        configure_genai()
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini disabled")
        model = genai.GenerativeModel(
            settings.gemini_model,
            generation_config=genai.GenerationConfig(temperature=temperature),
        )
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()
    except Exception:
        return _fallback_generate_text(prompt)


def _embed_one(text: str, task_type: str) -> list[float]:
    try:
        configure_genai()
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("Gemini disabled")
        try:
            r = genai.embed_content(
                model=settings.gemini_embedding_model,
                content=text[:8000],
                task_type=task_type,
            )
        except Exception:  # noqa: BLE001 — some API versions omit task_type support
            r = genai.embed_content(
                model=settings.gemini_embedding_model,
                content=text[:8000],
            )
        emb = r.get("embedding")
        if emb is None:
            raise RuntimeError("Embedding response missing 'embedding'")
        return [float(x) for x in emb]
    except Exception:
        return _fallback_embed(text)


def embed_documents(chunks: list[str]) -> list[list[float]]:
    return [_embed_one(c, "retrieval_document") for c in chunks]


def embed_query(text: str) -> list[float]:
    return _embed_one(text, "retrieval_query")
