"""
Ollama / LMStudio LLM Provider
Uses OpenAI-compatible API for local LLM transcript correction.
Supports:
  - Ollama (default port 11434)
  - LMStudio (default port 1234)
"""

from typing import List, Optional
from openai import OpenAI

from .base import LLMProvider
from .prompts import get_correction_prompt


class OllamaProvider(LLMProvider):
    """Local LLM provider via OpenAI-compatible API (Ollama, LMStudio)."""
    
    # Common local models (user can also use custom model names)
    AVAILABLE_MODELS = [
        "llama3",
        "llama3.2",
        "qwen2.5",
        "mistral",
        "gemma2",
    ]
    
    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3") -> None:
        """
        Initialize Ollama/LMStudio provider.
        
        Args:
            base_url: API base URL (default: http://localhost:11434/v1 for Ollama)
            model: Model name (default: llama3)
        """
        # Ensure base_url ends with /v1 to be compatible with OpenAI SDK limitations
        base_url = base_url.rstrip('/')
        if not base_url.endswith("/v1"):
            base_url += "/v1"
            
        self.base_url = base_url
        self.model_name = model
        self._client = None
    
    def _get_client(self):
        """Lazy-load the OpenAI-compatible client."""
        if self._client is None:
            # OpenAI SDK works with any OpenAI-compatible endpoint
            self._client = OpenAI(
                base_url=self.base_url,
                api_key="ollama"  # Local LLMs don't require API key, but SDK requires non-empty string
            )
        return self._client
    
    def correct_text(self, text: str, language: str = "zh-tw", system_prompt: Optional[str] = None, 
                     temperature: float = 0.3, max_output_tokens: int = 60000, enable_web_search: bool = False,
                     audio_path: Optional[str] = None,
                     status_update_callback: Optional[callable] = None) -> str:
        """
        Correct transcript text using local LLM.
        
        Args:
            text: The raw transcript text (SRT format content)
            language: Language code for prompt selection
            system_prompt: Optional custom system prompt
            temperature: Optional specific temperature (default 0.3)
            max_output_tokens: Maximum tokens for the output response
            enable_web_search: Not supported for local models (ignored)
            audio_path: Ignored for local models
        
        Returns:
            Corrected transcript text
        """
        # Note: enable_web_search is ignored for local models as they don't support web access
        final_prompt = system_prompt if system_prompt and system_prompt.strip() else get_correction_prompt(language)
        client = self._get_client()
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": text}
            ],
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        
        return response.choices[0].message.content
    
    def verify_connection(self) -> tuple[bool, str]:
        """
        Test if the local LLM API is accessible.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": "Hi"}
                ],
                max_tokens=5
            )
            return (True, "") if response.choices[0].message.content else (False, "Empty response")
        except Exception as e:
            return (False, str(e))
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available models from the local server.
        
        Returns:
            List of model names
        """
        try:
            client = self._get_client()
            models = client.models.list()
            return [model.id for model in models.data]
        except Exception as e:
            # Fallback to static list if API fails
            return self.AVAILABLE_MODELS
    
    @property
    def provider_name(self) -> str:
        return "Ollama (Local)"
