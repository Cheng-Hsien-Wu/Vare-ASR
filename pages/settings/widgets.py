"""
Settings Page - Shared Utilities
Contains helper classes and functions used across settings sections.
"""

import flet as ft
from typing import Optional, List, Callable

from ui.theme import ThemeManager, WeightScale, TextScale
from ui.components import FluentCard, FluentButton, FluentDropdown, FluentTextField
from core.i18n.localization import DesktopLocale


# ============ Settings Layout Constants ============
# Centralized spacing values to ensure consistency across all sections
SETTINGS_ROW_SPACING = 32      # Space between setting rows within a section
SETTINGS_INDENT = 32           # Left indent for setting rows (align with header text after icon)
SETTINGS_HEADER_GAP = 32       # Space between header and first setting row
SETTINGS_SECTION_SPACING = 24  # Space between major sections (beam, halluc, vad, system)


class ScrollablePathText(ft.Container):
    """A container displaying scrollable text for long paths using TextField"""
    def __init__(self, value: str, placeholder: str = "", width: Optional[int] = None, expand: bool = False) -> None:
        width_val = width if width is not None else (None if expand else 450)
        
        self.text_control = FluentTextField(
            value=value,
            hint_text=placeholder,
            read_only=True,
            border_color=ft.Colors.TRANSPARENT,
            expand=True,
            text_size=ThemeManager.get_font_size(),
            content_padding=ft.Padding.symmetric(horizontal=8, vertical=0),
        )
        
        super().__init__(
            content=self.text_control,
            width=width_val,
            expand=expand,
            bgcolor=None,
            border=None,
        )
        self.current_value = value
        self.placeholder_text = placeholder

    def value(self, new_val: Optional[str] = None) -> str:
        if new_val is not None:
            self.current_value = new_val
            self.text_control.value = new_val
            if self.text_control.page:
                self.text_control.update()
        return self.current_value

    def set_disabled(self, disabled: bool) -> None:
        self.disabled = disabled
        self.text_control.disabled = disabled
        if self.text_control.page:
            self.text_control.update()


class SettingsHelper:
    """Helper utilities for settings sections"""
    
    # Cached label width per language
    _cached_label_width: dict = {}
    
    @classmethod
    def get_font_multiplier(cls) -> float:
        """Get current font scale multiplier"""
        return TextScale.get_multiplier()
    
    @classmethod
    def v_space(cls, base_height: int = 8) -> ft.Container:
        """Create vertical spacing with dynamic height based on font scale"""
        return ft.Container(height=int(base_height * cls.get_font_multiplier()))
    
    @classmethod
    def estimate_width(cls, text: str) -> int:
        """Estimate text width based on character types"""
        width = 0
        for char in text:
            if ord(char) > 127:
                width += 18  # CJK chars
            elif char.isupper():
                width += 11  # Uppercase
            else:
                width += 9   # Lowercase/other
        return int(width * cls.get_font_multiplier())
    
    @classmethod
    def get_label_area_width(cls, label_keys: List[str]) -> int:
        """Calculate max label width (with caching)"""
        current_lang = DesktopLocale.current_lang
        cache_key = f"{current_lang}_{TextScale.current}"
        
        if cache_key in cls._cached_label_width:
            return cls._cached_label_width[cache_key]
        
        max_width = 0
        for key in label_keys:
            text = DesktopLocale.get(key)
            w = cls.estimate_width(text)
            if w > max_width:
                max_width = w
        
        result = max_width + 40  # Buffer
        cls._cached_label_width[cache_key] = result
        return result
    
    @classmethod
    def clear_cache(cls):
        """Clear cached values (call on language/font change)"""
        cls._cached_label_width.clear()
    
    @classmethod
    def get_adaptive_width(cls, options: list, min_width: int = 150, max_width: int = 500) -> int:
        """Calculate dropdown width based on option text"""
        max_w = 0
        for opt in options:
            text = opt.text if opt.text else str(opt.key)
            w = cls.estimate_width(text)
            if w > max_w:
                max_w = w
        return max(min_width, min(max_w + 60, max_width))
    
    @classmethod
    def section_header(cls, title_key: str, icon) -> ft.Container:
        """Create a section header with icon and title"""
        header_row = ft.Row([
            ft.Icon(icon, size=20, color=ThemeManager.current.accent),
            ft.Text(
                DesktopLocale.get(title_key),
                size=ThemeManager.get_font_size(2),  # Larger font for headers
                weight=WeightScale.BASE,
                color=ThemeManager.current.accent
            ),
        ], spacing=8)
        
        # Wrap in Container with margin for separate header spacing control
        return ft.Container(
            content=header_row,
            margin=ft.margin.only(bottom=SETTINGS_HEADER_GAP),  # Space after header
        )
    
    @classmethod
    def setting_row(cls, label_key: str, control: ft.Control, 
                    label_area_width: int, info_key: Optional[str] = None) -> ft.Row:
        """Create a setting row with label and control"""
        label_text = DesktopLocale.get(label_key)
        label_content = [
            ft.Text(label_text, style=ThemeManager.get_text_style(), weight=WeightScale.BASE)
        ]
        
        if info_key:
            info_text = DesktopLocale.get(info_key)
            label_content.append(
                ft.Icon(
                    ft.Icons.INFO_OUTLINE_ROUNDED,
                    size=int(14 * cls.get_font_multiplier()),
                    color=ThemeManager.current.text_tertiary,
                    tooltip=info_text
                )
            )
        
        label_row = ft.Row(
            label_content,
            spacing=4,
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True
        )
        
        # Use Container wrapper with margin for left indentation (cleaner than empty Container)
        row = ft.Row([
            ft.Container(content=label_row, width=label_area_width),
            control,
        ], spacing=24, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        
        return ft.Container(
            content=row,
            # Use margin for both indentation and vertical spacing
            # This ensures consistent spacing regardless of parent Column settings
            margin=ft.margin.only(left=SETTINGS_INDENT, bottom=SETTINGS_ROW_SPACING),
        )


# Standard label keys used across settings (for width calculation)
STANDARD_LABEL_KEYS = [
    "appearance", "display_language", "theme", "font_size",
    "basic_settings", "ai_model", "language", "task", "device", 
    "word_timestamps", "model_cache_dir", "initial_prompt",
    "output_format", "output_directory",
    "beam_search_settings", "beam_size", "best_of", "patience", 
    "length_penalty", "temperature",
    "hallucination_control", "repetition_penalty", "no_repeat_ngram_size", 
    "condition_on_previous_text", "suppress_blank", "log_prob_threshold", 
    "no_speech_threshold", "compression_ratio_threshold", "hallucination_silence_threshold",
    "vad_settings", "vad_enable", "vad_threshold", "vad_min_speech_duration", 
    "vad_max_speech_duration", "vad_min_silence_duration", "vad_speech_pad",
    "system_settings", "precision", "cpu_threads", "num_workers", "local_files_only"
]
