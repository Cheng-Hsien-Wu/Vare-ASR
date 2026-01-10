"""
Admin Required Dialog Component
Shows a warning dialog when administrator privileges are required for model cache directory.
"""

import re
import flet as ft
from core.i18n.localization import DesktopLocale
from ui.theme import ThemeManager, WeightScale
from ui.components import FluentButton


def show_admin_required_dialog(page: ft.Page, on_restart_callback, on_cancel_callback=None) -> None:
    """
    Show a styled admin required warning dialog.
    
    This dialog is shown on Windows when the user tries to change the model cache
    directory without administrator privileges.
    
    Args:
        page: The Flet page instance
        on_restart_callback: Function to call when user clicks "Restart as Admin"
        on_cancel_callback: Optional function to call when user cancels
    """
    
    def on_restart(_):
        dlg.open = False
        page.update()
        if on_restart_callback:
            on_restart_callback()
    
    def on_cancel(_):
        dlg.open = False
        page.update()
        if on_cancel_callback:
            on_cancel_callback()
    
    # Parse message for links
    message = DesktopLocale.get("admin_required_message")
    url_pattern = r"(https?://[^\s]+)"
    parts = re.split(url_pattern, message)
    
    spans = []
    for part in parts:
        if not part: continue
        if re.match(url_pattern, part):
            spans.append(
                ft.TextSpan(
                    part,
                    style=ft.TextStyle(color=ThemeManager.current.accent),
                    url=part,
                )
            )
        else:
            spans.append(ft.TextSpan(part))

    # Create styled dialog following Fluent Design
    dlg = ft.AlertDialog(
        modal=True,
        title_padding=ft.padding.only(top=24, bottom=0, left=24, right=24),
        content_padding=ft.padding.only(top=16, bottom=24, left=24, right=24),
        actions_padding=ft.padding.only(bottom=20, right=24, left=24),
        bgcolor=ThemeManager.current.card_bg,
        shape=ft.RoundedRectangleBorder(radius=12),
        
        # Title with warning icon
        title=ft.Row([
            ft.Icon(
                ft.Icons.WARNING_AMBER_ROUNDED,
                color=ThemeManager.current.warning,
                size=28
            ),
            ft.Text(
                DesktopLocale.get("admin_required_title"),
                style=ThemeManager.get_text_style(scale="XL", weight=WeightScale.LG),
            ),
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
        
        # Content with message and parsed links
        content=ft.Container(
            content=ft.Text(
                spans=spans,
                style=ThemeManager.get_text_style(
                    scale="BASE",
                    weight=WeightScale.BASE,
                    color=ThemeManager.current.text_primary,
                ),
            ),
            width=500,
            padding=ft.padding.only(top=8, bottom=12),
        ),
        
        # Actions: Cancel and Restart buttons
        actions=[
            ft.Row([
                ft.Container(
                    content=FluentButton(
                        DesktopLocale.get("cancel"),
                        on_click=on_cancel,
                        primary=False,
                    ),
                    expand=True,
                ),
                ft.Container(
                    content=FluentButton(
                        DesktopLocale.get("restart_as_admin"),
                        icon=ft.Icons.ADMIN_PANEL_SETTINGS_ROUNDED,
                        on_click=on_restart,
                        primary=True,
                    ),
                    expand=True,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=12),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    
    # Show dialog using overlay approach
    page.overlay.append(dlg)
    dlg.open = True
    page.update()

