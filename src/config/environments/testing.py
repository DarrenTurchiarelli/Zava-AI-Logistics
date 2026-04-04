"""Testing environment configuration overrides."""

from src.config.settings import Settings


def apply_testing_overrides(settings: Settings) -> Settings:
    """
    Apply testing-specific configuration overrides.

    Args:
        settings: Base settings instance

    Returns:
        Modified settings for testing environment
    """
    settings.flask.env = "testing"
    settings.debug_mode = False

    # Use test database
    if "test" not in settings.cosmos_db.database_name.lower():
        settings.cosmos_db.database_name = f"{settings.cosmos_db.database_name}_test"

    return settings
