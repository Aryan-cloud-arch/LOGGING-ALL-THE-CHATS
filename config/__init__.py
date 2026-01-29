"""
Configuration Package
=====================
Centralized configuration management for Telegram Mirror Bot.

Features:
    ✅ Environment variable support
    ✅ Validation with Pydantic
    ✅ Hot-reload capability
    ✅ Secure credential handling
    ✅ Multi-environment support
    ✅ Configuration versioning
    ✅ Automatic backup
    ✅ Encryption support
"""

from .settings import (
    Settings,
    Environment,
    load_settings,
    save_settings,
    validate_settings,
    get_settings,
    reload_settings,
    ConfigManager,
    ConfigValidator,
    SecureConfig
)

__version__ = "1.0.0"
__author__ = "Your Name"

# Global settings instance
_settings: Settings = None


def init_config(env: str = None) -> Settings:
    """
    Initialize configuration.
    
    Args:
        env: Environment name (development/production/testing)
        
    Returns:
        Settings: Initialized settings instance
    """
    global _settings
    _settings = load_settings(env)
    return _settings


def get_config() -> Settings:
    """
    Get current configuration.
    
    Returns:
        Settings: Current settings instance
    """
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


__all__ = [
    "Settings",
    "Environment",
    "load_settings",
    "save_settings",
    "validate_settings",
    "get_settings",
    "reload_settings",
    "ConfigManager",
    "ConfigValidator",
    "SecureConfig",
    "init_config",
    "get_config"
]
