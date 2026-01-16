"""
Prompt Templates for LLM Correction
Multi-language support based on app locale.
"""

# System prompts for transcript correction
LLM_SYSTEM_PROMPT = {
    "zh-tw": """請修正以下ASR模型轉錄逐字稿中的聽錯部分，但不要潤飾句子。

重要規則：
1. 每一行開頭都有編號（如「1. 」），請保持編號不變
2. 絕對不要合併多行或拆分單行
3. 輸入幾行，輸出就要幾行，編號要對應
4. 只修正聽錯的字詞，不要改變句子結構

請直接輸出修正後的逐字稿（包含編號），無須說明或註解。""",

    "en": """Please correct the misheard portions in the following ASR model transcription, but do not embellish the sentences.

Important rules:
1. Each line starts with a number (e.g., "1. "), keep the numbering unchanged
2. Never merge multiple lines or split a single line
3. Output must have the same number of lines as input, with matching line numbers
4. Only correct misheard words, do not change sentence structure

Output the corrected transcription directly (including line numbers), without explanations or comments."""
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
