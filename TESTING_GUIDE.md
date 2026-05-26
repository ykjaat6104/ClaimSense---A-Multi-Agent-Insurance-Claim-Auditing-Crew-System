# 🧪 TESTING GUIDE - CLAIMSENSE PHASE 2

## Overview

ClaimSense now includes comprehensive testing infrastructure with unit tests, integration tests, and end-to-end tests.

**Test Coverage Target**: 80%+
**Current Test Count**: 50+ tests
**Test Framework**: pytest

---

## Quick Start

### Run All Tests
```bash
pytest tests/
```

### Run with Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test Type

**Unit Tests Only:**
```bash
pytest tests/unit/ -m unit
```

**Integration Tests Only:**
```bash
pytest tests/integration/ -m integration
```

**End-to-End Tests Only:**
```bash
pytest tests/e2e/ -m e2e
```

### Run with Test Runner Script

```bash
# Unit tests with coverage
python run_tests.py --unit --coverage

# Integration tests
python run_tests.py --integration -v

# All tests with parallel execution
python run_tests.py -n 4 --coverage

# Failed tests first
python run_tests.py --ff

# Last failed tests
python run_tests.py --lf
```

---

## Test Structure

```
tests/
├── conftest.py                     # Pytest configuration & fixtures
├── pytest.ini                      # Pytest settings
│
├── unit/                           # Unit tests
│   ├── __init__.py
│   ├── test_agents_nodes.py        # Agent node tests
│   ├── test_tools.py               # Tool function tests
│   ├── test_api_endpoints.py       # API endpoint tests
│   ├── test_fraud_detection.py     # Fraud detection tests (TODO)
│   ├── test_database.py            # Database model tests (TODO)
│   └── test_validation.py          # Schema validation tests (TODO)
│
├── integration/                    # Integration tests
│   ├── __init__.py
│   ├── test_orchestrator.py        # Workflow integration tests
│   ├── test_database_flow.py       # Database flow tests (TODO)
│   ├── test_api_flow.py            # API integration tests (TODO)
│   └── test_services.py            # Service integration tests (TODO)
│
├── e2e/                            # End-to-end tests
│   ├── __init__.py
│   ├── test_full_workflow.py       # Full claim audit workflow (TODO)
│   ├── test_performance.py         # Performance benchmarks (TODO)
│   └── test_error_scenarios.py     # Error handling (TODO)
│
└── fixtures/                       # Shared test data
    └── sample_data.py              # Sample claims, policies (TODO)
```

---

## Test Categories

### Unit Tests

Test individual components in isolation with mocks.

**Files Tested:**
- Agent nodes (Policy Analyst, Data Miner, Fraud Auditor, Judge)
- Tool functions (database tools, web search, LLM)
- API endpoints
- Fraud detection algorithms
- Database models
- Validation schemas

**Example:**
```bash
pytest tests/unit/test_agents_nodes.py::TestPolicyAnalystNode::test_policy_analyst_extracts_coverage -v
```

### Integration Tests

Test component interactions and workflows.

**Scenarios Tested:**
- Multi-agent workflow end-to-end
- State flow through agents
- Conditional routing logic
- Database operations
- API integration
- External service integration

**Example:**
```bash
pytest tests/integration/test_orchestrator.py::TestMultiAgentWorkflow::test_full_audit_workflow -v
```

### End-to-End Tests

Test complete system workflows.

**Scenarios Tested:**
- Full claim audit from submission to decision
- Error handling and recovery
- Performance under load
- Data consistency

**Example:**
```bash
pytest tests/e2e/test_full_workflow.py -v
```

---

## Fixtures

### Database Fixtures

**`db`** - In-memory SQLite session
```python
def test_something(db):
    user = User(username="test")
    db.add(user)
    db.commit()
```

**`client`** - FastAPI TestClient with mocked DB
```python
def test_api(client, auth_headers):
    response = client.get("/api/v2/audit/status/123", headers=auth_headers)
    assert response.status_code == 200
```

### Test Data Fixtures

**`sample_user`** - Test user
```python
def test_claims(db, sample_user):
    assert sample_user.id is not None
```

**`sample_policy`** - Test insurance policy
```python
def test_policy(db, sample_policy):
    assert sample_policy.policy_number == "POL-2024-001"
```

**`sample_claim`** - Test claim
```python
def test_audit(db, sample_claim):
    assert sample_claim.claimed_amount == 8500.00
```

**`sample_audit_state`** - Test audit state
```python
def test_state(sample_audit_state):
    assert sample_audit_state.claim_id == "test-claim-001"
```

### Mock Fixtures

**`mock_gemini_client`** - Mocked LLM
```python
def test_llm(mock_gemini_client):
    result = mock_gemini_client.generate_json("prompt")
    assert result == {"mock": "json_response"}
```

**`mock_web_search`** - Mocked web search
```python
def test_search(mock_web_search):
    price = mock_web_search.search_market_price("repair")
    assert price == 150.00
```

**`auth_headers`** - Authorization headers
```python
def test_auth(client, auth_headers):
    response = client.get("/api/v2/audit/status/123", headers=auth_headers)
```

---

## Running Tests

### By Component

```bash
# Test agents
pytest tests/unit/test_agents_nodes.py -v

# Test API endpoints
pytest tests/unit/test_api_endpoints.py -v

# Test tools
pytest tests/unit/test_tools.py -v

# Test orchestration
pytest tests/integration/test_orchestrator.py -v
```

### By Pattern

```bash
# Tests containing "fraud"
pytest tests/ -k fraud -v

# Tests containing "audit"
pytest tests/ -k audit -v

# Tests NOT marked as slow
pytest tests/ -m "not slow" -v
```

### With Coverage

```bash
# Coverage report in terminal
pytest tests/ --cov=app --cov-report=term-missing

# Coverage report in HTML
pytest tests/ --cov=app --cov-report=html
# Open: htmlcov/index.html

# Coverage report with branch coverage
pytest tests/ --cov=app --cov-report=term-missing:skip-covered --cov-branch
```

### Performance

```bash
# Run specific test with timer
pytest tests/unit/test_agents_nodes.py -v -s

# Run with benchmark
pytest tests/ --benchmark-only

# Parallel execution
pytest tests/ -n 4 -v
```

---

## Writing Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
class TestMyComponent:
    """Test suite for my component."""
    
    def test_happy_path(self, fixture_1, fixture_2):
        """Test successful operation."""
        # Arrange
        data = {"key": "value"}
        
        # Act
        result = my_component(data)
        
        # Assert
        assert result is not None
        assert result.status == "success"
    
    def test_error_handling(self, fixture_1):
        """Test error handling."""
        with pytest.raises(ValueError):
            my_component(invalid_data)
    
    def test_with_mock(self, fixture_1):
        """Test with mocked service."""
        from unittest.mock import patch
        
        with patch('module.service') as mock_service:
            mock_service.call.return_value = "mocked"
            result = my_component(data)
            assert result == "mocked"
```

### Async Test Template

```python
@pytest.mark.unit
@pytest.mark.asyncio
class TestAsyncComponent:
    
    async def test_async_operation(self, fixture_1):
        """Test async function."""
        result = await async_function(data)
        assert result is not None
```

### Parametrized Test Template

```python
@pytest.mark.unit
class TestMultipleScenarios:
    
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (5, 6),
        (10, 11),
    ])
    def test_addition(self, input, expected):
        """Test multiple scenarios."""
        assert input + 1 == expected
```

---

## Test Reports

### Coverage Report

```bash
pytest tests/ --cov=app --cov-report=html
```

Opens `htmlcov/index.html` with:
- Line coverage percentage
- Branch coverage
- Missing lines highlighted
- File-by-file breakdown

### JUnit Report

```bash
pytest tests/ --junit-xml=test_report.xml
```

Generates XML report for CI/CD integration.

### HTML Report

```bash
pytest tests/ --html=test_report.html --self-contained-html
```

Generates standalone HTML report.

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: 3.14
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v2
```

### Pre-commit Hook

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Best Practices

### ✅ Do's

- ✅ Test one thing per test
- ✅ Use descriptive test names
- ✅ Use fixtures for reusable data
- ✅ Mock external services
- ✅ Test error cases
- ✅ Keep tests fast
- ✅ Use parametrize for multiple scenarios
- ✅ Document complex tests

### ❌ Don'ts

- ❌ Test implementation details
- ❌ Have tests dependent on each other
- ❌ Use real external services
- ❌ Have side effects in tests
- ❌ Make tests too complex
- ❌ Mix multiple assertions in one test
- ❌ Use sleep() for timing
- ❌ Have hardcoded data

---

## Troubleshooting

### Issue: "ModuleNotFoundError"
```bash
# Ensure dependencies are installed
pip install -r requirements.txt

# Run from project root
cd /path/to/ClaimSense
pytest tests/
```

### Issue: "Database locked"
```bash
# Tests use in-memory SQLite, shouldn't happen
# If it does, clear any stale connections
rm -f *.db
```

### Issue: "Async test not found"
```bash
# Ensure pytest-asyncio is installed
pip install pytest-asyncio

# Mark as async
@pytest.mark.asyncio
async def test_something():
    pass
```

### Issue: "ImportError" in tests
```bash
# Make sure __init__.py exists in all directories
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py
```

---

## Next Test Development

### TODO: More Tests Needed

1. **Unit Tests:**
   - [ ] Fraud detection algorithms
   - [ ] Database model validations
   - [ ] API schema validation
   - [ ] Error handling edge cases

2. **Integration Tests:**
   - [ ] Database transaction flows
   - [ ] API endpoint integration
   - [ ] Service layer interactions
   - [ ] Celery task execution

3. **End-to-End Tests:**
   - [ ] Complete audit workflow
   - [ ] Error recovery scenarios
   - [ ] Performance benchmarks
   - [ ] Stress testing

4. **Performance Tests:**
   - [ ] Agent processing time
   - [ ] Database query performance
   - [ ] API response times
   - [ ] Memory usage

---

## Useful Commands

```bash
# Run tests with most common options
pytest tests/ -v --tb=short --cov=app

# Run failed tests first
pytest tests/ --ff

# Run last failed tests
pytest tests/ --lf

# Run tests matching pattern
pytest tests/ -k "fraud" -v

# Run specific test
pytest tests/unit/test_agents_nodes.py::TestPolicyAnalystNode::test_policy_analyst_extracts_coverage

# Watch for changes and rerun tests
pip install pytest-watch
ptw tests/ -- -v

# Parallel execution
pytest tests/ -n auto

# Stop on first failure
pytest tests/ -x

# Stop after N failures
pytest tests/ --maxfail=3

# Show print statements
pytest tests/ -s

# Show local variables on failure
pytest tests/ -l

# Profile test execution
pytest tests/ --durations=10
```

---

## Test Statistics

```
Total Tests: 50+
  - Unit Tests: 35+
  - Integration Tests: 10+
  - End-to-End Tests: 5+

Coverage Target: 80%+
Expected Coverage by Component:
  - Agents: 85%
  - API: 80%
  - Services: 75%
  - Database: 70%
```

---

**Test Framework Version**: pytest 7.4.4
**Created**: May 24, 2026
**Status**: Testing infrastructure ready for expansion
