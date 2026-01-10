"""
About Dialog Component
Big Tech minimalist style - clean and informative.
"""

import flet as ft
from typing import Optional

from ui.theme import ThemeManager, WeightScale


class AboutDialog:
    """Professional About Dialog - Big Tech minimalist style."""
    
    # App Information
    APP_NAME = "Vare"
    APP_VERSION = "0.5.0"
    APP_AUTHOR = "Cheng-Hsien Wu"
    APP_YEAR = "2026"
    APP_LICENSE = "MIT License"
    APP_GITHUB = "https://github.com/Cheng-Hsien-Wu/Vare-ASR"
    
    def __init__(self, page: ft.Page, on_close: Optional[callable] = None) -> None:
        self.page = page
        self.on_close = on_close
        self.container: Optional[ft.Container] = None
    
    def show(self) -> None:
        """Display the About dialog."""
        theme = ThemeManager.current
        
        # Dialog content - minimalist Big Tech style
        content = ft.Container(
            content=ft.Column(
                [
                    # App Icon - using actual logo
                    ft.Image(
                        src="logo_transparent.png",
                        width=100,
                        height=100,
                    ),
                    
                    ft.Container(height=20),
                    
                    # App Name
                    ft.Text(
                        self.APP_NAME,
                        style=ThemeManager.get_text_style(
                            "XXL", 
                            color=theme.text_primary, 
                            weight=WeightScale.XXL
                        ),
                    ),
                    
                    # Version
                    ft.Text(
                        f"Version {self.APP_VERSION}",
                        style=ThemeManager.get_text_style("SM", color=theme.text_secondary, weight=WeightScale.XL),
                    ),
                    
                    ft.Container(height=28),
                    
                    # GitHub Link - using url property (Flet recommended approach)
                    ft.TextButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.CODE_ROUNDED, size=16, color=theme.accent),
                            ft.Text("GitHub", style=ThemeManager.get_text_style("SM", color=theme.accent, weight=WeightScale.XL)),
                        ], spacing=6, tight=True),
                        url=self.APP_GITHUB,  # Flet will handle opening the URL
                    ),
                    
                    ft.Container(height=24),
                    
                    # License and Copyright
                    ft.Text(
                        self.APP_LICENSE,
                        style=ThemeManager.get_text_style("XS", color=theme.text_tertiary, weight=WeightScale.XL),
                    ),
                    ft.Text(
                        f"© {self.APP_YEAR} {self.APP_AUTHOR}",
                        style=ThemeManager.get_text_style("XS", color=theme.text_tertiary, weight=WeightScale.XL),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=2,
            ),
            width=360,
            padding=ft.Padding(32, 36, 32, 28),
            bgcolor=theme.card_bg,
            border_radius=12,
            border=ft.Border.all(1, theme.border),
            shadow=ft.BoxShadow(
                blur_radius=24,
                color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
            ),
        )
        
        # Modal overlay container
        self.container = ft.Container(
            content=ft.Stack(
                [
                    # Backdrop - click to close (use GestureDetector for cursor control)
                    ft.GestureDetector(
                        content=ft.Container(
                            bgcolor=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                            expand=True,
                        ),
                        on_tap=lambda _: self.close(),
                        mouse_cursor=ft.MouseCursor.BASIC,
                    ),
                    # Dialog (centered)
                    ft.Column(
                        [ft.Row([content], alignment=ft.MainAxisAlignment.CENTER)],
                        alignment=ft.MainAxisAlignment.CENTER,
                        expand=True,
                    ),
                ],
            ),
            expand=True,
        )
        
        # Add to overlay and update
        self.page.overlay.append(self.container)
        self.page.update()
    
    def close(self) -> None:
        """Close the dialog."""
        if self.container and self.container in self.page.overlay:
            self.page.overlay.remove(self.container)
            self.page.update()
        self.container = None
        if self.on_close:
            self.on_close()
