"""
Configuration Management

Type-safe configuration with Pydantic for all environment variables
and application settings.
"""

from src.config.constants import (
    AgentType,
    ApprovalStatus,
    ApprovalType,
    AustralianState,
    CosmosContainer,
    Defaults,
    DocumentType,
    EventType,
    FraudRiskLevel,
    HTTPStatus,
    ManifestStatus,
    ParcelStatus,
    ScanType,
    ServiceType,
    UserRole,
    ValidationPattern,
)
from src.config.settings import Settings, get_settings, validate_settings

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    "validate_settings",
    # Enums
    "ParcelStatus",
    "UserRole",
    "ServiceType",
    "ScanType",
    "ApprovalStatus",
    "ApprovalType",
    "FraudRiskLevel",
    "ManifestStatus",
    "AgentType",
    "DocumentType",
    "EventType",
    "AustralianState",
    "CosmosContainer",
    # Constants
    "HTTPStatus",
    "Defaults",
    "ValidationPattern",
]
