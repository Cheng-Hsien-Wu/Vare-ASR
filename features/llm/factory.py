"""
LLM Provider Factory
Centralizes provider instantiation for DIP compliance.
"""

from typing import Dict, Any
from .base import LLMProvider


def create_provider(config: Dict[str, Any]) -> LLMProvider:
    """
    Factory function to create LLM provider from config.
    
    Args:
        config: Configuration dictionary containing:
            - llm_provider: 'gemini' or 'ollama'
            - llm_api_key: API key (for Gemini)
            - llm_model: Model name
            - llm_base_url: Base URL (for Ollama)
    
    Returns:
        LLMProvider instance
    
    Raises:
        ValueError: If provider name is unknown
    """
    provider_name = config.get('llm_provider', 'gemini')
    
    # helper to check model or fallback
    def _model(p_name):
        return config.get('llm_model') or get_default_model(p_name)

    if provider_name == 'gemini':
        from .gemini import GeminiProvider
        return GeminiProvider(
            api_key=config.get('llm_api_key', ''),
            model=_model('gemini')
        )
    elif provider_name == 'claude':
        from .claude import ClaudeProvider
        return ClaudeProvider(
            api_key=config.get('llm_api_key', ''),
            model=_model('claude')
        )
    elif provider_name == 'openai':
        from .openai_llm import OpenAIProvider
        return OpenAIProvider(
            api_key=config.get('llm_api_key', ''),
            model=_model('openai')
        )
    elif provider_name == 'ollama':
        from .ollama import OllamaProvider
        return OllamaProvider(
            base_url=config.get('llm_base_url', 'http://localhost:11434/v1'),
            model=_model('ollama')
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}. Supported: gemini, claude, openai, ollama")


def get_provider_models(provider_name: str) -> list:
    """
    Get available models for a provider from the provider class itself.
    This ensures UI stays in sync with provider capabilities (DRY/SOLID).
    
    Args:
        provider_name: Provider identifier ('gemini', 'claude', 'openai', 'ollama')
        
    Returns:
        List of model name strings
    """
    if provider_name == 'gemini':
        from .gemini import GeminiProvider
        return GeminiProvider.AVAILABLE_MODELS
    elif provider_name == 'claude':
        from .claude import ClaudeProvider
        return ClaudeProvider.AVAILABLE_MODELS
    elif provider_name == 'openai':
        from .openai_llm import OpenAIProvider
        return OpenAIProvider.AVAILABLE_MODELS
    elif provider_name == 'ollama':
        from .ollama import OllamaProvider
        return OllamaProvider.AVAILABLE_MODELS
    else:
        return []


def get_default_model(provider_name: str) -> str:
    """
    Get the default model for a provider.
    
    Args:
        provider_name: Provider identifier
        
    Returns:
        Default model name string
    """
    models = get_provider_models(provider_name)
    return models[0] if models else ""
