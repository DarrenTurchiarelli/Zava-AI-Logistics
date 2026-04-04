"""Development environment configuration overrides."""

from src.config.settings import Settings


def apply_development_overrides(settings: Settings) -> Settings:
    """
    Apply development-specific configuration overrides.

    Args:
        settings: Base settings instance

    Returns:
        Modified settings for development environment
    """
    # Enable debug mode in development
    settings.debug_mode = True
    settings.flask.env = "development"

    # Shorter agent timeouts for faster development feedback
    # (This would be used if we had agent timeout settings in Settings)

    return settings
