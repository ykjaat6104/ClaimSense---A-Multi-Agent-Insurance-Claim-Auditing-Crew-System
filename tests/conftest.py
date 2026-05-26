"""
Pytest configuration and fixtures for ClaimSense testing.
Provides database fixtures, mock services, and test data generators.
"""

import asyncio
import os
import pytest
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, AsyncMock, patch
import uuid
from datetime import datetime, timedelta

# Import models and configuration
from app.db.models import Base, Claim
from app.db.session import get_session
from app.config import get_settings
from app.agents.state import ClaimAuditState
from app.services import gemini_client
from app.services.web_search import WebSearchService
from fastapi.testclient import TestClient
from app.main import app


# ============================================================
# DATABASE FIXTURES
# ============================================================

@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Create an in-memory SQLite database for testing."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine(test_database_url: str):
    """Create SQLAlchemy engine for tests."""
    engine = create_engine(
        test_database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="session")
def SessionLocal(engine):
    """Create SessionLocal for tests."""
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


@pytest.fixture
def db(SessionLocal) -> Generator[Session, None, None]:
    """Database session fixture for individual tests."""
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def override_get_session(db: Session):
    """Override get_session dependency for FastAPI tests."""
    def _override_get_session():
        yield db
    return _override_get_session


@pytest.fixture
def client(override_get_session):
    """FastAPI TestClient with database override."""
    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# ============================================================
# MOCK SERVICE FIXTURES
# ============================================================

@pytest.fixture
def mock_gemini_client() -> Mock:
    """Mock Gemini LLM client."""
    mock = AsyncMock()
    mock.generate_text.return_value = "Mock LLM response"
    mock.generate_json.return_value = {"mock": "json_response"}
    mock.generate_structured.return_value = {"decision": "approved", "confidence": 0.95}
    return mock


@pytest.fixture
def mock_web_search() -> Mock:
    """Mock web search service."""
    mock = Mock(spec=WebSearchService)
    mock.search_market_price.return_value = 150.00
    mock.search_repair_rates.return_value = [
        {"vendor": "Shop A", "price": 160.00},
        {"vendor": "Shop B", "price": 140.00},
    ]
    mock.verify_vendor.return_value = {"verified": True, "rating": 4.5}
    return mock


@pytest.fixture
def mock_celery() -> Mock:
    """Mock Celery task queue."""
    mock = Mock()
    mock.delay.return_value = Mock(id="task-12345")
    return mock


# ============================================================
# TEST DATA GENERATORS
# ============================================================

@pytest.fixture
def sample_claim(db: Session) -> Claim:
    """Create a sample insurance claim."""
    claim = Claim(
        id=uuid.uuid4(),
        status="pending",
        risk_score=45,
        fraud_probability=15,
        decision="pending",
        structured_claim={
            "claim_number": "CLM-2024-001",
            "claimed_amount": 8500.00,
            "incident_description": "Car accident on highway",
            "incident_date": (datetime.utcnow() - timedelta(days=7)).isoformat(),
        },
        processing_logs=[],
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@pytest.fixture
def sample_claim_high_risk(db: Session) -> Claim:
    """Create a high-risk sample claim."""
    claim = Claim(
        id=uuid.uuid4(),
        status="processing",
        risk_score=85,
        fraud_probability=72,
        decision="pending",
        structured_claim={
            "claim_number": "CLM-2024-002",
            "claimed_amount": 45000.00,
            "incident_description": "Suspicious high-value claim",
            "incident_date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
        },
        processing_logs=["High risk detection"],
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@pytest.fixture
def sample_audit_state() -> ClaimAuditState:
    """Create a sample claim audit state."""
    return ClaimAuditState(
        claim_id="test-claim-001",
        user_id="test-user-001",
        policy_id="test-policy-001",
        claim_data={
            "claim_number": "CLM-2024-TEST",
            "incident_date": "2024-05-01",
            "claimed_amount": 5000.00,
            "incident_description": "Test incident",
        },
        policy_data={
            "policy_number": "POL-2024-TEST",
            "coverage_types": ["collision", "comprehensive"],
            "max_payout": 50000.00,
        },
        extracted_clauses_data={},
        database_alerts=[],
        fraud_signals=[],
        market_price_analysis={},
        suspicious_flags=[],
        decision="",
        risk_score=0,
        fraud_probability=0,
        confidence_score=0.0,
        audit_loop_count=0,
        processing_logs=[],
        mediator_output="",
    )


# ============================================================
# ASYNC TEST FIXTURES
# ============================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_db(SessionLocal) -> AsyncGenerator[Session, None]:
    """Async database session fixture."""
    session = SessionLocal()
    yield session
    session.close()


# ============================================================
# ENVIRONMENT FIXTURES
# ============================================================

@pytest.fixture
def test_env(monkeypatch):
    """Set up test environment variables."""
    test_env_vars = {
        "ENVIRONMENT": "testing",
        "DATABASE_URL": "sqlite:///:memory:",
        "GEMINI_API_KEY": "test-gemini-key",
        "CLAIMSENSE_AUTH_SECRET": "test-secret",
        "DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
    }
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)
    return test_env_vars


# ============================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "async: mark test as async"
    )


@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all mocks after each test."""
    yield
    # Cleanup code here if needed


# ============================================================
# PERFORMANCE TESTING FIXTURES
# ============================================================

@pytest.fixture
def benchmark_timer():
    """Simple timer for benchmarking."""
    class Timer:
        def __enter__(self):
            import time
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            import time
            self.duration = time.time() - self.start
            print(f"\nExecution time: {self.duration:.4f}s")
    
    return Timer()


# ============================================================
# UTILITY FIXTURES
# ============================================================

@pytest.fixture
def auth_headers() -> dict:
    """Generate test authorization headers."""
    return {
        "Authorization": "Bearer test-token-12345",
        "Content-Type": "application/json",
    }


@pytest.fixture
def api_base_url() -> str:
    """Get API base URL for tests."""
    return "http://testserver/api/v2"
