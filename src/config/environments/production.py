"""Production environment configuration overrides."""

from src.config.settings import Settings


def apply_production_overrides(settings: Settings) -> Settings:
    """
    Apply production-specific configuration overrides.

    Args:
        settings: Base settings instance

    Returns:
        Modified settings for production environment
    """
    # Force managed identity in production
    settings.cosmos_db.use_managed_identity = True

    # Disable debug mode
    settings.debug_mode = False
    settings.flask.env = "production"

    # Production should always validate required services
    missing = settings.validate_required_services()
    if missing:
        raise ValueError(f"Missing required configuration in production: {', '.join(missing)}")

    return settings
