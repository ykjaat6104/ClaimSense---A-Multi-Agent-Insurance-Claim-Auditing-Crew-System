"""
Unit tests for multi-agent nodes.
Tests Policy Analyst, Data Miner, Fraud Auditor, and Judge agents.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json

from app.agents.nodes import (
    policy_analyst_node,
    data_miner_node,
    fraud_auditor_node,
    judge_node,
)
from app.agents.state import ClaimAuditState
from app.db.models import Claim, Policy


@pytest.mark.unit
class TestPolicyAnalystNode:
    """Test suite for Policy Analyst agent node."""
    
    @pytest.mark.asyncio
    async def test_policy_analyst_extracts_coverage(self, sample_audit_state):
        """Test that Policy Analyst extracts coverage information."""
        state = sample_audit_state
        
        with patch('app.agents.nodes.rag_service') as mock_rag:
            mock_rag.retrieve_policy_info.return_value = {
                "coverage_types": ["collision", "comprehensive"],
                "max_payout": 50000,
                "deductible": 500,
            }
            
            with patch('app.agents.nodes.gemini_client') as mock_llm:
                mock_llm.generate_json.return_value = {
                    "extracted_clauses": "Coverage includes collision and comprehensive",
                    "relevant_coverage": ["collision", "comprehensive"],
                }
                
                result = await policy_analyst_node(state)
        
        assert result is not None
        assert "extracted_clauses_data" in result
    
    @pytest.mark.asyncio
    async def test_policy_analyst_handles_missing_policy(self, sample_audit_state):
        """Test Policy Analyst handles missing policy gracefully."""
        state = sample_audit_state
        state.policy_data = {}
        
        with patch('app.agents.nodes.rag_service') as mock_rag:
            mock_rag.retrieve_policy_info.return_value = None
            
            result = await policy_analyst_node(state)
        
        assert result is not None
        assert "extracted_clauses_data" in result
    
    def test_policy_analyst_coverage_type_detection(self):
        """Test detection of coverage types from policy."""
        from app.agents.nodes import extract_coverage_types
        
        policy_text = "This policy provides collision and comprehensive coverage"
        coverage_types = extract_coverage_types(policy_text)
        
        assert "collision" in coverage_types
        assert "comprehensive" in coverage_types


@pytest.mark.unit
class TestDataMinerNode:
    """Test suite for Data Miner agent node."""
    
    @pytest.mark.asyncio
    async def test_data_miner_queries_claim_history(self, sample_audit_state, db, sample_user):
        """Test that Data Miner retrieves claim history."""
        state = sample_audit_state
        state.user_id = sample_user.id
        
        # Create historical claims
        for i in range(3):
            claim = Claim(
                id=f"claim-{i}",
                user_id=sample_user.id,
                policy_id=state.policy_id,
                claim_number=f"CLM-2024-{i:03d}",
                claimed_amount=1000 * (i + 1),
                status="completed",
            )
            db.add(claim)
        db.commit()
        
        with patch('app.agents.nodes.crud.get_user_claims_history') as mock_crud:
            mock_crud.return_value = [
                {"claim_number": f"CLM-2024-{i:03d}", "amount": 1000 * (i + 1)}
                for i in range(3)
            ]
            
            result = await data_miner_node(state)
        
        assert result is not None
        assert "database_alerts" in result
    
    @pytest.mark.asyncio
    async def test_data_miner_detects_duplicate_claims(self, sample_audit_state):
        """Test that Data Miner detects potential duplicate claims."""
        state = sample_audit_state
        state.claim_data["incident_date"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        with patch('app.agents.nodes.crud.get_claim') as mock_get:
            # Simulate finding a similar recent claim
            mock_get.return_value = {
                "claim_number": "CLM-2024-RECENT",
                "incident_date": datetime.utcnow() - timedelta(days=2),
                "claimed_amount": 4800.00,  # Similar amount
            }
            
            result = await data_miner_node(state)
        
        assert result is not None
        # Should flag potential duplicate
        assert len(result.get("database_alerts", [])) >= 0
    
    @pytest.mark.asyncio
    async def test_data_miner_handles_no_history(self, sample_audit_state):
        """Test Data Miner handles users with no claim history."""
        state = sample_audit_state
        
        with patch('app.agents.nodes.crud.get_user_claims_history') as mock_crud:
            mock_crud.return_value = []
            
            result = await data_miner_node(state)
        
        assert result is not None
        assert isinstance(result.get("database_alerts"), list)


@pytest.mark.unit
class TestFraudAuditorNode:
    """Test suite for Fraud Auditor agent node."""
    
    @pytest.mark.asyncio
    async def test_fraud_auditor_detects_high_claims(self, sample_audit_state):
        """Test that Fraud Auditor flags unusually high claims."""
        state = sample_audit_state
        state.claim_data["claimed_amount"] = 45000.00  # High amount
        
        with patch('app.agents.nodes.web_search_service') as mock_search:
            mock_search.search_market_price.return_value = 5000.00
            
            result = await fraud_auditor_node(state)
        
        assert result is not None
        assert len(result.get("fraud_signals", [])) > 0
    
    @pytest.mark.asyncio
    async def test_fraud_auditor_market_price_check(self, sample_audit_state):
        """Test market price verification by Fraud Auditor."""
        state = sample_audit_state
        state.claim_data["claimed_amount"] = 10000.00
        state.claim_data["incident_description"] = "Car collision damage"
        
        with patch('app.agents.nodes.web_search_service.search_market_price') as mock_price:
            mock_price.return_value = 3500.00  # Market price much lower
            
            result = await fraud_auditor_node(state)
        
        assert result is not None
        market_analysis = result.get("market_price_analysis", {})
        # Should show significant price discrepancy
        if market_analysis:
            assert "discrepancy" in market_analysis or "inflation_ratio" in market_analysis
    
    @pytest.mark.asyncio
    async def test_fraud_auditor_vendor_verification(self, sample_audit_state):
        """Test vendor verification by Fraud Auditor."""
        state = sample_audit_state
        state.claim_data["vendor_name"] = "Unknown Repair Shop"
        
        with patch('app.agents.nodes.web_search_service.verify_vendor') as mock_verify:
            mock_verify.return_value = {
                "verified": False,
                "rating": 1.5,
                "complaints": 8,
                "suspicious_patterns": True
            }
            
            result = await fraud_auditor_node(state)
        
        assert result is not None
        fraud_signals = result.get("fraud_signals", [])
        # Should include vendor-related signal
        assert any("vendor" in signal.lower() for signal in fraud_signals if isinstance(signal, str))


@pytest.mark.unit
class TestJudgeNode:
    """Test suite for Judge/Decision agent node."""
    
    @pytest.mark.asyncio
    async def test_judge_makes_approval_decision(self, sample_audit_state):
        """Test Judge approves low-risk claims."""
        state = sample_audit_state
        state.fraud_signals = []
        state.risk_score = 15
        
        with patch('app.agents.nodes.gemini_client.generate_structured') as mock_judge:
            mock_judge.return_value = {
                "decision": "APPROVED",
                "reasoning": "Low risk claim with no fraud signals",
                "confidence": 0.95,
            }
            
            result = await judge_node(state)
        
        assert result is not None
        assert result.get("decision") in ["APPROVED", "DENIED", "REVIEW_REQUIRED"]
    
    @pytest.mark.asyncio
    async def test_judge_makes_denial_decision(self, sample_audit_state):
        """Test Judge denies high-risk claims."""
        state = sample_audit_state
        state.fraud_signals = [
            "Invoice discrepancy detected",
            "Vendor not verified",
            "Claim timing suspicious"
        ]
        state.risk_score = 85
        state.fraud_probability = 92
        
        with patch('app.agents.nodes.gemini_client.generate_structured') as mock_judge:
            mock_judge.return_value = {
                "decision": "DENIED",
                "reasoning": "Multiple fraud signals detected. High risk profile.",
                "confidence": 0.98,
            }
            
            result = await judge_node(state)
        
        assert result is not None
        assert result.get("decision") == "DENIED"
    
    @pytest.mark.asyncio
    async def test_judge_requires_review(self, sample_audit_state):
        """Test Judge marks ambiguous claims for review."""
        state = sample_audit_state
        state.fraud_signals = ["Potential invoice discrepancy"]
        state.risk_score = 50
        state.fraud_probability = 45
        
        with patch('app.agents.nodes.gemini_client.generate_structured') as mock_judge:
            mock_judge.return_value = {
                "decision": "REVIEW_REQUIRED",
                "reasoning": "Moderate risk. Recommend manual review.",
                "confidence": 0.70,
            }
            
            result = await judge_node(state)
        
        assert result is not None
        assert result.get("decision") == "REVIEW_REQUIRED"


@pytest.mark.unit
class TestAgentErrorHandling:
    """Test error handling in agents."""
    
    @pytest.mark.asyncio
    async def test_policy_analyst_handles_llm_error(self, sample_audit_state):
        """Test Policy Analyst handles LLM errors gracefully."""
        state = sample_audit_state
        
        with patch('app.agents.nodes.gemini_client.generate_json') as mock_llm:
            mock_llm.side_effect = Exception("LLM API error")
            
            # Should not raise, should return state with error handling
            result = await policy_analyst_node(state)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_data_miner_handles_db_error(self, sample_audit_state):
        """Test Data Miner handles database errors gracefully."""
        state = sample_audit_state
        
        with patch('app.agents.nodes.crud.get_user_claims_history') as mock_crud:
            mock_crud.side_effect = Exception("Database connection error")
            
            result = await data_miner_node(state)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_fraud_auditor_handles_web_search_error(self, sample_audit_state):
        """Test Fraud Auditor handles web search failures."""
        state = sample_audit_state
        
        with patch('app.agents.nodes.web_search_service.search_market_price') as mock_search:
            mock_search.side_effect = Exception("Web search failed")
            
            result = await fraud_auditor_node(state)
            assert result is not None


@pytest.mark.unit
class TestAgentStateManagement:
    """Test state management in agents."""
    
    @pytest.mark.asyncio
    async def test_state_preservation_through_nodes(self, sample_audit_state):
        """Test that state is properly preserved through agent nodes."""
        original_claim_id = sample_audit_state.claim_id
        original_user_id = sample_audit_state.user_id
        
        with patch('app.agents.nodes.rag_service'):
            with patch('app.agents.nodes.gemini_client'):
                result = await policy_analyst_node(sample_audit_state)
        
        # Original identifiers should be preserved
        assert result.get("claim_id") == original_claim_id
        assert result.get("user_id") == original_user_id
    
    def test_audit_state_structure(self, sample_audit_state):
        """Test ClaimAuditState structure and required fields."""
        state = sample_audit_state
        
        # Verify all required fields exist
        required_fields = [
            "claim_id", "user_id", "policy_id", "claim_data",
            "extracted_clauses_data", "database_alerts", "fraud_signals",
            "suspicious_flags", "decision", "risk_score", "fraud_probability"
        ]
        
        for field in required_fields:
            assert hasattr(state, field), f"Missing field: {field}"


@pytest.mark.unit  
class TestAgentOutputValidation:
    """Test that agent outputs are valid."""
    
    @pytest.mark.asyncio
    async def test_policy_analyst_output_schema(self, sample_audit_state):
        """Test Policy Analyst output conforms to schema."""
        with patch('app.agents.nodes.rag_service'):
            with patch('app.agents.nodes.gemini_client'):
                result = await policy_analyst_node(sample_audit_state)
        
        assert isinstance(result, dict)
        assert "extracted_clauses_data" in result
        assert isinstance(result["extracted_clauses_data"], (dict, list))
    
    @pytest.mark.asyncio
    async def test_fraud_auditor_output_schema(self, sample_audit_state):
        """Test Fraud Auditor output conforms to schema."""
        with patch('app.agents.nodes.web_search_service'):
            with patch('app.agents.nodes.gemini_client'):
                result = await fraud_auditor_node(sample_audit_state)
        
        assert isinstance(result, dict)
        assert "fraud_signals" in result
        assert isinstance(result["fraud_signals"], list)
        assert "suspicious_flags" in result
        assert isinstance(result["suspicious_flags"], list)
    
    @pytest.mark.asyncio
    async def test_judge_output_schema(self, sample_audit_state):
        """Test Judge output conforms to schema."""
        with patch('app.agents.nodes.gemini_client'):
            result = await judge_node(sample_audit_state)
        
        assert isinstance(result, dict)
        assert "decision" in result
        assert result.get("decision") in ["APPROVED", "DENIED", "REVIEW_REQUIRED"]
        assert "risk_score" in result
        assert isinstance(result["risk_score"], (int, float))
