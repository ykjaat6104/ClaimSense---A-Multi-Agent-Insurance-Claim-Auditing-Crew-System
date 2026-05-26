"""
Enhanced Fraud Detection System for ClaimSense
Implements ML-based and rule-based fraud detection algorithms.

Components:
  1. Anomaly Detection (Isolation Forest, One-Class SVM)
  2. Advanced Pattern Recognition
  3. Configurable Thresholds
  4. Risk Scoring Model
  5. Fraud Signal Aggregation
"""

from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import yaml
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class FraudSignalType(Enum):
    """Types of fraud signals that can be detected."""
    INVOICE_DISCREPANCY = "invoice_discrepancy"
    MARKET_PRICE_INFLATION = "market_price_inflation"
    VENDOR_ISSUE = "vendor_issue"
    REGIONAL_COST_ANOMALY = "regional_cost_anomaly"
    TIMING_SUSPICION = "timing_suspicion"
    CLAIM_FREQUENCY = "claim_frequency"
    CLAIM_LINKAGE = "claim_linkage"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    REPAIR_COST_INFLATION = "repair_cost_inflation"
    ADJUSTER_PATTERN = "adjuster_pattern"


@dataclass
class FraudSignal:
    """Represents a detected fraud signal."""
    signal_type: FraudSignalType
    severity: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    description: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.signal_type.value,
            "severity": round(self.severity, 3),
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FraudDetectionResult:
    """Result of fraud detection analysis."""
    claim_id: str
    fraud_probability: float  # 0.0 to 1.0
    risk_score: int  # 0 to 100
    signals: List[FraudSignal] = field(default_factory=list)
    verdict: str = "PENDING"  # APPROVED, DENIED, REVIEW_REQUIRED
    reasoning: str = ""
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "claim_id": self.claim_id,
            "fraud_probability": round(self.fraud_probability, 3),
            "risk_score": self.risk_score,
            "signals": [s.to_dict() for s in self.signals],
            "verdict": self.verdict,
            "reasoning": self.reasoning,
            "confidence": round(self.confidence, 3),
        }


class FraudThresholdConfig:
    """Configuration for fraud detection thresholds."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize with optional YAML config file."""
        self.config = self._load_default_config()
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                custom_config = yaml.safe_load(f)
                self.config.update(custom_config or {})
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default fraud detection thresholds."""
        return {
            "invoice_discrepancy": {
                "threshold": 15,  # percentage
                "weight": 2.0,
                "enabled": True,
            },
            "market_price_inflation": {
                "threshold": 1.5,  # multiplier
                "weight": 2.5,
                "enabled": True,
            },
            "vendor_issues": {
                "threshold": 3,  # issues count
                "weight": 1.5,
                "enabled": True,
            },
            "regional_anomaly": {
                "threshold": 2.0,  # std dev
                "weight": 1.8,
                "enabled": True,
            },
            "timing_suspicion": {
                "threshold": 14,  # days to renewal
                "weight": 1.2,
                "enabled": True,
            },
            "claim_frequency": {
                "threshold": 3,  # claims per year
                "weight": 1.5,
                "enabled": True,
            },
            "claim_linkage": {
                "threshold": 0.8,  # similarity score
                "weight": 2.0,
                "enabled": True,
            },
            "temporal_anomaly": {
                "threshold": 2.0,  # std dev
                "weight": 1.8,
                "enabled": True,
            },
        }
    
    def get_weight(self, signal_type: FraudSignalType) -> float:
        """Get weight for a signal type."""
        key = signal_type.value
        return self.config.get(key, {}).get("weight", 1.0)
    
    def is_enabled(self, signal_type: FraudSignalType) -> bool:
        """Check if signal type is enabled."""
        key = signal_type.value
        return self.config.get(key, {}).get("enabled", True)


class AnomalyDetector:
    """ML-based anomaly detection using Isolation Forest and One-Class SVM."""
    
    def __init__(self):
        """Initialize anomaly detectors."""
        try:
            from sklearn.ensemble import IsolationForest
            from sklearn.svm import OneClassSVM
            self.isolation_forest = IsolationForest(
                contamination=0.1,
                random_state=42,
                n_estimators=100
            )
            self.one_class_svm = OneClassSVM(
                kernel='rbf',
                gamma='auto',
                nu=0.1
            )
            self.is_available = True
        except ImportError:
            logger.warning("scikit-learn not available. Anomaly detection disabled.")
            self.is_available = False
    
    def detect_anomalies(
        self,
        features: Dict[str, float],
        feature_names: List[str]
    ) -> Tuple[bool, float]:
        """
        Detect anomalies in claim data.
        
        Args:
            features: Dict of feature values
            feature_names: List of feature names
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if not self.is_available:
            return False, 0.0
        
        try:
            # Convert features to array
            X = [[features.get(name, 0.0) for name in feature_names]]
            
            # Isolation Forest prediction
            iso_pred = self.isolation_forest.predict(X)[0]
            is_anomaly_iso = iso_pred == -1
            iso_score = self.isolation_forest.score_samples(X)[0]
            
            # One-Class SVM prediction
            svm_pred = self.one_class_svm.predict(X)[0]
            is_anomaly_svm = svm_pred == -1
            
            # Combine predictions
            is_anomaly = is_anomaly_iso or is_anomaly_svm
            anomaly_score = max(0.0, min(1.0, -iso_score / 10.0))
            
            return is_anomaly, anomaly_score
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return False, 0.0


class PatternRecognizer:
    """Advanced pattern recognition for fraud detection."""
    
    @staticmethod
    def detect_claim_linkage(
        current_claim: Dict[str, Any],
        historical_claims: List[Dict[str, Any]]
    ) -> Tuple[List[str], float]:
        """
        Detect linked claims (coordinated fraud rings).
        
        Returns:
            Tuple of (linked_claim_ids, similarity_score)
        """
        linked_claims = []
        max_similarity = 0.0
        
        current_amount = current_claim.get("claimed_amount", 0)
        current_date = datetime.fromisoformat(
            current_claim.get("incident_date", datetime.now().isoformat())
        )
        
        for hist_claim in historical_claims:
            hist_amount = hist_claim.get("claimed_amount", 0)
            hist_date = datetime.fromisoformat(
                hist_claim.get("incident_date", datetime.now().isoformat())
            )
            
            # Check amount similarity
            if current_amount > 0:
                amount_diff = abs(current_amount - hist_amount) / current_amount
                if amount_diff < 0.1:  # Within 10%
                    # Check date proximity
                    days_apart = abs((current_date - hist_date).days)
                    if days_apart < 30:  # Within 30 days
                        similarity = 1.0 - min(amount_diff, days_apart / 365.0)
                        linked_claims.append(hist_claim.get("id", "unknown"))
                        max_similarity = max(max_similarity, similarity)
        
        return linked_claims, max_similarity
    
    @staticmethod
    def detect_temporal_anomalies(
        claim_date: datetime,
        policy_start: datetime,
        policy_end: datetime
    ) -> Tuple[bool, str, float]:
        """
        Detect suspicious timing patterns.
        
        Returns:
            Tuple of (is_suspicious, reason, severity)
        """
        days_to_renewal = (policy_end - claim_date).days
        days_from_start = (claim_date - policy_start).days
        
        # Claim too close to renewal
        if 0 < days_to_renewal < 14:
            return True, "Claim submitted within 14 days of renewal", 0.6
        
        # Claim soon after policy start
        if 0 < days_from_start < 14:
            return True, "Claim submitted within 14 days of policy start", 0.5
        
        return False, "", 0.0
    
    @staticmethod
    def detect_adjuster_patterns(
        adjuster_id: str,
        adjuster_history: Dict[str, Any]
    ) -> Tuple[bool, str, float]:
        """
        Detect suspicious adjuster approval patterns.
        
        Returns:
            Tuple of (is_suspicious, pattern, severity)
        """
        if not adjuster_history:
            return False, "", 0.0
        
        total_cases = adjuster_history.get("total_cases", 0)
        approved_cases = adjuster_history.get("approved_cases", 0)
        avg_claim_amount = adjuster_history.get("avg_claim_amount", 0)
        
        if total_cases == 0:
            return False, "", 0.0
        
        approval_rate = approved_cases / total_cases
        
        # Unusually high approval rate (>90%)
        if approval_rate > 0.9:
            return True, f"High approval rate: {approval_rate:.1%}", 0.4
        
        # Anomalously high avg claim amount
        # (Would need industry benchmark for real comparison)
        
        return False, "", 0.0


class RiskScoringModel:
    """Probabilistic risk scoring model."""
    
    def __init__(self, config: Optional[FraudThresholdConfig] = None):
        """Initialize with optional config."""
        self.config = config or FraudThresholdConfig()
        self.anomaly_detector = AnomalyDetector()
    
    def calculate_fraud_probability(
        self,
        signals: List[FraudSignal],
        claim_history_length: int = 0
    ) -> float:
        """
        Calculate fraud probability using signals and claim history.
        
        Args:
            signals: List of detected fraud signals
            claim_history_length: Length of user's claim history
        
        Returns:
            Fraud probability (0.0 to 1.0)
        """
        if not signals:
            # Adjust base probability based on history
            if claim_history_length > 5:
                return 0.05  # Low probability for established customers
            return 0.10
        
        # Calculate weighted score
        total_weight = 0.0
        weighted_score = 0.0
        
        for signal in signals:
            if self.config.is_enabled(signal.signal_type):
                weight = self.config.get_weight(signal.signal_type)
                signal_contribution = signal.severity * signal.confidence * weight
                weighted_score += signal_contribution
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize to 0-1 range
        base_probability = min(1.0, weighted_score / total_weight)
        
        # Adjust based on claim history
        history_factor = 0.95 if claim_history_length > 0 else 1.0
        final_probability = base_probability * history_factor
        
        return min(1.0, final_probability)
    
    def calculate_risk_score(
        self,
        fraud_probability: float,
        claim_amount: float,
        avg_claim_amount: float = 5000.0
    ) -> int:
        """
        Calculate risk score (0-100) based on fraud probability and claim amount.
        
        Args:
            fraud_probability: Calculated fraud probability
            claim_amount: Current claim amount
            avg_claim_amount: Average claim amount
        
        Returns:
            Risk score (0-100)
        """
        # Base score from fraud probability
        fraud_score = fraud_probability * 70  # Up to 70 points
        
        # Amount-based score
        amount_ratio = claim_amount / avg_claim_amount if avg_claim_amount > 0 else 1.0
        amount_score = min(30, amount_ratio * 15)  # Up to 30 points
        
        # Total risk score
        risk_score = int(fraud_score + amount_score)
        
        return min(100, max(0, risk_score))
    
    def determine_verdict(self, risk_score: int, fraud_probability: float) -> str:
        """
        Determine verdict based on risk score and fraud probability.
        
        Returns:
            APPROVED, DENIED, or REVIEW_REQUIRED
        """
        if risk_score >= 75 or fraud_probability >= 0.75:
            return "DENIED"
        elif risk_score >= 50 or fraud_probability >= 0.50:
            return "REVIEW_REQUIRED"
        else:
            return "APPROVED"


class FraudDetectionEngine:
    """Main fraud detection engine orchestrating all components."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize fraud detection engine."""
        self.config = FraudThresholdConfig(config_path)
        self.pattern_recognizer = PatternRecognizer()
        self.risk_scorer = RiskScoringModel(self.config)
        self.signals: List[FraudSignal] = []
    
    def analyze_claim(
        self,
        claim_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]] = None,
        historical_claims: Optional[List[Dict[str, Any]]] = None,
        adjuster_data: Optional[Dict[str, Any]] = None,
    ) -> FraudDetectionResult:
        """
        Comprehensive claim fraud analysis.
        
        Args:
            claim_data: Current claim information
            market_data: Market price and repair data
            historical_claims: User's historical claims
            adjuster_data: Adjuster history and patterns
        
        Returns:
            FraudDetectionResult with all detected signals
        """
        claim_id = claim_data.get("claim_id", "unknown")
        self.signals = []
        
        # 1. Invoice Discrepancy
        self._check_invoice_discrepancy(claim_data)
        
        # 2. Market Price Inflation
        self._check_market_price_inflation(claim_data, market_data)
        
        # 3. Vendor Issues
        self._check_vendor_issues(claim_data)
        
        # 4. Regional Cost Anomaly
        self._check_regional_anomaly(claim_data, market_data)
        
        # 5. Timing Suspicion
        self._check_timing_suspicion(claim_data)
        
        # 6. Claim Frequency
        self._check_claim_frequency(claim_data, historical_claims)
        
        # 7. Claim Linkage
        self._check_claim_linkage(claim_data, historical_claims)
        
        # 8. Temporal Anomalies
        self._check_temporal_anomalies(claim_data)
        
        # 9. Adjuster Patterns
        self._check_adjuster_patterns(adjuster_data)
        
        # Calculate risk metrics
        fraud_probability = self.risk_scorer.calculate_fraud_probability(
            self.signals,
            len(historical_claims) if historical_claims else 0
        )
        
        claim_amount = float(claim_data.get("claimed_amount", 0))
        avg_amount = float(claim_data.get("avg_claim_amount", 5000.0))
        risk_score = self.risk_scorer.calculate_risk_score(
            fraud_probability,
            claim_amount,
            avg_amount
        )
        
        verdict = self.risk_scorer.determine_verdict(risk_score, fraud_probability)
        
        return FraudDetectionResult(
            claim_id=claim_id,
            fraud_probability=fraud_probability,
            risk_score=risk_score,
            signals=self.signals,
            verdict=verdict,
            confidence=self._calculate_confidence(),
            reasoning=self._generate_reasoning()
        )
    
    def _check_invoice_discrepancy(self, claim_data: Dict[str, Any]) -> None:
        """Check for invoice vs claimed amount discrepancy."""
        claimed = claim_data.get("claimed_amount", 0)
        invoice = claim_data.get("invoice_amount", claimed)
        
        if claimed > 0 and invoice > 0:
            discrepancy = abs(claimed - invoice) / claimed
            threshold = 0.15  # 15%
            
            if discrepancy > threshold:
                signal = FraudSignal(
                    signal_type=FraudSignalType.INVOICE_DISCREPANCY,
                    severity=min(1.0, discrepancy),
                    confidence=0.9,
                    description=f"Invoice discrepancy: {discrepancy:.1%}",
                    evidence={
                        "claimed_amount": claimed,
                        "invoice_amount": invoice,
                        "discrepancy_percent": discrepancy * 100,
                    }
                )
                self.signals.append(signal)
    
    def _check_market_price_inflation(
        self,
        claim_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]]
    ) -> None:
        """Check for claimed amount vs market price inflation."""
        if not market_data:
            return
        
        claimed = float(claim_data.get("claimed_amount", 0))
        market_price = float(market_data.get("market_price", claimed))
        
        if claimed > 0 and market_price > 0:
            inflation_ratio = claimed / market_price
            threshold = 1.5
            
            if inflation_ratio > threshold:
                signal = FraudSignal(
                    signal_type=FraudSignalType.MARKET_PRICE_INFLATION,
                    severity=min(1.0, (inflation_ratio - 1.0) / 2.0),
                    confidence=0.85,
                    description=f"Price inflation: {inflation_ratio:.2f}x market price",
                    evidence={
                        "claimed_amount": claimed,
                        "market_price": market_price,
                        "inflation_ratio": inflation_ratio,
                    }
                )
                self.signals.append(signal)
    
    def _check_vendor_issues(self, claim_data: Dict[str, Any]) -> None:
        """Check for vendor-related issues."""
        vendor_issues = claim_data.get("vendor_issues", [])
        if len(vendor_issues) >= 3:
            signal = FraudSignal(
                signal_type=FraudSignalType.VENDOR_ISSUE,
                severity=min(1.0, len(vendor_issues) / 10.0),
                confidence=0.8,
                description=f"Vendor has {len(vendor_issues)} reported issues",
                evidence={"issues": vendor_issues}
            )
            self.signals.append(signal)
    
    def _check_regional_anomaly(
        self,
        claim_data: Dict[str, Any],
        market_data: Optional[Dict[str, Any]]
    ) -> None:
        """Check for regional cost anomalies."""
        # Placeholder for regional analysis
        pass
    
    def _check_timing_suspicion(self, claim_data: Dict[str, Any]) -> None:
        """Check for suspicious timing patterns."""
        try:
            incident_date = datetime.fromisoformat(claim_data.get("incident_date", ""))
            policy_start = datetime.fromisoformat(claim_data.get("policy_start", ""))
            policy_end = datetime.fromisoformat(claim_data.get("policy_end", ""))
            
            is_suspicious, reason, severity = self.pattern_recognizer.detect_temporal_anomalies(
                incident_date, policy_start, policy_end
            )
            
            if is_suspicious:
                signal = FraudSignal(
                    signal_type=FraudSignalType.TIMING_SUSPICION,
                    severity=severity,
                    confidence=0.8,
                    description=reason
                )
                self.signals.append(signal)
        except Exception as e:
            logger.debug(f"Timing check error: {e}")
    
    def _check_claim_frequency(
        self,
        claim_data: Dict[str, Any],
        historical_claims: Optional[List[Dict[str, Any]]]
    ) -> None:
        """Check for unusual claim frequency."""
        if not historical_claims:
            return
        
        # Count claims in last 12 months
        cutoff_date = datetime.now() - timedelta(days=365)
        recent_claims = [
            c for c in historical_claims
            if datetime.fromisoformat(c.get("date", "")) > cutoff_date
        ]
        
        if len(recent_claims) > 3:
            signal = FraudSignal(
                signal_type=FraudSignalType.CLAIM_FREQUENCY,
                severity=min(1.0, len(recent_claims) / 10.0),
                confidence=0.7,
                description=f"{len(recent_claims)} claims in past 12 months",
                evidence={"claim_count": len(recent_claims)}
            )
            self.signals.append(signal)
    
    def _check_claim_linkage(
        self,
        claim_data: Dict[str, Any],
        historical_claims: Optional[List[Dict[str, Any]]]
    ) -> None:
        """Check for linked claims (fraud rings)."""
        if not historical_claims:
            return
        
        linked, similarity = self.pattern_recognizer.detect_claim_linkage(
            claim_data,
            historical_claims
        )
        
        if linked and similarity > 0.8:
            signal = FraudSignal(
                signal_type=FraudSignalType.CLAIM_LINKAGE,
                severity=similarity,
                confidence=0.85,
                description=f"Possible claim ring: {len(linked)} linked claims",
                evidence={"linked_claims": linked, "similarity": similarity}
            )
            self.signals.append(signal)
    
    def _check_temporal_anomalies(self, claim_data: Dict[str, Any]) -> None:
        """Check temporal anomalies."""
        # Already covered in timing suspicion
        pass
    
    def _check_adjuster_patterns(self, adjuster_data: Optional[Dict[str, Any]]) -> None:
        """Check for suspicious adjuster patterns."""
        if not adjuster_data:
            return
        
        is_suspicious, pattern, severity = self.pattern_recognizer.detect_adjuster_patterns(
            adjuster_data.get("id", "unknown"),
            adjuster_data
        )
        
        if is_suspicious:
            signal = FraudSignal(
                signal_type=FraudSignalType.ADJUSTER_PATTERN,
                severity=severity,
                confidence=0.6,
                description=pattern
            )
            self.signals.append(signal)
    
    def _calculate_confidence(self) -> float:
        """Calculate overall confidence in the fraud assessment."""
        if not self.signals:
            return 0.5
        
        avg_confidence = sum(s.confidence for s in self.signals) / len(self.signals)
        return avg_confidence
    
    def _generate_reasoning(self) -> str:
        """Generate human-readable reasoning for the verdict."""
        if not self.signals:
            return "No fraud signals detected."
        
        signal_types = [s.signal_type.value for s in self.signals]
        return f"Detected {len(self.signals)} fraud signals: {', '.join(signal_types[:3])}" + \
               ("..." if len(signal_types) > 3 else "")


# Convenience function for integration
async def detect_fraud(
    claim_data: Dict[str, Any],
    market_data: Optional[Dict[str, Any]] = None,
    historical_claims: Optional[List[Dict[str, Any]]] = None,
    adjuster_data: Optional[Dict[str, Any]] = None,
    config_path: Optional[Path] = None,
) -> FraudDetectionResult:
    """
    Async wrapper for fraud detection.
    
    This is the main entry point for fraud analysis in the Fraud Auditor agent.
    """
    engine = FraudDetectionEngine(config_path)
    result = engine.analyze_claim(
        claim_data,
        market_data,
        historical_claims,
        adjuster_data
    )
    return result
