"""
Appearance Section
Settings for theme, language, and font size.
"""

import flet as ft
from typing import Optional

from ui.theme import ThemeManager, TextScale
from ui.components import FluentCard, FluentDropdown
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from core.events import EventBus, Events
from .widgets import SettingsHelper

class AppearanceSection:
    """Appearance settings section (theme, language, font size)"""
    
    def __init__(self, label_area_width: int) -> None:
        self.label_area_width = label_area_width
        
        # Controls
        self.combo_display_lang: Optional[FluentDropdown] = None
        self.combo_theme: Optional[FluentDropdown] = None
        self.combo_font_size: Optional[FluentDropdown] = None
    
    def build(self) -> FluentCard:
        """Build the appearance settings card"""
        h = SettingsHelper
        
        # Section header
        header = h.section_header("appearance", ft.Icons.PALETTE_OUTLINED)
        
        # Language dropdown
        lang_opts = [
            ft.dropdown.Option("zh-tw", "繁體中文"),
            ft.dropdown.Option("en", "English")
        ]
        self.combo_display_lang = FluentDropdown(
            options=lang_opts,
            value=DesktopLocale.current_lang,
            width=h.get_adaptive_width(lang_opts),
            on_change=self._on_language_changed,
        )
        
        # Theme dropdown
        theme_opts = [
            ft.dropdown.Option("light", DesktopLocale.get("light")),
            ft.dropdown.Option("dark", DesktopLocale.get("dark"))
        ]
        self.combo_theme = FluentDropdown(
            options=theme_opts,
            value=ThemeManager.mode,
            width=h.get_adaptive_width(theme_opts),
            on_change=self._on_theme_changed,
        )
        
        # Font size dropdown
        font_opts = [
            ft.dropdown.Option("compact", DesktopLocale.get("font_small")),
            ft.dropdown.Option("default", DesktopLocale.get("font_medium")),
            ft.dropdown.Option("large", DesktopLocale.get("font_large")),
            ft.dropdown.Option("extra_large", DesktopLocale.get("font_xlarge"))
        ]
        self.combo_font_size = FluentDropdown(
            options=font_opts,
            value=TextScale.current,
            width=h.get_adaptive_width(font_opts),
            on_change=self._on_font_changed,
        )
        
        return FluentCard(
            ft.Column([
                header,
                h.setting_row("display_language", self.combo_display_lang, self.label_area_width),
                h.setting_row("theme", self.combo_theme, self.label_area_width),
                h.setting_row("font_size", self.combo_font_size, self.label_area_width),
            ], spacing=0),
            padding=ft.Padding(20, 20, 20, 10)
        )

    def _on_language_changed(self, e: ft.ControlEvent) -> None:
        """Handle language change internally and emit event"""
        lang = e.control.value
        # 1. Update Persistent Settings
        UserSettings.set("language", lang)
        # 2. Emit Event
        EventBus.emit(Events.APP_LANGUAGE_CHANGED, lang)

    def _on_theme_changed(self, e: ft.ControlEvent) -> None:
        """Handle theme change internally and emit event"""
        theme_mode = e.control.value
        # 1. Update Persistent Settings
        UserSettings.set("theme", theme_mode)
        # 2. Update Theme Manager (which might emit its own event, but we can emit explicit UI one too)
        # Actually ThemeManager.set_theme emits THEME_CHANGED if wired, but let's stick to our plan
        # We need to call ThemeManager to update internal state (FluentColors)
        ThemeManager.set_theme(theme_mode) 
        # 3. Emit Event
        EventBus.emit(Events.THEME_CHANGED, theme_mode)

    def _on_font_changed(self, e: ft.ControlEvent) -> None:
        """Handle font size change internally and emit event"""
        scale = e.control.value
        # 1. Update Persistent Settings
        UserSettings.set("font_size", scale)
        TextScale.current = scale
        # 2. Emit Event
        EventBus.emit(Events.TEXT_SCALE_CHANGED, scale)
    
    def set_disabled(self, disabled: bool) -> None:
        """Enable/disable all controls in this section"""
        controls = [self.combo_display_lang, self.combo_theme, self.combo_font_size]
        for ctrl in controls:
            if ctrl:
                if hasattr(ctrl, 'set_disabled'):
                    ctrl.set_disabled(disabled)
                else:
                    ctrl.disabled = disabled
