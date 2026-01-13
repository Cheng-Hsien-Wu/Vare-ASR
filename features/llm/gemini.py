"""
Gemini LLM Provider
Uses Google Gen AI SDK (google-genai) for transcript correction.
"""

from typing import List, Optional

from .base import LLMProvider
from .base import LLMProvider
from .prompts import get_correction_prompt
import os
import time
import tempfile
import logging

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini API provider for transcript correction."""
    
    # Available Gemini models for selection
    AVAILABLE_MODELS = [
        "gemini-3-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
    ]
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.5-flash)
        """
        self.api_key = api_key
        self.model_name = model
        self._client = None
        self._file_cache = {} # Cache for uploaded file objects
    
    def _get_client(self):
        """Lazy-load the Gemini client."""
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
        return self._client
    
    def _upload_and_wait(self, path: str, mime_type: str = None, status_callback: Optional[callable] = None):
        """Upload file to Gemini and wait for it to be active."""
        # Check cache first
        if path in self._file_cache:
            logger.info(f"Using cached file for: {path}")
            return self._file_cache[path]
            
        client = self._get_client()
        logger.info(f"Uploading file to Gemini: {path}")
        
        # Use localized status if available
        from core.i18n.localization import DesktopLocale
        
        if status_callback:
            msg = DesktopLocale.get("status_uploading_audio") if mime_type != "text/plain" else DesktopLocale.get("status_uploading_text")
            status_callback(f"{msg} ({os.path.basename(path)})")
            
        from google.genai import types
        
        try:
            # Fix: Use types.UploadFileConfig for proper strict typing
            upload_config = None
            if mime_type:
                upload_config = types.UploadFileConfig(mime_type=mime_type)

            file_obj = client.files.upload(file=path, config=upload_config)
            
            # Wait for processing (especially for audio)
            start_time = time.time()
            if status_callback:
                status_callback(f"{DesktopLocale.get('status_processing_llm')} ({os.path.basename(path)})")
                
            while file_obj.state.name == "PROCESSING":
                time.sleep(2) # Poll every 2 seconds
                file_obj = client.files.get(name=file_obj.name)
                if status_callback and (time.time() - start_time) > 5:
                    status_callback(f"{DesktopLocale.get('status_processing_llm')} ({os.path.basename(path)})")
                
            if file_obj.state.name != "ACTIVE":
                raise ValueError(f"File upload failed with state: {file_obj.state.name}")
                
            logger.info(f"File uploaded successfully: {file_obj.name}")
            self._file_cache[path] = file_obj
            return file_obj
        except Exception as e:
            logger.error(f"Gemini file upload error: {e}")
            raise

    def correct_text(self, text: str, language: str = "zh-tw", system_prompt: Optional[str] = None, 
                     temperature: float = 0.3, max_output_tokens: int = 60000, enable_web_search: bool = False,
                     audio_path: Optional[str] = None, use_file_caching: bool = False,
                     status_update_callback: Optional[callable] = None) -> str:
        """
        Correct transcript text using Gemini.
        
        Args:
            text: The raw transcript text (SRT format content)
            language: Language code for prompt selection
            system_prompt: Optional custom system prompt
            temperature: Optional specific temperature (default 0.3)
            max_output_tokens: Maximum tokens for the output response
            enable_web_search: Enable Google Search grounding for fact-checking
            audio_path: Optional path to audio file for multimodal grounding
            use_file_caching: Enable uploading transcript as file (for long contexts)
            status_update_callback: Optional callback(str) to update UI status message
        
        Returns:
            Corrected transcript text
        """
        # Use custom prompt if provided, else use default based on language
        final_prompt = system_prompt if system_prompt and system_prompt.strip() else get_correction_prompt(language)
        client = self._get_client()
        from google.genai import types
        from core.i18n.localization import DesktopLocale
        
        # Build contents list
        contents = []
        
        # 1. Handle Audio Grounding
        if audio_path and os.path.exists(audio_path):
            try:
                # Optimized: Ensure audio is in supported/efficient format (MP3)
                # This extracts audio from video or converts unsupported formats
                from core.utils.audio_utils import ensure_audio_format
                
                if status_update_callback:
                    status_update_callback(f"{DesktopLocale.get('status_processing_llm')} (Pre-processing Audio...)")
                    
                processed_audio_path = ensure_audio_format(audio_path)
                
                audio_file = self._upload_and_wait(processed_audio_path, status_callback=status_update_callback)
                contents.append(types.Part.from_uri(
                    file_uri=audio_file.uri,
                    mime_type=audio_file.mime_type
                ))
                contents.append("Please correct the following transcript using this audio as a reference for accuracy:")
                
            except Exception as e:
                logger.error(f"Failed to process audio for grounding: {e}")
                if status_update_callback:
                    # Provide a more user-friendly error message in the UI status
                    if "FFmpeg not found" in str(e):
                        status_update_callback(f"{DesktopLocale.get('status_processing_llm')} (Audio Skipped: FFmpeg missing)")
                    else:
                        status_update_callback(f"{DesktopLocale.get('status_processing_llm')} (Audio Skipped: {str(e)})")
                
                # Fail gracefully: Skip adding audio but continue with text correction
                pass
        
        # 2. Handle Text Input (Direct string of File Caching)
        if use_file_caching and len(text) > 100: # Only cache meaningful length
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.srt', encoding='utf-8') as tmp:
                tmp.write(text)
                tmp_path = tmp.name
            
            try:
                # Use plain text for SRT content cache
                # Status update handled inside _upload_and_wait
                text_file = self._upload_and_wait(tmp_path, mime_type="text/plain", status_callback=status_update_callback)
                contents.append(types.Part.from_uri(
                    file_uri=text_file.uri,
                    mime_type=text_file.mime_type
                ))
            finally:
                # Cleanup local temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        else:
            # Standard text injection - wrapped in Part for consistency with multimodal inputs
            contents.append(types.Part.from_text(text=text))

        # Build config with optional web search tool
        config_params = {
            "system_instruction": final_prompt,
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        
        if enable_web_search:
            # Enable Google Search grounding - model will decide when to search
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            config_params["tools"] = [grounding_tool]
        else:
            # Explicitly disable tools to prevent "AFC is enabled" logs
            config_params["tools"] = None
        
        response = client.models.generate_content(
            model=self.model_name,
            contents=contents,
            config=types.GenerateContentConfig(**config_params),
        )
        
        if not response.text:
            raise ValueError("Gemini returned empty response (possibly due to safety filters)")
        return response.text
    
    def verify_connection(self) -> tuple[bool, str]:
        """
        Test if the Gemini API connection is working.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            client = self._get_client()
            from google.genai import types
            response = client.models.generate_content(
                model=self.model_name,
                contents="Hello",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            return (True, "") if response.text else (False, "Empty response")
        except Exception as e:
            return (False, str(e))
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available Gemini models.
        
        Returns:
            List of model names
        """
        try:
            client = self._get_client()
            # List models that support content generation
            # Note: client.models.list returns an iterator of Model objects
            models = client.models.list(config={'query_base': True})
            
            # Simple filtering for common Gemini models (or check supported_actions)
            # Adjust filter logic as needed based on actual API response structure
            available = []
            for m in models:
                # Based on google-genai SDK, m is a Model object
                # We filter for 'generateContent' support if possible, or just look for gemini prefixes
                name = m.name.split('/')[-1] # models/gemini-1.5-flash -> gemini-1.5-flash
                if "gemini" in name.lower() and "vision" not in name.lower():
                    available.append(name)
            
            # If we found models, return them (sorted for consistency)
            if available:
                return sorted(list(set(available)), reverse=True)
                
        except Exception as e:
            # Fallback to static list if API fails
            pass
            
        # Fallback to static list
        return self.AVAILABLE_MODELS
    
    @property
    def provider_name(self) -> str:
        return "Gemini"
