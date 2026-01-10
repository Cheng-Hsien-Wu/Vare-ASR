"""
Logs Page
Page for displaying application logs.
"""

import flet as ft
from typing import Optional, TYPE_CHECKING

from ui.theme import ThemeManager, WeightScale
from ui.components import FluentButton
from core.i18n.localization import DesktopLocale
from .base_page import BasePage

if TYPE_CHECKING:
    from app import VareApp


class LogsPage(BasePage):
    """Logs display page.
    
    Displays:
    - Real-time log output
    - Scrollable log view
    - Clear log button
    """
    
    def __init__(self, page: ft.Page, app: "VareApp"):
        """Initialize logs page.
        
        Args:
            page: Flet page reference
            app: VareApp reference for callbacks and log_view sharing
        """
        super().__init__(page)
        self.app = app
        self.log_view: Optional[ft.TextField] = None
    
    def build(self) -> ft.Container:
        """Build the logs page UI."""
        # Title section - matches Task page style
        title_section = ft.Column([
            ft.Text(DesktopLocale.get("logs"), style=ThemeManager.get_text_style(14, weight=WeightScale.XL)),
            ft.Text(DesktopLocale.get("logs_subtitle"), style=ThemeManager.get_text_style(-1, color=ThemeManager.current.text_tertiary, weight=WeightScale.LG)),
        ], spacing=8)
        
        # Create log view TextField
        self.log_view = ft.TextField(
            value="",
            multiline=True,
            read_only=True,
            border=ft.InputBorder.NONE,
            bgcolor=ft.Colors.TRANSPARENT,
            color=ThemeManager.current.text_primary,
            cursor_color=ThemeManager.current.accent,
            selection_color=ThemeManager.current.accent_dark,
            filled=False,
            text_style=ft.TextStyle(font_family="Consolas, Courier New", size=ThemeManager.get_font_size(-1)),
            expand=True,
        )
        
        # Share log_view with app for _log() method to work
        self.app.log_view = self.log_view
        
        # Log content container
        log_content_container = ft.Container(
            content=ft.Column([self.log_view], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor=ThemeManager.current.card_bg,
            border_radius=8,
            border=ft.Border.all(1, ThemeManager.current.border),
            padding=ft.Padding.only(left=15, top=15, bottom=15, right=5),
            expand=True,
        )
        
        # Clear log button
        btn_clear_log = FluentButton(
            DesktopLocale.get("clear_log"),
            ft.Icons.DELETE_OUTLINE_ROUNDED,
            on_click=lambda _: self.app._clear_log(),
        )
        
        # Action row
        action_row = ft.Row([
            ft.Container(),
            btn_clear_log
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # Content column
        return ft.Container(
            content=ft.Column([
                title_section,
                ft.Container(height=20),
                action_row,
                ft.Container(height=15),
                log_content_container,
                ft.Container(height=20),
            ], spacing=0, expand=True),
            padding=ft.Padding.only(right=40),
            expand=True,
        )
