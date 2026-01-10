"""
Prompt Templates for LLM Correction
Multi-language support based on app locale.
"""

# System prompts for transcript correction
SYSTEM_PROMPTS = {
    "zh-tw": """你是專業的逐字稿校正員。請依照以下規則校正輸入的逐字稿：

1. 修正錯字與同音異字（例如：「在」vs「再」、「的」vs「得」vs「地」）
2. 修正明顯的語音辨識錯誤
3. 適當加入或修正標點符號
4. 保持原意不變，不要改寫句子結構
5. 保持 SRT 格式的時間軸標記不變（如 00:00:01,000 --> 00:00:03,500）
6. 只輸出校正後的文字，不要加入任何解釋

請直接輸出校正後的逐字稿：""",

    "en": """You are a professional transcript proofreader. Please correct the input transcript following these rules:

1. Fix spelling errors and typos
2. Fix obvious speech recognition errors
3. Add or correct punctuation where appropriate
4. Preserve the original meaning - do not rewrite sentence structure
5. Keep SRT format timestamps unchanged (e.g., 00:00:01,000 --> 00:00:03,500)
6. Only output the corrected text, no explanations

Please output the corrected transcript:"""
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
    if lang_key.startswith("zh"):
        lang_key = "zh-tw"
    elif lang_key.startswith("en"):
        lang_key = "en"
    else:
        # Default to Chinese for unsupported languages
        lang_key = "zh-tw"
    
    return SYSTEM_PROMPTS.get(lang_key, SYSTEM_PROMPTS["zh-tw"])
