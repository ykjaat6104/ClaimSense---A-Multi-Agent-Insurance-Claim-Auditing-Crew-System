from __future__ import annotations

from typing import Any


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, v))


def compute_risk_score(mediator: dict[str, Any]) -> int:
    """Weighted risk score 0–100 from mediator factor signals."""
    cov = _clamp01(mediator.get("coverage_violation"))
    inv = _clamp01(mediator.get("invoice_anomaly"))
    tim = _clamp01(mediator.get("timing_suspicion"))
    miss = _clamp01(mediator.get("missing_docs"))
    hist = _clamp01(mediator.get("historical_pattern"))
    raw = cov * 30 + inv * 25 + tim * 20 + miss * 15 + hist * 10
    return int(max(0, min(100, round(raw))))


def fraud_probability_from_mediator(mediator: dict[str, Any], risk_score: int) -> int:
    fp = mediator.get("fraud_probability")
    if fp is None:
        return risk_score
    try:
        return int(max(0, min(100, round(float(fp)))))
    except (TypeError, ValueError):
        return risk_score
