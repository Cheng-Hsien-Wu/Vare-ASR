"""
OpenAI LLM Provider
Uses OpenAI SDK for transcript correction.
"""

from typing import List, Optional

from .base import LLMProvider
from .prompts import get_correction_prompt


class OpenAIProvider(LLMProvider):
    """OpenAI API provider for transcript correction."""
    
    # Available OpenAI models
    AVAILABLE_MODELS = [
        "gpt-5.2-2025-12-11",
        "gpt-5-mini-2025-08-07",
        "gpt-5-2025-08-07",
    ]
    
    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
        """
        self.api_key = api_key
        self.model_name = model
        self._client = None
    
    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def correct_text(self, text: str, language: str = "zh-tw", system_prompt: Optional[str] = None, 
                     temperature: float = 0.3, max_output_tokens: int = 60000, enable_web_search: bool = False,
                     audio_path: Optional[str] = None, use_file_caching: bool = False,
                     status_update_callback: Optional[callable] = None) -> str:
        """
        Correct transcript text using OpenAI.
        
        Args:
            text: The raw transcript text (SRT format content)
            language: Language code for prompt selection
            system_prompt: Optional custom system prompt
            temperature: Optional specific temperature (default 0.3)
            max_output_tokens: Maximum tokens for the output response
            enable_web_search: Enable web search for fact-checking
            audio_path: Optional path to audio file (not supported yet)
            use_file_caching: Enable file context (not supported yet)
        
        Returns:
            Corrected transcript text
        """
        # Use custom prompt if provided, else use default based on language
        final_prompt = system_prompt if system_prompt and system_prompt.strip() else get_correction_prompt(language)
        client = self._get_client()
        
        if enable_web_search:
            # Use Responses API with web_search tool
            # The model will decide when to search based on the content
            response = client.responses.create(
                model=self.model_name,
                instructions=final_prompt,
                input=text,
                tools=[{"type": "web_search"}],
                tool_choice="auto",
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            return response.output_text
        else:
            # Use standard Chat Completions API
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
        Test if the OpenAI API connection is working.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": "Hello"}
                ],
                max_tokens=5
            )
            return (True, "") if response.choices[0].message.content else (False, "Empty response")
        except Exception as e:
            return (False, str(e))
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available OpenAI models.
        
        Returns:
            List of model names
        """
        return self.AVAILABLE_MODELS
    
    @property
    def provider_name(self) -> str:
        return "OpenAI"
