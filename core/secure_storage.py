"""
Secure Storage Module
Uses OS-level credential storage (keyring) for sensitive data like API keys.
Falls back to in-memory storage if keyring is unavailable.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Service name for keyring (app identity)
SERVICE_NAME = "Vare"

# Mapping of provider names to keyring key names
API_KEY_NAMES = {
    "gemini": "gemini_api_key",
    "openai": "openai_api_key",
    "claude": "claude_api_key",
    "ollama": "ollama_api_key",  # Usually not needed, but for consistency
}

# Fallback in-memory storage (used if keyring unavailable)
_memory_storage: dict = {}
_keyring_available: bool = False

try:
    import keyring
    # Test if keyring backend is functional
    keyring.get_keyring()
    _keyring_available = True
    logger.info("Keyring backend available for secure storage")
except Exception as e:
    logger.warning(f"Keyring unavailable, using in-memory fallback: {e}")


def get_api_key(provider: str) -> str:
    """
    Retrieve API key for a specific LLM provider from secure storage.
    
    Args:
        provider: Provider name (gemini, openai, claude, ollama)
    
    Returns:
        API key string, or empty string if not found
    """
    key_name = API_KEY_NAMES.get(provider, f"{provider}_api_key")
    
    if _keyring_available:
        try:
            value = keyring.get_password(SERVICE_NAME, key_name)
            return value or ""
        except Exception as e:
            logger.warning(f"Failed to get key from keyring: {e}")
            return _memory_storage.get(key_name, "")
    else:
        return _memory_storage.get(key_name, "")


def set_api_key(provider: str, value: str) -> bool:
    """
    Store API key for a specific LLM provider in secure storage.
    
    Args:
        provider: Provider name (gemini, openai, claude, ollama)
        value: API key value (empty string to delete)
    
    Returns:
        True if successful, False otherwise
    """
    key_name = API_KEY_NAMES.get(provider, f"{provider}_api_key")
    
    if _keyring_available:
        try:
            if value:
                keyring.set_password(SERVICE_NAME, key_name, value)
            else:
                # Delete the key if value is empty
                try:
                    keyring.delete_password(SERVICE_NAME, key_name)
                except keyring.errors.PasswordDeleteError:
                    pass  # Key didn't exist, that's fine
            return True
        except Exception as e:
            logger.warning(f"Failed to set key in keyring: {e}")
            # Fall through to memory storage
    
    # Fallback to memory storage
    if value:
        _memory_storage[key_name] = value
    elif key_name in _memory_storage:
        del _memory_storage[key_name]
    return True


def migrate_from_settings(settings_dict: dict) -> bool:
    """
    Migrate API key from old settings.json format to secure storage.
    Called once during app startup.
    
    Args:
        settings_dict: Dictionary containing old settings
    
    Returns:
        True if migration occurred, False otherwise
    """
    old_key = settings_dict.get("llm_api_key", "")
    provider = settings_dict.get("llm_provider", "gemini")
    
    if old_key:
        logger.info(f"Migrating API key for {provider} to secure storage")
        set_api_key(provider, old_key)
        return True
    return False


def is_keyring_available() -> bool:
    """Check if secure keyring storage is available."""
    return _keyring_available
