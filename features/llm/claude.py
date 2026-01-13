"""
Claude LLM Provider
Uses Anthropic SDK for transcript correction.
"""

from typing import List, Optional

from .base import LLMProvider
from .prompts import get_correction_prompt


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API provider for transcript correction."""
    
    # Available Claude models for selection
    AVAILABLE_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-haiku-20240307",
    ]
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514") -> None:
        """
        Initialize Claude provider.
        
        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-sonnet-4-20250514)
        """
        self.api_key = api_key
        self.model_name = model
        self._client = None
    
    def _get_client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    def correct_text(self, text: str, language: str = "zh-tw", system_prompt: Optional[str] = None, 
                     temperature: float = 0.3, max_output_tokens: int = 60000, enable_web_search: bool = False,
                     audio_path: Optional[str] = None, use_file_caching: bool = False,
                     status_update_callback: Optional[callable] = None) -> str:
        """
        Correct transcript text using Claude.
        
        Args:
            text: The raw transcript text (SRT format content)
            language: Language code for prompt selection
            system_prompt: Optional custom system prompt
            temperature: Optional specific temperature (default 0.3)
            max_output_tokens: Maximum tokens for the output response
            enable_web_search: Enable web search for fact-checking
            audio_path: Optional path to audio file (not supported/ignored)
            use_file_caching: Enable prompt caching (todo)
        
        Returns:
            Corrected transcript text
        """
        # Use custom prompt if provided, else use default based on language
        final_prompt = system_prompt if system_prompt and system_prompt.strip() else get_correction_prompt(language)
        client = self._get_client()
        
        # Build request params
        request_params = {
            "model": self.model_name,
            "max_tokens": max_output_tokens,
            "system": final_prompt,
            "messages": [{"role": "user", "content": text}],
            "temperature": temperature,
        }
        
        if enable_web_search:
            # Enable Claude web search tool
            # Note: Requires web search to be enabled in Anthropic Console
            request_params["tools"] = [{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }]
        
        message = client.messages.create(**request_params)
        
        # Extract text from response (robust parsing across blocks including tool results)
        if message.content:
            return "".join([block.text for block in message.content if hasattr(block, 'text') and block.text])
        return ""
    
    def verify_connection(self) -> tuple[bool, str]:
        """
        Test if the Claude API connection is working.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            client = self._get_client()
            message = client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
            )
            # Check content valid
            has_text = any(block.type == "text" and block.text for block in message.content)
            return (True, "") if has_text else (False, "Empty response")
        except Exception as e:
            return (False, str(e))
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Claude models.
        
        Returns:
            List of model names
        """
        try:
            client = self._get_client()
            # Try to list models (Anthropic API recently added this)
            models = client.models.list()
            # The models iterate
            available = []
            for m in models:
                # Check if it looks like a Claude model
                if "claude" in m.id:
                    available.append(m.id)
            
            if available:
                return sorted(available, reverse=True)
                 
        except Exception as e:
            # Fallback to static list if API fails
            pass
            
        # Fallback to static list
        return self.AVAILABLE_MODELS
    
    @property
    def provider_name(self) -> str:
        return "Claude"
