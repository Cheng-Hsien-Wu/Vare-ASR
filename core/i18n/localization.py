import locale
import json
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DesktopLocale:
    _strings = {}
    current_lang = "en"

    @classmethod
    def init(cls):
        """Auto-detect system language and load locales"""
        # 1. Detect Language
        try:
            sys_lang = locale.getlocale()[0]
        except Exception:
            sys_lang = None
            
        if not sys_lang:
            # Fallback for some systems
            sys_lang = os.getenv('LANG')
        if sys_lang:
            lang_code = sys_lang.lower().replace("_", "-")
            if lang_code.startswith("zh"):
                cls.current_lang = "zh-tw"
            else:
                cls.current_lang = "en"
        else:
            cls.current_lang = "en"
            
        # 2. Load JSON files
        base_dir = Path(__file__).parent.parent.parent / "locales"
        
        # Load English (Fallback)
        try:
            with open(base_dir / "en.json", "r", encoding="utf-8") as f:
                cls._strings["en"] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading en.json: {e}")
            cls._strings["en"] = {}

        # Load Current Language if different
        if cls.current_lang != "en":
            try:
                target_file = base_dir / f"{cls.current_lang}.json"
                if target_file.exists():
                    with open(target_file, "r", encoding="utf-8") as f:
                        cls._strings[cls.current_lang] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading {cls.current_lang}.json: {e}")
    
    @classmethod
    def get(cls, key):
        """Get localized string"""
        # Dictionary lookup: Current Lang -> Fallback (En) -> Key itself
        lang_dict = cls._strings.get(cls.current_lang, cls._strings.get("en", {}))
        value = lang_dict.get(key, cls._strings.get("en", {}).get(key, key))
        
        # If value is a list, join with newlines (for multi-line JSON readability)
        if isinstance(value, list):
            return "\n".join(value)
        return value

    @classmethod
    def set_locale(cls, lang_code):
        """Set the current language and load its locale file if needed"""
        cls.current_lang = lang_code
        
        # Load the locale file if not already loaded
        if lang_code not in cls._strings:
            base_dir = Path(__file__).parent.parent.parent / "locales"
            target_file = base_dir / f"{lang_code}.json"
            if target_file.exists():
                try:
                    with open(target_file, "r", encoding="utf-8") as f:
                        cls._strings[lang_code] = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading {lang_code}.json: {e}")
