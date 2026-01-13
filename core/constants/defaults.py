"""
Application Defaults
Single Source of Truth for default configurations.
"""

from core.settings import UserSettings

# LLM Configuration
DEFAULT_LLM_PROVIDER = "gemini" # Valid fallback if settings load fails early
DEFAULT_LLM_MODEL = UserSettings.DEFAULTS["llm_model"]
DEFAULT_LLM_TEMPERATURE = UserSettings.DEFAULTS["llm_temperature"]
DEFAULT_LLM_MAX_TOKENS = 60000
