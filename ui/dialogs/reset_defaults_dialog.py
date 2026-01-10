"""
Reset Defaults Dialog Component
Encapsulates reset defaults confirmation dialog UI logic.
"""

import flet as ft
from core.i18n.localization import DesktopLocale
from ui.theme import ThemeManager, WeightScale


def show_reset_defaults_dialog(page: ft.Page, on_confirm_callback) -> None:
    """
    Show a styled reset defaults confirmation dialog.
    
    Uses overlay approach compatible with current Flet version.
    Follows SRP by separating dialog UI logic from App Controller.
    
    Args:
        page: The Flet page instance
        on_confirm_callback: Function to call when user confirms reset
    """
    
    # Get destructive button colors from theme
    confirm_bg = ThemeManager.current.destructive_bg
    confirm_text = ThemeManager.current.destructive_text
    
    def on_confirm(_):
        dlg.open = False
        page.update()
        if on_confirm_callback:
            on_confirm_callback()
    
    def on_cancel(_):
        dlg.open = False
        page.update()
    
    # Create styled dialog with FilledButton design
    dlg = ft.AlertDialog(
        modal=True,
        title_padding=ft.padding.only(top=30, bottom=10, left=30, right=30),
        content_padding=ft.padding.only(top=0, bottom=30, left=30, right=30),
        actions_padding=ft.padding.only(bottom=30, right=30, left=30),
        bgcolor=ThemeManager.current.card_bg,
        shape=ft.RoundedRectangleBorder(radius=12),
        
        # Title: XL Scale
        title=ft.Text(
            DesktopLocale.get("reset_defaults"),
            style=ThemeManager.get_text_style(scale="XL", weight=WeightScale.LG),
            text_align=ft.TextAlign.CENTER,
        ),
        
        # Content: L Scale
        content=ft.Container(
            content=ft.Text(
                DesktopLocale.get("reset_confirm_msg"),
                style=ThemeManager.get_text_style(scale="L", weight=WeightScale.MD, color=ThemeManager.current.text_secondary),
                text_align=ft.TextAlign.CENTER,
            ),
            width=400,
            padding=ft.padding.symmetric(vertical=10),
        ),
        
        # Actions: Styled FilledButton pair
        actions=[
            ft.Row([
                ft.Container(
                    content=ft.FilledButton(
                        DesktopLocale.get("cancel"),
                        on_click=on_cancel,
                        style=ft.ButtonStyle(
                            bgcolor={"": ThemeManager.current.hover_bg},
                            color={"": ThemeManager.current.text_primary},
                            text_style=ThemeManager.get_text_style(scale="BASE", weight=WeightScale.MD, color=ThemeManager.current.text_primary),
                        ),
                    ),
                    expand=True,
                ),
                ft.Container(
                    content=ft.FilledButton(
                        DesktopLocale.get("confirm"),
                        on_click=on_confirm,
                        style=ft.ButtonStyle(
                            bgcolor={"": confirm_bg},
                            color={"": confirm_text},
                            text_style=ThemeManager.get_text_style(scale="BASE", weight=WeightScale.MD, color=confirm_text),
                        ),
                    ),
                    expand=True,
                ),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=20),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    
    # Show dialog using overlay approach
    page.overlay.append(dlg)
    dlg.open = True
    page.update()
