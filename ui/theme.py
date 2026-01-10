"""
Fluent Design System Theme Module
Contains color palettes, font scaling, and theme management.
"""

import flet as ft
from dataclasses import dataclass
from typing import Optional
import weakref


# ==========================================
# Fluent Design System Colors
# ==========================================
class FluentColors:
    """Windows 11 Fluent Design System Colors"""
    
    @dataclass
    class Palette:
        # Surfaces
        mica_bg: str
        nav_bg: str
        card_bg: str
        card_bg_secondary: str
        
        # Interaction
        hover_bg: str
        nav_hover_bg: str
        pressed_bg: str
        
        # Accents
        accent: str
        accent_light: str
        accent_dark: str
        accent_text: str
        
        # Text
        text_primary: str
        text_secondary: str
        text_tertiary: str
        text_disabled: str
        
        # Borders & Dividers
        border: str
        border_active: str
        divider: str
        
        # Semantic
        error: str
        success: str
        warning: str
        
        # Destructive Actions (e.g., Reset, Delete buttons)
        destructive_bg: str
        destructive_text: str
        
        # Components (Added for centralization)
        tooltip_bg: str
        scrollbar_thumb: str
        scrollbar_track: str
        win_close_hover_bg: str
        win_close_hover_icon: str
        win_btn_hover_overlay: str
        win_btn_hover_bg: str

    # Dark Mode Palette
    DARK = Palette(
        mica_bg="#202020",
        nav_bg="#202020",
        card_bg="#272727",
        card_bg_secondary="#2c2c2c",
        hover_bg="#3e3e3e",
        nav_hover_bg="#353535",
        pressed_bg="#303030",
        accent="#60cdff",
        accent_light="#9ae3ff",
        accent_dark="#4cc2ff",
        accent_text="#000000",
        text_primary="#f0f0f0",
        text_secondary="#c8c8c8",
        text_tertiary="#a0a0a0",  # Improved contrast ratio (~5.5:1)
        text_disabled="#5d5d5d",
        border="#353535",
        border_active="#454545",
        divider="#2b2b2b",
        error="#ff6b6b",
        success="#6ccb5f",
        warning="#fce100",
        
        # Destructive Actions (Reset, Delete buttons)
        destructive_bg="#D32F2F",  # Deep red for dark backgrounds
        destructive_text="#FFFFFF",
        
        # Component Colors
        tooltip_bg="#202020", # Base color, opacity applied in app
        scrollbar_thumb="#888888",
        scrollbar_track="#404040",
        win_close_hover_bg="#c42b1c",
        win_close_hover_icon="#ffffff",
        # 0.08 * 255 = ~20 -> 14 hex. White is #FFFFFF. So #14FFFFFF
        win_btn_hover_overlay="#14FFFFFF",
        win_btn_hover_bg="#3e3e3e"  # Matches hover_bg
    )

    # Light Mode Palette
    LIGHT = Palette(
        mica_bg="#eff4f9",
        nav_bg="#eff4f9",
        card_bg="#fbfbfb",
        card_bg_secondary="#ffffff",
        hover_bg="#e8e8e8",
        nav_hover_bg="#e6ebf0",
        pressed_bg="#d0d5d9",
        accent="#0078d4",
        accent_light="#2b88d8",
        accent_dark="#005a9e",
        accent_text="#ffffff",
        text_primary="#1C1C1E",
        text_secondary="#555555",
        text_tertiary="#5A5A5F",
        text_disabled="#9e9e9e",
        border="#e1dfdd",
        border_active="#8a8886",
        divider="#e1dfdd",
        error="#c50f1f",
        success="#107c10",
        warning="#d83b01",
        
        # Destructive Actions (Reset, Delete buttons)
        destructive_bg="#F44336",  # Softer red for light backgrounds
        destructive_text="#FFFFFF",
        
        # Component Colors
        tooltip_bg="#202020", # Preserved "Always Dark" tooltip
        scrollbar_thumb="#c0c0c0",
        scrollbar_track="#f0f0f0",
        win_close_hover_bg="#c42b1c",
        win_close_hover_icon="#ffffff",
        # 0.1 * 255 = 25.5 -> 19 hex. Black is #000000. So #19000000
        win_btn_hover_overlay="#19000000",
        win_btn_hover_bg="#a0a0a0"  # Specific override for light mode visibility
    )


# ===========================================
# Type Scale System
# ===========================================
class FontScale:
    """Predefined font sizes for consistent typography hierarchy"""
    XS = 12    # Captions, timestamps
    SM = 14    # Secondary text, dense lists
    BASE = 16  # Body text, default
    LG = 20    # Subtitles, section headers
    XL = 24    # Page titles
    XXL = 32   # Hero stats, large displays


class TextScale:
    """User-adjustable text scale multiplier"""
    OPTIONS = {
        "compact": 0.9,
        "default": 1.0,
        "large": 1.125,
        "extra_large": 1.25
    }
    current = "default"
    
    @classmethod
    def get_multiplier(cls) -> float:
        return cls.OPTIONS.get(cls.current, 1.0)
    
    @classmethod
    def set_scale(cls, scale_name: str) -> None:
        if scale_name in cls.OPTIONS:
            cls.current = scale_name


class FluentStyles:
    """Shared style configurations"""
    BORDER_RADIUS = 8
    ANIMATION_DURATION = 150
    
    FONT_FAMILY = "Noto Sans TC" #"Inter"
    
    NAV_ITEM_HEIGHT = 40
    NAV_WIDTH_EXPANDED = 260
    NAV_WIDTH_COLLAPSED = 48


# ===========================================
# Font Weight Scale
# ===========================================
class WeightScale:
    """
    Standardized font weight levels.
    Decouples design intent from implementation values.
    """
    BASE = ft.FontWeight.W_400  # 400 - General Text
    MD   = ft.FontWeight.W_500   # 500 - Emphasis, Subtitles
    LG   = ft.FontWeight.W_600   # 600 - UI Headers (Columns, Nav Selected)
    XL   = ft.FontWeight.W_700    # 700 - Page Titles, Major Dialog Headers
    XXL   = ft.FontWeight.W_900    # 900 - Title Headers


# ===========================================
# Theme Manager
# ===========================================
class ThemeManager:
    """Manages application theme state"""
    current: FluentColors.Palette = FluentColors.DARK
    mode: str = "dark"
    page: Optional[ft.Page] = None
    font_size: int = FontScale.BASE
    _listeners = weakref.WeakSet()

    @classmethod
    def get_font_size(cls, scale: str | int = "BASE", offset: int = 0) -> int:
        """Get font size with scale multiplier applied"""
        if isinstance(scale, int):
            base = FontScale.BASE + scale
        else:
            base = getattr(FontScale, scale.upper(), FontScale.BASE)
        
        scaled = int(base * TextScale.get_multiplier()) + offset
        return scaled
    
    @classmethod
    def get_text_style(cls, scale: str | int = "BASE", color: str | None = None, weight: ft.FontWeight | None = None, offset: int = 0) -> ft.TextStyle:
        """Get standard text style with Type Scale System"""
        if isinstance(scale, int):
            size = cls.get_font_size("BASE", scale)
        else:
            size = cls.get_font_size(scale, offset)
        
        return ft.TextStyle(
            size=size,
            color=color or cls.current.text_primary,
            weight=weight or WeightScale.BASE,
            font_family=FluentStyles.FONT_FAMILY,
            letter_spacing=0
        )

    @classmethod
    def set_font_size(cls, size: int) -> None:
        """Legacy: Set base font size and notify listeners"""
        cls.font_size = int(size)
        # Clear button style cache on font change
        from ui.components import FluentButton
        FluentButton.clear_style_cache()
        cls.notify_listeners()
    
    @classmethod
    def toggle(cls) -> None:
        if cls.mode == "dark":
            cls.set_theme("light")
        else:
            cls.set_theme("dark")
    
    @classmethod
    def set_theme(cls, mode: str) -> None:
        cls.mode = mode
        cls.current = FluentColors.LIGHT if mode == "light" else FluentColors.DARK
        # Clear button style cache on theme change
        from ui.components import FluentButton
        FluentButton.clear_style_cache()
        if cls.page:
            cls.page.theme_mode = ft.ThemeMode.LIGHT if mode == "light" else ft.ThemeMode.DARK
            cls._apply_global_theme_overrides(cls.page)
            cls.page.update()
        cls.notify_listeners()
        
    @classmethod
    def _apply_global_theme_overrides(cls, page: ft.Page) -> None:
        """Apply global theme overrides like SliderTheme"""
        if not page.theme:
            page.theme = ft.Theme()
            
        page.theme.slider_theme = ft.SliderTheme(
            year_2023=True,

            active_track_color=ThemeManager.current.accent, 
            inactive_track_color=ThemeManager.current.border,
            thumb_color=ThemeManager.current.accent,
            
            active_tick_mark_color=ft.Colors.TRANSPARENT,
            inactive_tick_mark_color=ft.Colors.TRANSPARENT,
            disabled_active_tick_mark_color=ft.Colors.TRANSPARENT,
            disabled_inactive_tick_mark_color=ft.Colors.TRANSPARENT,
        )

    @classmethod
    def subscribe(cls, control: object) -> None:
        cls._listeners.add(control)

    @classmethod
    def unsubscribe(cls, control: object) -> None:
        cls._listeners.discard(control)

    @classmethod
    def clear_component_listeners(cls, keep_app: object | None = None) -> None:
        """Clear all component listeners except the main app"""
        cls._listeners = weakref.WeakSet()
        if keep_app:
            cls._listeners.add(keep_app)

    @classmethod
    def notify_listeners(cls) -> None:
        for control in list(cls._listeners):
            try:
                if hasattr(control, "on_theme_changed"):
                    control.on_theme_changed()
            except Exception as e:
                import logging
                logging.error(f"Error notifying listener {control}: {e}")
