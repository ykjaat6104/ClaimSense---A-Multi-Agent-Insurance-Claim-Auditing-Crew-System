"""
Integration tests for multi-agent workflow.
Tests agent interactions, state management, and orchestration.
"""

import pytest
from unittest.mock import patch, AsyncMock
import uuid


@pytest.mark.integration
class TestMultiAgentWorkflow:
    """Integration tests for the complete audit workflow."""
    
    @pytest.mark.asyncio
    async def test_full_audit_workflow(self, sample_audit_state):
        """Test complete audit workflow from start to finish."""
        from app.agents.orchestrator import run_claim_audit_workflow
        
        state = sample_audit_state
        
        with patch('app.agents.nodes.rag_service'):
            with patch('app.agents.nodes.gemini_client'):
                with patch('app.agents.nodes.web_search_service'):
                    # Run workflow
                    result = await run_claim_audit_workflow(state)
        
        assert result is not None
        assert "decision" in result
        assert result.get("decision") in ["APPROVED", "DENIED", "REVIEW_REQUIRED"]
    
    @pytest.mark.asyncio
    async def test_agent_state_flow(self, sample_audit_state):
        """Test that state flows correctly through all agents."""
        from app.agents.nodes import (
            policy_analyst_node,
            data_miner_node,
            fraud_auditor_node,
            judge_node,
        )
        
        state = sample_audit_state
        
        with patch('app.agents.nodes.rag_service'):
            with patch('app.agents.nodes.gemini_client'):
                with patch('app.agents.nodes.web_search_service'):
                    with patch('app.agents.nodes.crud'):
                        # Run through agents sequentially
                        state_after_analyst = await policy_analyst_node(state)
                        assert state_after_analyst is not None
                        
                        state_after_miner = await data_miner_node(state_after_analyst)
                        assert state_after_miner is not None
                        
                        state_after_auditor = await fraud_auditor_node(state_after_miner)
                        assert state_after_auditor is not None
                        
                        final_state = await judge_node(state_after_auditor)
                        assert final_state is not None
    
    @pytest.mark.asyncio
    async def test_conditional_routing(self, sample_audit_state):
        """Test conditional routing logic based on fraud evidence."""
        from app.agents.orchestrator import conditional_route_after_audit
        
        # Test routing for sufficient evidence
        state_with_evidence = sample_audit_state
        state_with_evidence.fraud_signals = [
            "Signal 1",
            "Signal 2",
            "Signal 3",
        ]
        
        with patch('app.agents.orchestrator.judge_node'):
            route = conditional_route_after_audit(state_with_evidence)
            assert route is not None


@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations."""
    
    def test_claim_creation_and_retrieval(self, db, sample_user, sample_policy):
        """Test creating and retrieving claims."""
        from app.db import crud
        
        claim_data = {
            "user_id": sample_user.id,
            "policy_id": sample_policy.id,
            "claim_number": "CLM-TEST-INT-001",
            "incident_description": "Integration test incident",
            "claimed_amount": 5000.00,
            "status": "pending",
        }
        
        # Create
        created = crud.create_claim(db, claim_data)
        assert created is not None
        
        # Retrieve
        retrieved = crud.get_claim(db, created.id)
        assert retrieved.claim_number == "CLM-TEST-INT-001"
    
    def test_claim_update_integration(self, db, sample_claim):
        """Test updating claim through database."""
        from app.db import crud
        
        update_data = {
            "status": "completed",
            "decision": "APPROVED",
            "risk_score": 25,
        }
        
        updated = crud.update_claim(db, sample_claim.id, update_data)
        
        assert updated.status == "completed"
        assert updated.decision == "APPROVED"
    
    def test_policy_claim_relationship(self, db, sample_user, sample_policy, sample_claim):
        """Test relationship between policies and claims."""
        from app.db import crud
        
        # Get claims for policy
        claims = crud.get_policy_claims(db, sample_policy.id)
        
        assert isinstance(claims, list)
        assert any(c.id == sample_claim.id for c in claims)


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints."""
    
    def test_audit_trigger_to_status_flow(self, client, sample_claim, auth_headers):
        """Test triggering audit and checking status."""
        # Trigger audit
        trigger_response = client.post(
            f"/api/v2/audit/trigger?claim_id={sample_claim.id}",
            headers=auth_headers
        )
        
        if trigger_response.status_code in [200, 202]:
            # Get status
            status_response = client.get(
                f"/api/v2/audit/status/{sample_claim.id}",
                headers=auth_headers
            )
            
            assert status_response.status_code == 200
            data = status_response.json()
            assert data["status"] in [
                "queued",
                "processing",
                "completed",
                "pending"
            ]


@pytest.mark.integration
class TestExternalServiceIntegration:
    """Integration tests for external services."""
    
    @pytest.mark.asyncio
    async def test_web_search_in_fraud_detection(self, sample_audit_state):
        """Test web search integration in fraud detection."""
        from app.agents.nodes import fraud_auditor_node
        
        state = sample_audit_state
        state.claim_data["claimed_amount"] = 15000.00
        
        with patch('app.agents.nodes.web_search_service.search_market_price') as mock_search:
            mock_search.return_value = 3500.00
            
            result = await fraud_auditor_node(state)
            
            assert result is not None
            # Should have detected price inflation
            fraud_signals = result.get("fraud_signals", [])
            assert len(fraud_signals) > 0


@pytest.mark.integration
class TestCeleryIntegration:
    """Integration tests for Celery task queue."""
    
    def test_celery_task_creation(self):
        """Test that Celery tasks can be created."""
        from app.services.celery_tasks import process_claim_audit_task
        
        # Mock task
        with patch('app.services.celery_tasks.celery_app.send_task'):
            # Should not raise
            task = process_claim_audit_task.delay("test-claim-id")
            assert task is not None


@pytest.mark.integration
class TestDataFlow:
    """Test data flow through the system."""
    
    def test_claim_data_preservation(self, db, sample_user, sample_policy):
        """Test that claim data is preserved through workflow."""
        from app.db import crud
        
        original_amount = 7500.00
        claim_data = {
            "user_id": sample_user.id,
            "policy_id": sample_policy.id,
            "claim_number": "CLM-DATA-FLOW-001",
            "incident_description": "Test data flow",
            "claimed_amount": original_amount,
            "status": "pending",
        }
        
        # Create
        claim = crud.create_claim(db, claim_data)
        db.commit()
        
        # Retrieve
        retrieved = crud.get_claim(db, claim.id)
        
        # Verify data integrity
        assert retrieved.claimed_amount == original_amount
        assert retrieved.user_id == sample_user.id
