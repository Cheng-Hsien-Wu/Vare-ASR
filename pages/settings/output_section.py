"""
Output Settings Section
Settings for output format and directory.
"""

import flet as ft
from typing import Optional

from ui.theme import ThemeManager
from ui.components import FluentCard, FluentButton, FluentDropdown
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from .widgets import SettingsHelper, ScrollablePathText
from core.events import EventBus, Events

class OutputSection:
    """Output settings section (format, directory)"""
    
    def __init__(self, label_area_width: int) -> None:
        self.label_area_width = label_area_width
        
        # Controls
        self.combo_output_format: Optional[FluentDropdown] = None
        self.text_output_dir: Optional[ScrollablePathText] = None
        self.btn_browse_output_dir: Optional[FluentButton] = None
        
        # Subscribe to updates
        EventBus.subscribe(Events.OUTPUT_DIR_CHANGED, self._on_external_output_dir_change)

    def __del__(self):
        try:
            EventBus.unsubscribe(Events.OUTPUT_DIR_CHANGED, self._on_external_output_dir_change)
        except (ImportError, Exception):
            pass

    
    def build(self) -> FluentCard:
        """Build the output settings card"""
        h = SettingsHelper
        
        # Section header
        header = h.section_header("output_settings", ft.Icons.FOLDER_OPEN_ROUNDED)
        
        # Output format dropdown
        saved_format = UserSettings.get("output_format", "srt")
        format_opts = [
            ft.dropdown.Option("srt", DesktopLocale.get("format_srt")),
            ft.dropdown.Option("txt", DesktopLocale.get("format_txt")),
        ]
        self.combo_output_format = FluentDropdown(
            options=format_opts,
            value=saved_format,
            width=h.get_adaptive_width(format_opts),
            on_change=lambda e: self._on_format_changed(e.control.value),
        )
        
        # Output directory
        saved_output_dir = UserSettings.get("output_directory", "")
        self.text_output_dir = ScrollablePathText(
            value=saved_output_dir,
            placeholder=DesktopLocale.get("output_directory_tooltip"),
            width=450,
        )
        self.btn_browse_output_dir = FluentButton(
            DesktopLocale.get("browse"),
            ft.Icons.FOLDER_OPEN_ROUNDED,
            on_click=self._on_browse_output_dir
        )
        output_dir_row = ft.Row([self.text_output_dir, self.btn_browse_output_dir], spacing=8)
        
        return FluentCard(
            ft.Column([
                header,
                h.setting_row("output_format", self.combo_output_format, self.label_area_width, "output_format_tooltip"),
                h.setting_row("output_directory", output_dir_row, self.label_area_width, "output_directory_tooltip"),
            ], spacing=0),
            padding=ft.Padding(20, 20, 20, 10)
        )
    
    def _on_format_changed(self, value: str) -> None:
        """Handle format change"""
        UserSettings.set("output_format", value)
        EventBus.emit(Events.OUTPUT_FORMAT_CHANGED, value)

    def _on_browse_output_dir(self, e: ft.ControlEvent) -> None:
        """Handle browse output directory"""
        # Emitting event to request app to open file picker
        EventBus.emit(Events.BROWSE_OUTPUT_DIR_REQUESTED)

    def _on_external_output_dir_change(self, path: str) -> None:
        """Handle external output directory change"""
        if self.text_output_dir and hasattr(self.text_output_dir, 'value') and callable(self.text_output_dir.value):
            self.text_output_dir.value(path)

    def set_disabled(self, disabled: bool) -> None:
        """Enable/disable all controls in this section"""
        if self.combo_output_format:
            self.combo_output_format.disabled = disabled
        if self.btn_browse_output_dir:
            if hasattr(self.btn_browse_output_dir, 'set_disabled'):
                self.btn_browse_output_dir.set_disabled(disabled)
            else:
                self.btn_browse_output_dir.disabled = disabled
