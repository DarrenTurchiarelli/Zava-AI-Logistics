"""
Centralized Configuration Management with Pydantic

This module provides type-safe, validated configuration for the entire application.
Uses Pydantic v2 for automatic environment variable loading and validation.

Usage:
    from src.config.settings import get_settings

    settings = get_settings()
    endpoint = settings.cosmos_db.endpoint
    agent_id = settings.azure_ai.customer_service_agent_id
"""

import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureAISettings(BaseSettings):
    """Azure AI Foundry and OpenAI configuration."""

    project_endpoint: str = Field(..., description="Azure AI project endpoint URL")
    model_deployment_name: str = Field(default="gpt-4o", description="OpenAI model deployment name")

    # Agent IDs - all required for full functionality
    customer_service_agent_id: str = Field(..., description="Customer Service Agent ID")
    fraud_risk_agent_id: str = Field(..., description="Fraud Detection Agent ID")
    identity_agent_id: str = Field(..., description="Identity Verification Agent ID")
    dispatcher_agent_id: str = Field(..., description="Dispatcher Agent ID")
    parcel_intake_agent_id: str = Field(..., description="Parcel Intake Agent ID")
    sorting_facility_agent_id: str = Field(..., description="Sorting Facility Agent ID")
    delivery_coordination_agent_id: str = Field(..., description="Delivery Coordination Agent ID")
    optimization_agent_id: str = Field(..., description="Optimization Agent ID")
    driver_agent_id: Optional[str] = Field(default=None, description="Driver Agent ID (optional)")

    @field_validator("project_endpoint")
    @classmethod
    def validate_project_endpoint(cls, v: str) -> str:
        """Validate Azure AI project endpoint format."""
        if not v.startswith("https://"):
            raise ValueError("Project endpoint must start with https://")
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_prefix="AZURE_AI_", case_sensitive=False)


class CosmosDBSettings(BaseSettings):
    """Azure Cosmos DB configuration."""

    endpoint: str = Field(..., description="Cosmos DB endpoint URL")
    database_name: str = Field(default="logisticstracking", description="Database name")
    use_managed_identity: bool = Field(default=False, description="Use Azure managed identity for auth")

    # Optional: for local development with connection string
    connection_string: Optional[str] = Field(default=None, description="Cosmos DB connection string (local dev)")
    key: Optional[str] = Field(default=None, description="Cosmos DB account key (local dev)")

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate Cosmos DB endpoint format."""
        if not v.startswith("https://"):
            raise ValueError("Cosmos DB endpoint must start with https://")
        return v.rstrip("/")

    model_config = SettingsConfigDict(env_prefix="COSMOS_DB_", case_sensitive=False)


class AzureMapsSettings(BaseSettings):
    """Azure Maps configuration for route optimization."""

    subscription_key: Optional[str] = Field(default=None, description="Azure Maps subscription key")

    @property
    def is_configured(self) -> bool:
        """Check if Azure Maps is properly configured."""
        return self.subscription_key is not None

    model_config = SettingsConfigDict(env_prefix="AZURE_MAPS_", case_sensitive=False)


class AzureSpeechSettings(BaseSettings):
    """Azure Speech Services configuration."""

    resource_id: Optional[str] = Field(default=None, description="Azure Speech resource ID")
    endpoint: Optional[str] = Field(default=None, description="Azure Speech endpoint URL")
    region: str = Field(default="australiaeast", description="Azure region")
    voice: str = Field(default="natasha", description="Voice persona for speech synthesis")

    @property
    def is_configured(self) -> bool:
        """Check if Azure Speech is properly configured."""
        return self.endpoint is not None

    model_config = SettingsConfigDict(env_prefix="AZURE_SPEECH_", case_sensitive=False)


class AzureVisionSettings(BaseSettings):
    """Azure AI Vision configuration for OCR and image analysis."""

    endpoint: Optional[str] = Field(default=None, description="Azure Vision endpoint URL")

    @property
    def is_configured(self) -> bool:
        """Check if Azure Vision is properly configured."""
        return self.endpoint is not None

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Validate Azure Vision endpoint format."""
        if v and not v.startswith("https://"):
            raise ValueError("Vision endpoint must start with https://")
        return v.rstrip("/") if v else None

    model_config = SettingsConfigDict(env_prefix="AZURE_VISION_", case_sensitive=False)


class DepotSettings(BaseSettings):
    """Depot/warehouse addresses by state for route optimization."""

    nsw: str = Field(default="1 Homebush Bay Drive, Rhodes NSW 2138")
    vic: str = Field(default="456 Spencer Street, Melbourne VIC 3000")
    qld: str = Field(default="789 Creek Street, Brisbane QLD 4000")
    sa: str = Field(default="321 North Terrace, Adelaide SA 5000")
    wa: str = Field(default="654 Wellington Street, Perth WA 6000")
    tas: str = Field(default="147 Elizabeth Street, Hobart TAS 7000")
    act: str = Field(default="258 Northbourne Avenue, Canberra ACT 2600")
    nt: str = Field(default="369 Mitchell Street, Darwin NT 0800")

    def get_depot_address(self, state: str) -> str:
        """Get depot address for a given state code."""
        return getattr(self, state.lower(), self.nsw)

    model_config = SettingsConfigDict(env_prefix="DEPOT_", case_sensitive=False)


class FlaskSettings(BaseSettings):
    """Flask web application configuration."""

    secret_key: str = Field(..., description="Flask secret key for sessions")
    env: Literal["development", "production", "testing"] = Field(default="development")
    port: int = Field(default=5000, ge=1000, le=65535)
    host: str = Field(default="0.0.0.0")

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure secret key is sufficiently long."""
        if len(v) < 16:
            raise ValueError("Flask secret key must be at least 16 characters")
        return v

    model_config = SettingsConfigDict(env_prefix="FLASK_", case_sensitive=False)


class Settings(BaseSettings):
    """Root application settings combining all sub-configurations."""

    # Environment
    environment: Literal["development", "production", "testing"] = Field(default="development")
    debug_mode: bool = Field(default=False, description="Enable debug mode")

    # Sub-settings
    azure_ai: AzureAISettings
    cosmos_db: CosmosDBSettings
    azure_maps: AzureMapsSettings = Field(default_factory=AzureMapsSettings)
    azure_speech: AzureSpeechSettings = Field(default_factory=AzureSpeechSettings)
    azure_vision: AzureVisionSettings = Field(default_factory=AzureVisionSettings)
    depot: DepotSettings = Field(default_factory=DepotSettings)
    flask: FlaskSettings

    # Python configuration
    pythonwarnings: str = Field(default="ignore::ResourceWarning", description="Python warnings filter")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == "testing"

    def validate_required_services(self) -> list[str]:
        """
        Validate all required services are configured.

        Returns:
            List of missing configuration items (empty if all good).
        """
        missing = []

        # Core services (always required)
        if not self.azure_ai.project_endpoint:
            missing.append("AZURE_AI_PROJECT_ENDPOINT")
        if not self.cosmos_db.endpoint:
            missing.append("COSMOS_DB_ENDPOINT")

        return missing

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra environment variables
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings (singleton pattern).

    Settings are cached after first load for performance.
    In testing, clear the cache with get_settings.cache_clear().

    Returns:
        Validated Settings instance.

    Raises:
        ValidationError: If required environment variables are missing or invalid.
    """
    return Settings()


def validate_settings() -> None:
    """
    Validate settings and print configuration status.

    Useful for startup checks and deployment verification.
    """
    try:
        settings = get_settings()

        print("=" * 80)
        print("CONFIGURATION STATUS")
        print("=" * 80)

        print(f"Environment: {settings.environment}")
        print(f"Debug Mode: {settings.debug_mode}")
        print()

        print("Azure AI Foundry:")
        print(f"  ✓ Project Endpoint: {settings.azure_ai.project_endpoint[:50]}...")
        print(f"  ✓ Model Deployment: {settings.azure_ai.model_deployment_name}")
        print(f"  ✓ Agents Configured: 8/8")
        print()

        print("Azure Cosmos DB:")
        print(f"  ✓ Endpoint: {settings.cosmos_db.endpoint[:50]}...")
        print(f"  ✓ Database: {settings.cosmos_db.database_name}")
        print(f"  ✓ Auth Method: {'Managed Identity' if settings.cosmos_db.use_managed_identity else 'Key/Connection String'}")
        print()

        print("Optional Services:")
        print(f"  Azure Maps: {'✓ Configured' if settings.azure_maps.is_configured else '○ Not Configured'}")
        print(f"  Azure Speech: {'✓ Configured' if settings.azure_speech.is_configured else '○ Not Configured'}")
        print(f"  Azure Vision: {'✓ Configured' if settings.azure_vision.is_configured else '○ Not Configured'}")
        print()

        missing = settings.validate_required_services()
        if missing:
            print("⚠ MISSING REQUIRED CONFIGURATION:")
            for item in missing:
                print(f"  - {item}")
            print()
        else:
            print("✓ All required services configured")
            print()

        print("=" * 80)

    except Exception as e:
        print(f"❌ Configuration Error: {e}")
        raise


if __name__ == "__main__":
    # Allow running this module directly for configuration validation
    validate_settings()
