"""
LLM Provider Base Class
Abstract interface for LLM-based transcript correction.
"""

from abc import ABC, abstractmethod
from typing import List, Optional


class LLMProvider(ABC):
    """Abstract base class for LLM providers (Gemini, Ollama, etc.)"""
    
    @abstractmethod
    def correct_text(self, text: str, language: str = "zh-tw", system_prompt: Optional[str] = None, 
                     temperature: float = 0.3, max_output_tokens: int = 8192, enable_web_search: bool = False,
                     audio_path: Optional[str] = None,
                     status_update_callback: Optional[callable] = None) -> str:
        """
        Correct the given transcript text.
        
        Args:
            text: The raw transcript text (SRT format content)
            language: Language code for prompt selection
            system_prompt: Optional custom system prompt
            temperature: Optional specific temperature (default 0.3)
            max_output_tokens: Maximum tokens for the output response
            enable_web_search: Enable web search for fact-checking (default False)
            audio_path: Optional path to audio file for multimodal grounding (default None)
            status_update_callback: Optional callback(str) to update UI status message
        
        Returns:
            Corrected transcript text
        """
        pass
    
    @abstractmethod
    def verify_connection(self) -> tuple[bool, str]:
        """
        Test if the API connection is working.
        
        Returns:
            Tuple of (success, error_message)
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        Get list of available models from the provider.
        
        Returns:
            List of model names/IDs
        """
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name for display."""
        pass
