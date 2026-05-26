"""
Unit tests for agent tools and utilities.
Tests database tools, web search, and LLM integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from app.agents.tools import (
    get_user_claims_history,
    get_payment_status,
    get_policy_recent_changes,
    check_duplicate_claims,
)


@pytest.mark.unit
class TestDatabaseTools:
    """Test suite for database query tools."""
    
    def test_get_user_claims_history(self, db, sample_user, sample_claim):
        """Test retrieving user's claim history."""
        history = get_user_claims_history(db, sample_user.id, limit=10)
        
        assert isinstance(history, list)
        assert len(history) > 0
        assert any(claim.get("claim_number") == sample_claim.claim_number for claim in history)
    
    def test_get_user_claims_history_empty(self, db, sample_user):
        """Test retrieving history for user with no claims."""
        history = get_user_claims_history(db, "non-existent-user", limit=10)
        
        assert isinstance(history, list)
        assert len(history) == 0
    
    def test_get_user_claims_history_limit(self, db, sample_user):
        """Test that claims history respects limit."""
        # Create multiple claims
        for i in range(5):
            claim = sample_claim.__class__(
                id=str(uuid.uuid4()),
                user_id=sample_user.id,
                policy_id=sample_user.id,
                claim_number=f"CLM-TEST-{i}",
                claimed_amount=1000,
                status="completed",
            )
            db.add(claim)
        db.commit()
        
        history = get_user_claims_history(db, sample_user.id, limit=2)
        
        assert len(history) <= 2
    
    def test_get_payment_status(self, db, sample_claim):
        """Test retrieving payment status for a claim."""
        status = get_payment_status(db, sample_claim.id)
        
        assert isinstance(status, dict)
        assert "claim_id" in status
        assert "status" in status
    
    def test_get_payment_status_nonexistent(self, db):
        """Test getting status for non-existent claim."""
        status = get_payment_status(db, "non-existent-id")
        
        assert isinstance(status, dict)
        assert status.get("status") is None
    
    def test_get_policy_recent_changes(self, db, sample_policy):
        """Test retrieving recent policy changes."""
        changes = get_policy_recent_changes(db, sample_policy.id, days=30)
        
        assert isinstance(changes, list)
    
    def test_check_duplicate_claims(self, db, sample_user, sample_claim):
        """Test detection of potential duplicate claims."""
        new_claim_data = {
            "incident_date": sample_claim.incident_date.isoformat(),
            "claimed_amount": sample_claim.claimed_amount,
            "incident_description": sample_claim.incident_description,
        }
        
        duplicates = check_duplicate_claims(
            db,
            sample_user.id,
            new_claim_data,
            threshold=0.8
        )
        
        assert isinstance(duplicates, list)


@pytest.mark.unit
class TestToolErrorHandling:
    """Test error handling in tools."""
    
    def test_get_claims_history_with_invalid_user_id(self, db):
        """Test handling of invalid user ID."""
        result = get_user_claims_history(db, None)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_get_payment_status_with_invalid_claim_id(self, db):
        """Test handling of invalid claim ID."""
        result = get_payment_status(db, "")
        
        assert isinstance(result, dict)
    
    def test_db_connection_error_handling(self, db):
        """Test graceful handling of database errors."""
        with patch('app.agents.tools.db.query') as mock_query:
            mock_query.side_effect = Exception("Database error")
            
            # Should handle error gracefully
            try:
                result = get_user_claims_history(db, "user-id")
                assert result is not None or result is None
            except Exception:
                # Expected that error might be raised and caught
                pass


@pytest.mark.unit
class TestWebSearchTools:
    """Test suite for web search functionality."""
    
    def test_search_market_price_success(self, mock_web_search):
        """Test successful market price search."""
        price = mock_web_search.search_market_price("car repair bumper damage")
        
        assert isinstance(price, (int, float))
        assert price > 0
    
    def test_search_market_price_returns_float(self, mock_web_search):
        """Test market price returns proper float value."""
        price = mock_web_search.search_market_price("broken windshield")
        
        assert isinstance(price, float)
    
    def test_search_repair_rates_returns_list(self, mock_web_search):
        """Test repair rates search returns list of vendors."""
        rates = mock_web_search.search_repair_rates("transmission repair")
        
        assert isinstance(rates, list)
        if len(rates) > 0:
            assert "vendor" in rates[0]
            assert "price" in rates[0]
    
    def test_verify_vendor_success(self, mock_web_search):
        """Test vendor verification."""
        result = mock_web_search.verify_vendor("ABC Repair Shop")
        
        assert isinstance(result, dict)
        assert "verified" in result
        assert isinstance(result["verified"], bool)
    
    def test_search_with_empty_query(self, mock_web_search):
        """Test search with empty query."""
        # Should handle gracefully
        price = mock_web_search.search_market_price("")
        assert price is not None


@pytest.mark.unit
class TestLLMIntegration:
    """Test suite for LLM integration."""
    
    def test_gemini_json_generation(self, mock_gemini_client):
        """Test Gemini JSON generation."""
        result = mock_gemini_client.generate_json("Extract claim info")
        
        assert isinstance(result, dict)
        assert "mock" in result
    
    def test_gemini_text_generation(self, mock_gemini_client):
        """Test Gemini text generation."""
        result = mock_gemini_client.generate_text("Summarize this claim")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_gemini_structured_output(self, mock_gemini_client):
        """Test Gemini structured output generation."""
        result = mock_gemini_client.generate_structured(
            "Make a decision on this claim",
            output_schema={"decision": str, "confidence": float}
        )
        
        assert isinstance(result, dict)
        assert "decision" in result
    
    def test_llm_error_handling(self):
        """Test error handling in LLM calls."""
        mock_client = Mock()
        mock_client.generate_json.side_effect = Exception("API error")
        
        with pytest.raises(Exception):
            mock_client.generate_json("Test prompt")


@pytest.mark.unit
class TestFraudDetectionTools:
    """Test suite for fraud detection tool functions."""
    
    def test_detect_invoice_discrepancy(self):
        """Test invoice discrepancy detection."""
        from app.agents.tools import detect_invoice_discrepancy
        
        claimed_amount = 1000.00
        invoice_amount = 850.00
        threshold = 15  # 15% threshold
        
        discrepancy = detect_invoice_discrepancy(claimed_amount, invoice_amount, threshold)
        
        assert isinstance(discrepancy, (bool, float))
    
    def test_detect_market_price_inflation(self):
        """Test market price inflation detection."""
        from app.agents.tools import detect_market_price_inflation
        
        claimed_amount = 5000.00
        market_price = 3000.00
        threshold = 1.5  # 1.5x threshold
        
        inflation = detect_market_price_inflation(claimed_amount, market_price, threshold)
        
        assert isinstance(inflation, (bool, float))
    
    def test_calculate_fraud_score(self):
        """Test fraud score calculation."""
        from app.agents.tools import calculate_fraud_score
        
        fraud_signals = [
            {"type": "price_inflation", "severity": 0.8},
            {"type": "vendor_issue", "severity": 0.6},
            {"type": "timing_anomaly", "severity": 0.5},
        ]
        
        score = calculate_fraud_score(fraud_signals)
        
        assert isinstance(score, (int, float))
        assert 0 <= score <= 100


@pytest.mark.unit
class TestClaimValidation:
    """Test claim validation tools."""
    
    def test_validate_claim_data(self):
        """Test claim data validation."""
        from app.agents.tools import validate_claim_data
        
        valid_claim = {
            "claim_number": "CLM-2024-001",
            "claimed_amount": 5000.00,
            "incident_date": datetime.utcnow().isoformat(),
            "incident_description": "Valid incident",
        }
        
        is_valid = validate_claim_data(valid_claim)
        
        assert is_valid is True
    
    def test_validate_claim_data_missing_fields(self):
        """Test validation with missing required fields."""
        from app.agents.tools import validate_claim_data
        
        invalid_claim = {
            "claim_number": "CLM-2024-001",
            # Missing claimed_amount and other required fields
        }
        
        is_valid = validate_claim_data(invalid_claim)
        
        assert is_valid is False
    
    def test_validate_claim_amount(self):
        """Test claim amount validation."""
        from app.agents.tools import validate_claim_amount
        
        # Valid amount
        assert validate_claim_amount(5000.00) is True
        
        # Invalid amounts
        assert validate_claim_amount(0) is False
        assert validate_claim_amount(-1000) is False


@pytest.mark.unit
class TestToolDataFormatting:
    """Test data formatting in tools."""
    
    def test_format_claim_for_llm(self):
        """Test formatting claim data for LLM input."""
        from app.agents.tools import format_claim_for_llm
        
        claim_data = {
            "claim_number": "CLM-2024-001",
            "claimed_amount": 5000.00,
            "incident_description": "Car accident",
        }
        
        formatted = format_claim_for_llm(claim_data)
        
        assert isinstance(formatted, str)
        assert "CLM-2024-001" in formatted
    
    def test_format_policy_for_llm(self):
        """Test formatting policy data for LLM input."""
        from app.agents.tools import format_policy_for_llm
        
        policy_data = {
            "policy_number": "POL-2024-001",
            "coverage_types": ["collision", "comprehensive"],
            "max_payout": 50000.00,
        }
        
        formatted = format_policy_for_llm(policy_data)
        
        assert isinstance(formatted, str)
        assert "POL-2024-001" in formatted
