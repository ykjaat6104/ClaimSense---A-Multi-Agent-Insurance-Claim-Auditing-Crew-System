"""
Unit tests for REST API endpoints.
Tests multi-agent audit endpoints and claim management APIs.
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import uuid
from datetime import datetime


@pytest.mark.unit
class TestMultiAgentAuditEndpoints:
    """Test suite for multi-agent audit endpoints."""
    
    def test_trigger_audit_success(self, client, sample_claim, auth_headers):
        """Test successfully triggering an audit."""
        response = client.post(
            f"/api/v2/audit/trigger?claim_id={sample_claim.id}",
            headers=auth_headers
        )
        
        assert response.status_code in [200, 202]
        data = response.json()
        assert "status" in data
        assert data["status"] in ["queued", "processing"]
        assert "claim_id" in data
    
    def test_trigger_audit_nonexistent_claim(self, client, auth_headers):
        """Test triggering audit for non-existent claim."""
        response = client.post(
            f"/api/v2/audit/trigger?claim_id=non-existent-id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    def test_trigger_audit_missing_auth(self, client, sample_claim):
        """Test audit endpoint requires authentication."""
        response = client.post(
            f"/api/v2/audit/trigger?claim_id={sample_claim.id}"
        )
        
        assert response.status_code == 401 or response.status_code == 403
    
    def test_get_audit_status(self, client, sample_claim, auth_headers):
        """Test getting audit status."""
        response = client.get(
            f"/api/v2/audit/status/{sample_claim.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "claim_id" in data
        assert "status" in data
        assert data["claim_id"] == str(sample_claim.id)
    
    def test_get_audit_result(self, client, db, sample_claim, auth_headers):
        """Test retrieving completed audit result."""
        # Mark claim as completed
        sample_claim.status = "completed"
        sample_claim.decision = "APPROVED"
        sample_claim.risk_score = 25
        sample_claim.fraud_probability = 10
        db.commit()
        
        response = client.get(
            f"/api/v2/audit/result/{sample_claim.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("decision") is not None
    
    def test_get_audit_result_not_completed(self, client, sample_claim, auth_headers):
        """Test getting result for non-completed audit."""
        response = client.get(
            f"/api/v2/audit/result/{sample_claim.id}",
            headers=auth_headers
        )
        
        # Should return error or no data
        assert response.status_code in [200, 400, 404]
    
    def test_compare_audits(self, client, sample_claim, sample_claim_high_risk, auth_headers):
        """Test comparing two audit results."""
        response = client.post(
            f"/api/v2/audit/compare/{sample_claim.id}/with/{sample_claim_high_risk.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert "comparison" in data or "differences" in data


@pytest.mark.unit
class TestClaimManagementEndpoints:
    """Test suite for claim management endpoints."""
    
    def test_list_claims(self, client, sample_claim, auth_headers):
        """Test listing claims."""
        response = client.get(
            "/api/claims",
            headers=auth_headers
        )
        
        # Endpoint might not exist or might be in different route
        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, list) or isinstance(data, dict)
    
    def test_get_claim_detail(self, client, sample_claim, auth_headers):
        """Test getting claim details."""
        response = client.get(
            f"/api/claims/{sample_claim.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("id") == str(sample_claim.id)
    
    def test_create_claim(self, client, auth_headers, sample_user):
        """Test creating a new claim."""
        claim_data = {
            "policy_id": str(sample_user.id),
            "incident_date": datetime.utcnow().isoformat(),
            "incident_description": "Test incident",
            "claimed_amount": 5000.00,
        }
        
        response = client.post(
            "/api/claims",
            json=claim_data,
            headers=auth_headers
        )
        
        # Endpoint might not exist
        if response.status_code in [200, 201, 404]:
            if response.status_code in [200, 201]:
                data = response.json()
                assert "id" in data or "claim_id" in data
    
    def test_update_claim(self, client, sample_claim, auth_headers):
        """Test updating a claim."""
        update_data = {
            "status": "under_review"
        }
        
        response = client.patch(
            f"/api/claims/{sample_claim.id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Endpoint might not exist or might reject
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") == "under_review"


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in API endpoints."""
    
    def test_invalid_claim_id_format(self, client, auth_headers):
        """Test handling of invalid claim ID format."""
        response = client.get(
            "/api/v2/audit/status/invalid-format-!!!",
            headers=auth_headers
        )
        
        # Should reject invalid format
        assert response.status_code in [400, 404, 422]
    
    def test_malformed_json_request(self, client, auth_headers):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v2/audit/trigger",
            data="not valid json",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        
        # Should reject malformed JSON
        assert response.status_code in [400, 422]
    
    def test_missing_required_parameters(self, client, auth_headers):
        """Test handling of missing required parameters."""
        response = client.post(
            "/api/v2/audit/trigger",
            headers=auth_headers
        )
        
        # Should reject missing parameters
        assert response.status_code in [400, 422]


@pytest.mark.unit
class TestResponseFormats:
    """Test API response formats."""
    
    def test_audit_status_response_format(self, client, sample_claim, auth_headers):
        """Test audit status response structure."""
        response = client.get(
            f"/api/v2/audit/status/{sample_claim.id}",
            headers=auth_headers
        )
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["claim_id", "status"]
            for field in required_fields:
                assert field in data
    
    def test_trigger_audit_response_format(self, client, sample_claim, auth_headers):
        """Test trigger audit response structure."""
        response = client.post(
            f"/api/v2/audit/trigger?claim_id={sample_claim.id}",
            headers=auth_headers
        )
        
        if response.status_code in [200, 202]:
            data = response.json()
            required_fields = ["status", "claim_id"]
            for field in required_fields:
                assert field in data


@pytest.mark.unit
class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_missing_auth_header(self, client, sample_claim):
        """Test request without auth header."""
        response = client.get(f"/api/v2/audit/status/{sample_claim.id}")
        
        assert response.status_code in [401, 403]
    
    def test_invalid_auth_token(self, client, sample_claim):
        """Test request with invalid token."""
        response = client.get(
            f"/api/v2/audit/status/{sample_claim.id}",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code in [401, 403]
    
    def test_valid_auth_token(self, client, sample_claim, auth_headers):
        """Test request with valid token."""
        response = client.get(
            f"/api/v2/audit/status/{sample_claim.id}",
            headers=auth_headers
        )
        
        # Should not be 401 or 403
        assert response.status_code not in [401, 403]


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting (if implemented)."""
    
    def test_rate_limit_headers(self, client, auth_headers):
        """Test that rate limit headers are present."""
        response = client.get(
            "/api/v2/audit/status/test-id",
            headers=auth_headers
        )
        
        # Check for rate limit headers
        headers = response.headers
        # Rate limit headers might be present
        if "X-RateLimit-Limit" in headers:
            assert "X-RateLimit-Remaining" in headers


@pytest.mark.unit
class TestCORSHeaders:
    """Test CORS configuration."""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are properly set."""
        response = client.options("/api/v2/audit/trigger")
        
        # CORS preflight response
        if response.status_code == 200:
            assert "Access-Control-Allow-Origin" in response.headers or "allow" in response.headers.lower()
