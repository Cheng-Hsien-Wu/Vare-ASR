"""
Basic Settings Section
Settings for ASR model, language, device, and basic transcription options.
"""

import flet as ft
import os
from typing import Optional

from ui.theme import ThemeManager, WeightScale, TextScale
from ui.components import FluentCard, FluentButton, FluentDropdown, FluentTextField
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from core.events import EventBus, Events
from core.constants.srt_languages import WHISPER_LANGUAGES
from core import device_detection
from .widgets import SettingsHelper, ScrollablePathText, SETTINGS_ROW_SPACING

class BasicSection:
    """Basic transcription settings section"""
    
    def __init__(self, label_area_width: int) -> None:
        self.label_area_width = label_area_width
        
        # Controls
        self.combo_model: Optional[FluentDropdown] = None
        self.text_custom_model: Optional[FluentTextField] = None
        self.custom_model_container: Optional[ft.Container] = None
        self.combo_lang: Optional[FluentDropdown] = None
        self.combo_task: Optional[FluentDropdown] = None
        self.combo_device: Optional[FluentDropdown] = None
        self.switch_word_timestamps: Optional[ft.Switch] = None
        self.text_model_cache_dir: Optional[ScrollablePathText] = None
        self.btn_browse_model_dir: Optional[FluentButton] = None
        self.text_initial_prompt: Optional[FluentTextField] = None
        
        # Determine path to user home-based HuggingFace cache for default display
        self._default_cache_path = os.path.abspath(os.path.join(
            os.getenv("HF_HOME", os.path.join(os.path.expanduser("~"), ".cache", "huggingface")),
            "hub"
        ))
        
        # Subscribe to updates
        EventBus.subscribe(Events.MODEL_DIR_CHANGED, self._on_external_model_dir_change)
    
    def __del__(self) -> None:
        try:
            EventBus.unsubscribe(Events.MODEL_DIR_CHANGED, self._on_external_model_dir_change)
        except (ImportError, Exception):
            pass

    
    def build(self) -> FluentCard:
        """Build the basic settings card"""
        h = SettingsHelper
        
        # Section header
        header = h.section_header("basic_settings", ft.Icons.TUNE_ROUNDED)
        
        # Model selection
        saved_model = UserSettings.get("asr_model")
        predefined_models = [
            "SoybeanMilk/faster-whisper-Breeze-ASR-25",
            "Systran/faster-whisper-tiny",
            "Systran/faster-whisper-small",
            "Systran/faster-whisper-base",
            "Systran/faster-whisper-medium",
            "Systran/faster-whisper-large-v2",
            "Systran/faster-whisper-large-v3",
            "Systran/faster-distil-whisper-large-v2",
            "Systran/faster-distil-whisper-large-v3",
            "Systran/faster-whisper-tiny.en",
            "Systran/faster-whisper-small.en",
            "Systran/faster-whisper-base.en",
            "Systran/faster-whisper-medium.en",
            "Systran/faster-distil-whisper-small.en",
            "Systran/faster-distil-whisper-medium.en",
        ]
        is_custom_model = saved_model not in predefined_models
        
        model_options = [
            ft.dropdown.Option(m, m) for m in predefined_models
        ] + [ft.dropdown.Option("__custom__", DesktopLocale.get("custom_model"))]
        
        self.combo_model = FluentDropdown(
            options=model_options,
            value="__custom__" if is_custom_model else saved_model,
            width=h.get_adaptive_width(model_options, min_width=350, max_width=500),
            on_change=self._on_model_changed,
        )
        
        # Custom model input
        self.text_custom_model = FluentTextField(
            value=saved_model if is_custom_model else "",
            hint_text="user/model-name",
            width=350,
            on_change=self._on_custom_model_changed,
        )
        custom_model_info = ft.Icon(
            ft.Icons.HELP_OUTLINE_ROUNDED,
            size=int(16 * TextScale.get_multiplier()),
            color=ThemeManager.current.text_tertiary,
            tooltip=DesktopLocale.get("custom_model_hint")
        )
        self.custom_model_container = ft.Container(
            content=ft.Row([self.text_custom_model, custom_model_info], spacing=8, 
                          vertical_alignment=ft.CrossAxisAlignment.CENTER),
            visible=is_custom_model,
            padding=ft.Padding.only(top=8),
        )
        
        model_column = ft.Column([
            self.combo_model,
            self.custom_model_container,
        ], spacing=0)
        
        # Language dropdown
        priority = ['auto', 'zh', 'en', 'ja', 'ko']
        other_langs = sorted([k for k in WHISPER_LANGUAGES.keys() if k not in priority])
        sorted_keys = priority + other_langs
        
        lang_options = []
        for key in sorted_keys:
            label = WHISPER_LANGUAGES[key]
            loc_key = f"lang_{key}"
            loc_val = DesktopLocale.get(loc_key)
            if loc_val != loc_key:
                label = loc_val
            lang_options.append(ft.dropdown.Option(key, label))
        
        saved_lang = UserSettings.get("asr_language")
        self.combo_lang = FluentDropdown(
            options=lang_options,
            value=saved_lang,
            width=h.get_adaptive_width(lang_options, min_width=200),
            on_change=self._on_language_changed,
        )
        
        # Task dropdown
        saved_task = UserSettings.get("task")
        task_opts = [
            ft.dropdown.Option("transcribe", DesktopLocale.get("task_transcribe")),
            ft.dropdown.Option("translate", DesktopLocale.get("task_translate")),
        ]
        self.combo_task = FluentDropdown(
            options=task_opts,
            value=saved_task,
            width=h.get_adaptive_width(task_opts),
            on_change=lambda e: UserSettings.set("task", e.control.value),
        )
        
        # Device dropdown - dynamically detect available devices
        available_devices = device_detection.detect_available_devices()
        device_opts = [ft.dropdown.Option(dev_id, dev_name) for dev_id, dev_name in available_devices]
        
        # Get saved device, validate it's still available
        saved_device = UserSettings.get("asr_device")
        available_ids = [dev_id for dev_id, _ in available_devices]
        if saved_device not in available_ids:
            # Saved device not available, use best detected device
            saved_device = device_detection.get_default_device()
            UserSettings.set("asr_device", saved_device)
        
        def on_device_changed(e):
            device = e.control.value
            UserSettings.set("asr_device", device)
            EventBus.emit(Events.DEVICE_CHANGED, device)  # Notify AdvancedSection to refresh compute types
        
        self.combo_device = FluentDropdown(
            options=device_opts,
            value=saved_device,
            width=h.get_adaptive_width(device_opts),
            on_change=on_device_changed,
        )
        
        # Word timestamps switch
        saved_word_ts = UserSettings.get("word_timestamps")
        self.switch_word_timestamps = ft.Switch(
            value=saved_word_ts,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("word_timestamps", e.control.value),
        )
        
        saved_model_dir = UserSettings.get("model_cache_directory")
        
        self.text_model_cache_dir = ScrollablePathText(
            value=saved_model_dir,
            placeholder=self._default_cache_path,
            width=450
        )
        self.btn_browse_model_dir = FluentButton(
            DesktopLocale.get("browse"),
            ft.Icons.FOLDER_OPEN_ROUNDED,
            on_click=self._on_browse_model_dir
        )
        model_dir_row = ft.Row([self.text_model_cache_dir, self.btn_browse_model_dir], spacing=8)
        
        # Initial prompt
        saved_prompt = UserSettings.get("initial_prompt")
        self.text_initial_prompt = FluentTextField(
            value=saved_prompt,
            multiline=True,
            width=500,
            min_lines=3,
            max_lines=5,
            hint_text=DesktopLocale.get("prompt_hint"),
            on_blur=lambda e: UserSettings.set("initial_prompt", e.control.value),
        )
        
        return FluentCard(
            ft.Column([
                header,
                h.setting_row("ai_model", model_column, self.label_area_width, "model_tooltip"),
                h.setting_row("language", self.combo_lang, self.label_area_width, "lang_tooltip"),
                h.setting_row("device", self.combo_device, self.label_area_width, "device_tooltip"),
                h.setting_row("initial_prompt", self.text_initial_prompt, self.label_area_width, "prompt_tooltip"),
                
                ft.Divider(height=10, thickness=1, color=ThemeManager.current.divider),
                
                # Advanced Settings Tile (Moved to bottom)
                ft.ExpansionTile(
                    title=ft.Text(DesktopLocale.get("advanced_settings"), weight=WeightScale.LG),
                    controls=[
                        ft.Column([
                            h.setting_row("task", self.combo_task, self.label_area_width, "task_tooltip"),
                            h.setting_row("word_timestamps", self.switch_word_timestamps, self.label_area_width, "word_timestamps_tooltip"),
                            h.setting_row("model_cache_dir", model_dir_row, self.label_area_width, "model_cache_dir_tooltip"),
                        ], spacing=0)
                    ],
                    maintain_state=False,
                    affinity=ft.TileAffinity.LEADING,
                    tile_padding=ft.Padding.symmetric(vertical=SETTINGS_ROW_SPACING/2),
                    text_color=ThemeManager.current.text_primary,
                    icon_color=ThemeManager.current.text_secondary,
                    collapsed_text_color=ThemeManager.current.text_primary,
                    collapsed_icon_color=ThemeManager.current.text_secondary,
                )
            ], spacing=0),
            padding=ft.Padding(20, 20, 20, 10)
        )
    
    # === Local Handlers ===
    
    def _on_model_changed(self, e: ft.ControlEvent) -> None:
        """Handle model selection"""
        val = e.control.value
        is_custom = val == "__custom__"
        self.custom_model_container.visible = is_custom
        self.custom_model_container.update()
        
        # If not custom, save immediately
        if not is_custom:
             UserSettings.set("asr_model", val)
    
    def _on_custom_model_changed(self, e: ft.ControlEvent) -> None:
        """Handle custom model text change"""
        val = e.control.value
        UserSettings.set("asr_model", val) # Save raw string for custom
    
    def _on_language_changed(self, e: ft.ControlEvent) -> None:
        """Handle ASR language change"""
        val = e.control.value
        UserSettings.set("asr_language", val)
    
    def _on_browse_model_dir(self, e: ft.ControlEvent) -> None:
        """Open file picker for model dir"""
        EventBus.emit(Events.BROWSE_MODEL_DIR_REQUESTED)

    def _on_external_model_dir_change(self, path: str) -> None:
        """Handle external model directory change (e.g. from FilePicker)"""
        if self.text_model_cache_dir and hasattr(self.text_model_cache_dir, 'value'):
            self.text_model_cache_dir.value(path)

    def set_disabled(self, disabled: bool) -> None:
        """Enable/disable all controls in this section"""
        controls = [
            self.combo_model, self.text_custom_model, self.combo_lang,
            self.combo_task, self.combo_device, self.switch_word_timestamps,
            self.text_initial_prompt
        ]
        if self.btn_browse_model_dir:
            self.btn_browse_model_dir.disabled = disabled
            
        for ctrl in controls:
            if ctrl:
                if hasattr(ctrl, 'set_disabled'):
                    ctrl.set_disabled(disabled)
                else:
                    ctrl.disabled = disabled
