"""
Prompt Templates for LLM Correction
Multi-language support based on app locale.
"""

# System prompts for transcript correction
LLM_SYSTEM_PROMPT = {
    "zh-tw": """請修正以下ASR模型轉錄逐字稿中的聽錯部分，但不要潤飾句子，也請維持逐字稿的原始結構。請直接輸出修正後的逐字稿，無須說明或註解。""",

    "en": """Please correct the misheard portions in the following ASR model transcription, but do not embellish the sentences. Also, please maintain the original structure of the transcription. Output the corrected transcription directly, without explanations or comments."""
}


def get_correction_prompt(language: str = "zh-tw") -> str:
    """
    Get the appropriate system prompt based on language.
    
    Args:
        language: Language code (e.g., 'zh-tw', 'en')
    
    Returns:
        System prompt string
    """
    # Normalize language code
    lang_key = language.lower()
    
    # Map common Chinese variants to zh-tw
    if "zh" in lang_key:
        lang_key = "zh-tw"
    elif lang_key.startswith("en"):
        lang_key = "en"
    else:
        # Default to English for unsupported languages
        lang_key = "en"
    
    return LLM_SYSTEM_PROMPT.get(lang_key, LLM_SYSTEM_PROMPT["en"])
