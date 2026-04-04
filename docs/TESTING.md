# Zava Testing Guide

## Testing Strategy

The Zava platform uses a comprehensive three-tier testing approach:

1. **Unit Tests** - Isolated component testing
2. **Integration Tests** - Multi-component workflows
3. **End-to-End (E2E) Tests** - Full application testing

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── unit/                         # Unit tests (fast, isolated)
│   ├── domain/                  # Domain model tests
│   │   ├── test_parcel_model.py
│   │   ├── test_manifest_model.py
│   │   ├── test_parcel_service.py
│   │   └── test_fraud_service.py
│   ├── application/             # Command/Query tests
│   │   ├── test_register_parcel_command.py
│   │   ├── test_get_parcel_query.py
│   │   └── test_approval_command.py
│   └── infrastructure/          # Infrastructure tests (mocked)
│       ├── test_parcel_repository.py
│       └── test_cosmos_client.py
│
├── integration/                 # Integration tests (DB mocked)
│   ├── test_parcel_workflow.py
│   ├── test_manifest_workflow.py
│   └── test_approval_workflow.py
│
└── e2e/                        # End-to-end tests (full stack)
    ├── test_web_routes.py
    ├── test_chatbot_flow.py
    └── test_driver_workflow.py
```

## Running Tests

### Run All Tests
```bash
pytest tests/
```

### Run Specific Test Levels
```bash
# Unit tests only (fast)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests (slowest)
pytest tests/e2e/
```

### Run Specific Tests
```bash
# Specific file
pytest tests/unit/domain/test_parcel_model.py

# Specific test class
pytest tests/unit/domain/test_parcel_model.py::TestParcelModel

# Specific test case
pytest tests/unit/domain/test_parcel_model.py::TestParcelModel::test_create_parcel_with_required_fields
```

### Verbose Output
```bash
# Show print statements and detailed output
pytest -v -s tests/

# Show coverage
pytest --cov=src --cov-report=term-missing tests/
```

### Generate Coverage Report
```bash
# Terminal report
pytest --cov=src tests/

# HTML report
pytest --cov=src --cov-report=html tests/
# Open htmlcov/index.html

# XML report (for CI/CD)
pytest --cov=src --cov-report=xml tests/
```

## Test Fixtures

### Available Fixtures

#### Database Fixtures
```python
@pytest.fixture
def mock_cosmos_client():
    """Mock Cosmos DB client"""
    # Returns fully mocked CosmosClient
    
@pytest.fixture
def mock_parcel_repository(mock_cosmos_client):
    """Mock ParcelRepository"""
    # Returns mocked repository with CRUD methods
```

#### Sample Data Fixtures
```python
@pytest.fixture
def sample_parcel_data():
    """Complete parcel data dictionary"""
    
@pytest.fixture
def sample_manifest_data():
    """Complete manifest data dictionary"""
    
@pytest.fixture
def sample_approval_data():
    """Complete approval request data"""
```

#### AI Agent Fixtures
```python
@pytest.fixture
def mock_ai_agent():
    """Mock Azure AI agent responses"""
    # Automatically patches agents.base.call_azure_agent
```

#### Flask Fixtures
```python
@pytest.fixture
def flask_app():
    """Flask test application"""
    
@pytest.fixture
def flask_client(flask_app):
    """Flask test client"""
    
@pytest.fixture
def authenticated_client(flask_client):
    """Flask client with authenticated session"""
```

### Using Fixtures

```python
# tests/unit/domain/test_parcel_model.py
def test_create_parcel(sample_parcel_data):
    """Test uses sample_parcel_data fixture"""
    assert sample_parcel_data['tracking_number'].startswith('DT')

# tests/unit/application/test_register_parcel_command.py
@pytest.mark.asyncio
async def test_register_parcel(mock_parcel_repository, mock_ai_agent):
    """Test uses both repository and AI mocks"""
    command = RegisterParcelCommand(mock_parcel_repository)
    result = await command.execute(...)
    assert result is not None
```

## Writing Tests

### Unit Test Template

```python
"""
Unit Tests: <Component Name>
Tests <what is being tested>
"""
import pytest
from unittest.mock import AsyncMock, patch


class Test<ComponentName>:
    """Test <component> functionality"""
    
    def test_basic_functionality(self):
        """Test basic operation"""
        # Arrange
        input_data = "test"
        
        # Act
        result = function_to_test(input_data)
        
        # Assert
        assert result == expected_output
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, mock_dependency):
        """Test async operation"""
        # Arrange
        mock_dependency.method.return_value = "mocked_result"
        
        # Act
        result = await async_function_to_test()
        
        # Assert
        assert mock_dependency.method.called
        assert result == "mocked_result"
```

### Integration Test Template

```python
"""
Integration Tests: <Workflow Name>
Tests end-to-end workflow with multiple components
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class Test<Workflow>Workflow:
    """Test complete <workflow> workflow"""
    
    async def test_full_workflow(
        self, 
        mock_parcel_repository, 
        mock_ai_agent
    ):
        """Test complete workflow from start to finish"""
        # Arrange
        mock_parcel_repository.create.return_value = {'id': 'test'}
        
        # Act
        result = await execute_workflow()
        
        # Assert
        assert mock_parcel_repository.create.called
        assert result['success'] is True
```

### E2E Test Template

```python
"""
End-to-End Tests: <Feature Name>
Tests complete HTTP request/response cycles
"""
import pytest
from unittest.mock import patch, AsyncMock
import json


class Test<Feature>:
    """Test <feature> end-to-end"""
    
    def test_page_loads(self, authenticated_client):
        """Test page is accessible"""
        response = authenticated_client.get('/feature')
        
        assert response.status_code == 200
    
    @patch('module.dependency')
    def test_form_submission(self, mock_dep, authenticated_client):
        """Test form submission workflow"""
        # Arrange
        mock_dep.return_value = {'success': True}
        
        # Act
        response = authenticated_client.post('/feature/submit', data={
            'field1': 'value1',
            'field2': 'value2',
        })
        
        # Assert
        assert response.status_code in [200, 302]
        assert mock_dep.called
```

## Test-Driven Development (TDD)

### TDD Workflow

1. **Write failing test**
   ```python
   def test_calculate_delivery_fee():
       fee = calculate_delivery_fee(weight=5.0, distance=10.0)
       assert fee == 25.0  # Test fails - function doesn't exist
   ```

2. **Implement minimum code**
   ```python
   def calculate_delivery_fee(weight: float, distance: float) -> float:
       return weight * distance / 2  # Simple implementation
   ```

3. **Test passes**
   ```bash
   $ pytest tests/test_delivery_fee.py
   ✓ test_calculate_delivery_fee PASSED
   ```

4. **Refactor**
   ```python
   def calculate_delivery_fee(weight: float, distance: float) -> float:
       """Calculate delivery fee based on weight and distance"""
       base_fee = 10.0
       weight_cost = weight * 2.0
       distance_cost = distance * 0.5
       return base_fee + weight_cost + distance_cost
   ```

5. **Test still passes**
   ```bash
   $ pytest tests/test_delivery_fee.py
   ✓ test_calculate_delivery_fee PASSED
   ```

## Mocking Strategies

### Mocking Database Calls

```python
@pytest.fixture
def mock_parcel_repository():
    """Create mock repository"""
    repo = MagicMock()
    
    # Mock async methods
    repo.create = AsyncMock(return_value={'id': 'test-001'})
    repo.get_by_id = AsyncMock(return_value={'id': 'test-001'})
    repo.update = AsyncMock(return_value={'id': 'test-001', 'updated': True})
    
    return repo


@pytest.mark.asyncio
async def test_with_mock_repo(mock_parcel_repository):
    """Test using mocked repository"""
    result = await mock_parcel_repository.create({'data': 'test'})
    
    assert result['id'] == 'test-001'
    mock_parcel_repository.create.assert_called_once()
```

### Mocking AI Agents

```python
@patch('agents.base.customer_service_agent')
async def test_with_mock_agent(mock_agent):
    """Test with mocked AI agent"""
    # Setup mock response
    mock_agent.return_value = {
        'success': True,
        'response': 'Parcel is out for delivery',
    }
    
    # Call function that uses agent
    result = await process_customer_inquiry('Where is my parcel?')
    
    # Verify
    assert mock_agent.called
    assert result['response'] == 'Parcel is out for delivery'
```

### Mocking External Services

```python
@patch('services.maps_service.AzureMapsService.optimize_route')
async def test_route_optimization(mock_optimize):
    """Test with mocked Azure Maps"""
    # Setup mock
    mock_optimize.return_value = {
        'optimized_sequence': ['stop1', 'stop2', 'stop3'],
        'total_distance_km': 15.5,
    }
    
    # Test
    result = await create_optimized_manifest(['stop1', 'stop2', 'stop3'])
    
    # Verify
    assert len(result['sequence']) == 3
    mock_optimize.assert_called_once()
```

## Testing Best Practices

### DO ✅

1. **Write tests first (TDD)**
   ```python
   # Write test
   def test_validate_postcode():
       assert validate_postcode("2000") is True
       assert validate_postcode("invalid") is False
   
   # Then implement
   def validate_postcode(postcode: str) -> bool:
       return postcode.isdigit() and len(postcode) == 4
   ```

2. **Test one thing per test**
   ```python
   # Good - focused test
   def test_parcel_status_transitions():
       parcel.status = 'registered'
       assert parcel.can_transition_to('at_depot') is True
   
   # Bad - testing multiple things
   def test_parcel_everything():
       parcel.status = 'registered'
       assert parcel.can_transition_to('at_depot') is True
       assert parcel.tracking_number.startswith('DT')
       assert parcel.weight > 0
   ```

3. **Use descriptive test names**
   ```python
   # Good
   def test_high_fraud_risk_triggers_approval_workflow():
       pass
   
   # Bad
   def test_fraud():
       pass
   ```

4. **Arrange-Act-Assert pattern**
   ```python
   def test_create_parcel():
       # Arrange
       parcel_data = {'tracking_number': 'DT123', ...}
       
       # Act
       result = create_parcel(parcel_data)
       
       # Assert
       assert result['success'] is True
   ```

5. **Test edge cases**
   ```python
   def test_postcode_validation_edge_cases():
       # Valid cases
       assert validate_postcode("2000") is True
       assert validate_postcode("9999") is True
       
       # Invalid cases
       assert validate_postcode("") is False
       assert validate_postcode("12345") is False  # Too long
       assert validate_postcode("ABC") is False    # Not numeric
       assert validate_postcode(None) is False     # None
   ```

### DON'T ❌

1. **Don't test implementation details**
   ```python
   # Bad - testing internal variable names
   def test_internal_details():
       assert obj._internal_counter == 5
   
   # Good - testing behavior
   def test_increment_behavior():
       obj.increment()
       assert obj.get_count() == 1
   ```

2. **Don't write tests that depend on each other**
   ```python
   # Bad - test2 depends on test1
   def test1_create_user():
       global user
       user = create_user('test')
   
   def test2_update_user():
       user.name = 'updated'  # Fails if test1 doesn't run
   
   # Good - each test is independent
   def test1_create_user():
       user = create_user('test')
       assert user.name == 'test'
   
   def test2_update_user():
       user = create_user('test')
       user.name = 'updated'
       assert user.name == 'updated'
   ```

3. **Don't use real database in unit tests**
   ```python
   # Bad - hits real database
   def test_create_parcel():
       parcel = create_parcel({'data': 'test'})  # Writes to real DB!
   
   # Good - uses mock
   @patch('repository.create')
   def test_create_parcel(mock_create):
       mock_create.return_value = {'id': 'test'}
       parcel = create_parcel({'data': 'test'})
   ```

4. **Don't ignore test failures**
   ```python
   # Bad - skipping broken tests
   @pytest.mark.skip("TODO: Fix later")
   def test_important_feature():
       pass
   
   # Good - fix the test or remove it
   def test_important_feature():
       result = important_feature()
       assert result is not None
   ```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

## Coverage Goals

### Target Coverage
- **Unit Tests**: 80%+ coverage
- **Integration Tests**: 60%+ coverage
- **E2E Tests**: Critical paths covered

### Running Coverage
```bash
# Generate report
pytest --cov=src --cov-report=term-missing tests/

# View in browser
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

### Coverage Configuration
```ini
# pytest.ini or setup.cfg
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --cov=src
    --cov-report=term-missing
    --cov-report=html
```

## Troubleshooting Tests

### Test Discovery Issues
```bash
# Ensure PYTHONPATH is set
$env:PYTHONPATH="$PWD;$PWD\src"

# Verify pytest can find tests
pytest --collect-only
```

### Async Test Errors
```python
# Error: RuntimeError: Event loop is closed
# Solution: Use pytest-asyncio

import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Mock Not Working
```python
# Error: Mock not being called
# Solution: Patch at point of use, not definition

# Bad - patches where defined
@patch('module_a.function')

# Good - patches where used
@patch('module_b.function')  # module_b imports and uses function
```

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)
- [TDD with Python](https://www.obeythetestinggoat.com/)
