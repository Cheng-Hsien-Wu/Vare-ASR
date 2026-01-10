"""
Settings Page (Modular)
Main settings page that composes individual section components.
Reduced from 984 lines to ~150 lines.
"""

import flet as ft
from typing import TYPE_CHECKING

from ui.theme import ThemeManager, WeightScale
from ui.components import FluentCard, FluentButton
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from .base_page import BasePage

# Import modular sections
from .settings import (
    SettingsHelper, STANDARD_LABEL_KEYS,
    AppearanceSection, BasicSection, OutputSection, LLMSection, AdvancedSection
)

if TYPE_CHECKING:
    from app import VareApp


class SettingsPage(BasePage):
    """Settings configuration page using modular sections."""
    
    def __init__(self, page: ft.Page, app: "VareApp"):
        super().__init__(page)
        self.app = app
        
        # Section instances
        self._appearance: AppearanceSection = None
        self._basic: BasicSection = None
        self._output: OutputSection = None
        self._llm: LLMSection = None
        self._advanced: AdvancedSection = None
    
    def build(self) -> ft.Column:
        """Build settings configuration page using modular sections"""
        # Calculate label width once (cached by SettingsHelper)
        label_area_width = SettingsHelper.get_label_area_width(STANDARD_LABEL_KEYS)
        
        title = ft.Text(
            DesktopLocale.get("settings_title"),
            style=ThemeManager.get_text_style(14, weight=WeightScale.XL)
        )
        
        # Create section instances
        self._appearance = AppearanceSection(
            label_area_width=label_area_width,
        )
        
        self._basic = BasicSection(
            label_area_width=label_area_width,
        )
        
        self._output = OutputSection(
            label_area_width=label_area_width,
        )
        
        self._llm = LLMSection(
            label_area_width=label_area_width,
        )
        
        self._advanced = AdvancedSection(
            label_area_width=label_area_width,
        )
        
        # Build all section UI components FIRST (this creates the controls)
        appearance_card = self._appearance.build()
        basic_card = self._basic.build()
        output_card = self._output.build()
        llm_card = self._llm.build()
        advanced_group = self._advanced.build()
        
        
        # Reset button
        btn_reset = ft.TextButton(
            content=ft.Row([
                ft.Icon(ft.Icons.REFRESH_ROUNDED, size=14, color=ThemeManager.current.text_tertiary),
                ft.Text(DesktopLocale.get("reset_defaults"), style=ThemeManager.get_text_style(-2, color=ThemeManager.current.text_tertiary, weight=WeightScale.XL)),
            ], spacing=4, tight=True),
            on_click=self.app._reset_to_defaults,
            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=8, vertical=4)),
        )
        self.btn_reset = btn_reset
        
        # Apply read-only state if processing
        if self.app.is_processing:
            self.set_read_only(True)
        
        # Using Column with scroll (ListView causes cross-axis expansion issues)
        # Keep Column(spacing) optimization but restore proper layout structure
        return ft.Column([
            ft.Container(
                content=ft.Column([
                    title,
                    ft.Container(height=20),  # Space after title
                    appearance_card,
                    basic_card,
                    output_card,
                    llm_card,
                    advanced_group,
                    ft.Container(height=20),  # Space before reset button
                    btn_reset,
                    ft.Container(height=20),  # Bottom padding
                ], spacing=15),
                padding=ft.Padding.only(right=40),
            )
        ], spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
    
    
    def set_read_only(self, readonly: bool) -> None:
        """Set all input controls to read-only/disabled state."""
        if self._appearance:
            self._appearance.set_disabled(readonly)
        if self._basic:
            self._basic.set_disabled(readonly)
        if self._output:
            self._output.set_disabled(readonly)
        if self._llm:
            self._llm.set_disabled(readonly)
        if self._advanced:
            self._advanced.set_disabled(readonly)
        
        # Reset button
        if hasattr(self, 'btn_reset') and self.btn_reset:
            self.btn_reset.disabled = readonly
        
        if self.page:
            self.page.update()
            
    def reset_state(self) -> None:
        """Reset internal state (e.g. collapse advanced settings)"""
        if self._advanced:
            self._advanced.collapse()
