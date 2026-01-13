"""
User Settings Persistence
Saves and loads user preferences (theme, language, font size) to a local JSON file.
"""
import json
import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class UserSettings:
    """Manages user preferences with persistent storage"""
    
    # Default settings
    DEFAULTS = {
        # Appearance
        "theme": "dark",
        "language": "zh-tw", 
        "font_size": "default",
        
        # === Model Loading Settings ===
        "asr_model": "SoybeanMilk/faster-whisper-Breeze-ASR-25",
        "asr_device": "cuda",
        "compute_type": "float16",
        "cpu_threads": 4,
        "num_workers": 1,
        "flash_attention": False,
        "local_files_only": False,

        # === LLM Advanced Context ===
        "llm_enabled": False,
        "llm_provider": "gemini", 
        "llm_model": "gemini-2.5-flash",
        "llm_temperature": 0.3,
        "llm_system_prompt": "",
        "llm_base_url": "http://localhost:11434",
        "llm_web_search": False,
        "llm_use_file_caching": True,
        "llm_use_audio_grounding": False,
        
        # === Basic Transcription Settings ===
        "asr_language": "zh",
        "task": "transcribe",  # transcribe or translate
        "output_format": "srt",
        "initial_prompt": "",
        "word_timestamps": False,
        
        # === Beam Search Settings ===
        "beam_size": 5,
        "best_of": 5,
        "patience": 1.0,
        "length_penalty": 1.0,
        "repetition_penalty": 1.0,
        "no_repeat_ngram_size": 0,
        "temperature": "0",  # Can be comma-separated list like "0,0.2,0.4,0.6,0.8,1.0"
        
        # === Hallucination Control ===
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "condition_on_previous_text": True,
        "prompt_reset_on_temperature": 0.5,
        "hallucination_silence_threshold": 0.0,  # 0 = disabled
        "suppress_blank": True,
        
        # === VAD Settings ===
        "vad_enabled": True,
        "vad_threshold": 0.5,
        "vad_min_speech_duration_ms": 250,
        "vad_max_speech_duration_s": 5.0,
        "vad_min_silence_duration_ms": 300,
        "vad_speech_pad_ms": 100,
        
        # === Directories ===
        "output_directory": "",  # Empty = same as input file
        "model_cache_directory": "",  # Empty = default HF cache
        
        # === Window state persistence ===
        "window_width": 1040,
        "window_height": 640,
        "window_top": None,
        "window_left": None,
        "window_maximized": False,
    }
    
    _instance = None
    _settings = {}
    _settings_path = None
    
    @classmethod
    def init(cls, app_dir: str | None = None) -> None:
        """Initialize settings with optional custom directory"""
        if app_dir:
            cls._settings_path = Path(app_dir) / "settings.json"
        else:
            # Settings stored in platform-specific config directory
            import platform
            app_name = "Vare"
            system = platform.system()
            
            if system == "Windows":
                base_dir = Path(os.getenv('APPDATA', os.path.expanduser("~")))
            elif system == "Darwin":
                base_dir = Path.home() / "Library" / "Application Support"
            else:
                # Linux and other Unix-like systems
                base_dir = Path(os.getenv('XDG_CONFIG_HOME', Path.home() / ".config"))
            
            target_dir = base_dir / app_name
            target_dir.mkdir(parents=True, exist_ok=True)
            cls._settings_path = target_dir / "settings.json"
            

            


        
        cls._settings_path.parent.mkdir(parents=True, exist_ok=True)
        cls.load()
    
    @classmethod
    def load(cls) -> None:
        """Load settings from file"""
        cls._settings = cls.DEFAULTS.copy()
        
        if cls._settings_path and cls._settings_path.exists():
            try:
                with open(cls._settings_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    cls._settings.update(saved)
            except Exception as e:
                logger.warning(f"Could not load settings: {e}")
    
    @classmethod
    def save(cls) -> None:
        """Save current settings to file"""
        if cls._settings_path:
            try:
                with open(cls._settings_path, 'w', encoding='utf-8') as f:
                    json.dump(cls._settings, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Could not save settings: {e}")
    
    @classmethod
    def get(cls, key: str, default: any = None) -> any:
        """Get a setting value"""
        val = cls._settings.get(key)
        if val is not None:
            return val
        if default is not None:
            return default
        return cls.DEFAULTS.get(key)
    
    @classmethod
    def set(cls, key: str, value: any) -> None:
        """Set a setting value and save"""
        cls._settings[key] = value
        cls.save()
    
    @classmethod
    def get_all(cls) -> dict:
        """Get all settings"""
        return cls._settings.copy()
    
    @classmethod
    def reset_to_defaults(cls, exclude_window_state: bool = True) -> None:
        """Reset all settings to default values
        
        Args:
            exclude_window_state: If True, preserve window position/size settings
        """
        if exclude_window_state:
            # Preserve window state
            window_keys = ["window_width", "window_height", "window_top", "window_left", "window_maximized"]
            saved_window = {k: cls._settings.get(k) for k in window_keys}
            cls._settings = cls.DEFAULTS.copy()
            cls._settings.update(saved_window)
        else:
            cls._settings = cls.DEFAULTS.copy()
        cls.save()
