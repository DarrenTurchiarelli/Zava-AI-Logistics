"""
Pytest Configuration and Shared Fixtures
Provides test fixtures for database mocking, async support, and test data
"""
import asyncio
import os
import pytest
from typing import AsyncGenerator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Set test environment variables
os.environ['COSMOS_DB_ENDPOINT'] = 'https://test-account.documents.azure.com:443/'
os.environ['COSMOS_DB_DATABASE_NAME'] = 'test_logistics'
os.environ['USE_MANAGED_IDENTITY'] = 'false'
os.environ['FLASK_SECRET_KEY'] = 'test-secret-key'


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_cosmos_client():
    """Mock Cosmos DB client for testing"""
    mock_client = MagicMock()
    mock_database = MagicMock()
    mock_container = MagicMock()
    
    # Setup mock chain
    mock_client.get_database_client.return_value = mock_database
    mock_database.get_container_client.return_value = mock_container
    
    # Mock async methods
    mock_container.create_item = AsyncMock()
    mock_container.upsert_item = AsyncMock()
    mock_container.query_items = MagicMock()
    mock_container.read_item = AsyncMock()
    mock_container.delete_item = AsyncMock()
    
    return mock_client


@pytest.fixture
def sample_parcel_data() -> Dict[str, Any]:
    """Sample parcel data for testing"""
    return {
        'id': 'test-parcel-001',
        'barcode': 'BC123456789ABC',
        'tracking_number': 'DT1234567890',
        'sender_name': 'John Smith',
        'sender_address': '123 Sender St, Sydney NSW 2000',
        'sender_phone': '+61400111222',
        'recipient_name': 'Jane Doe',
        'recipient_address': '456 Recipient Ave, Melbourne VIC 3000',
        'recipient_phone': '+61400333444',
        'destination_postcode': '3000',
        'destination_state': 'VIC',
        'destination_city': 'Melbourne',
        'service_type': 'express',
        'weight': 2.5,
        'dimensions': '30x20x15cm',
        'declared_value': 150.0,
        'store_location': 'Sydney_Central',
        'current_location': 'Sydney_Central',
        'current_status': 'registered',
        'registration_timestamp': datetime.now(timezone.utc).isoformat(),
        'delivery_attempts': 0,
        'is_delivered': False,
        'fraud_risk_score': 5,
        'requires_approval': False,
        'lodgement_photos': [],
        'delivery_photos': [],
        'created_at': datetime.now(timezone.utc).isoformat(),
        'updated_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_manifest_data() -> Dict[str, Any]:
    """Sample manifest data for testing"""
    return {
        'id': 'test-manifest-001',
        'manifest_id': 'MAN20240101001',
        'driver_id': 'driver001',
        'driver_name': 'Test Driver',
        'date': '2024-01-01',
        'status': 'pending',
        'route_sequence': [],
        'total_parcels': 0,
        'completed_parcels': 0,
        'created_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_approval_data() -> Dict[str, Any]:
    """Sample approval request data for testing"""
    return {
        'id': 'test-approval-001',
        'parcel_id': 'test-parcel-001',
        'tracking_number': 'DT1234567890',
        'request_reason': 'High value shipment',
        'risk_score': 65,
        'status': 'pending',
        'requested_by': 'system',
        'requested_at': datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def mock_parcel_repository(mock_cosmos_client):
    """Mock ParcelRepository for testing"""
    from src.domain.repositories.parcel_repository import ParcelRepository
    
    with patch.object(ParcelRepository, '__init__', lambda x: None):
        repo = ParcelRepository.__new__(ParcelRepository)
        repo.container = mock_cosmos_client.get_database_client().get_container_client()
        
        # Mock repository methods
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_tracking_number = AsyncMock()
        repo.update = AsyncMock()
        repo.delete = AsyncMock()
        repo.find_by_status = AsyncMock()
        
        yield repo


@pytest.fixture
def mock_ai_agent():
    """Mock Azure AI agent responses"""
    async def mock_agent_response(*args, **kwargs):
        return {
            'success': True,
            'response': 'Mock agent response',
            'recommendations': ['Test recommendation'],
            'risk_assessment': 'Low risk',
        }
    
    with patch('agents.base.call_azure_agent', new=AsyncMock(side_effect=mock_agent_response)):
        yield


@pytest.fixture
def flask_app():
    """Create Flask test application"""
    from src.interfaces.web.app import create_app
    
    app = create_app({'TESTING': True})
    app.config['WTF_CSRF_ENABLED'] = False
    
    return app


@pytest.fixture
def flask_client(flask_app):
    """Create Flask test client"""
    return flask_app.test_client()


@pytest.fixture
def authenticated_client(flask_client):
    """Flask client with authenticated session"""
    with flask_client.session_transaction() as sess:
        sess['user'] = 'testuser'
        sess['role'] = 'admin'
    
    return flask_client
