"""
Fluent Navigation Button Component
Sidebar navigation button with selection indicator.
"""

import flet as ft
from typing import Callable

from .theme import ThemeManager, FluentStyles, WeightScale


class FluentNavButton(ft.Container):
    """Fluent sidebar navigation button"""
    def __init__(self, icon: str, label: str, index: int, on_click: Callable[[int], None], selected: bool = False) -> None:
        self.index = index
        self.label_text = label
        self.selected = selected
        self.click_fn = on_click
        self.icon_name = icon
        
        self.indicator = ft.Container(
            width=3, 
            height=16, 
            bgcolor=ThemeManager.current.accent if selected else "transparent",
            border_radius=4,
            animate=ft.Animation(300, "easeOut"),
        )
        
        self.icon_view = ft.Icon(
            icon, 
            size=18,
            color=self._get_content_color()
        )
        
        self.label_view = ft.Text(
            label,
            size=ThemeManager.get_font_size(),
            weight=WeightScale.LG if selected else WeightScale.BASE,
            color=self._get_content_color(),
            visible=True
        )
        
        content = ft.Row(
            [
                self.indicator,
                ft.Container(width=10),
                self.icon_view,
                ft.Container(width=12),
                self.label_view
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.START,
        )
        
        super().__init__(
            content=content,
            height=FluentStyles.NAV_ITEM_HEIGHT,
            width=218,
            margin=ft.Margin.only(left=12, right=10),
            border_radius=6,
            on_click=lambda _: on_click(index),
            ink=True,
            ink_color=ThemeManager.current.nav_hover_bg,
            bgcolor=ThemeManager.current.nav_hover_bg if selected else "transparent"
        )
        ThemeManager.subscribe(self)
        # Ensure initial visual state matches selection
        self._update_state(do_update=False)

    def _get_content_color(self) -> str:
        if self.selected:
            return ThemeManager.current.text_primary
        return ThemeManager.current.text_secondary

    def _update_state(self, do_update: bool = True) -> None:
        theme = ThemeManager.current
        self.indicator.bgcolor = theme.accent if self.selected else "transparent"
        
        color = self._get_content_color()
        self.icon_view.color = color
        self.label_view.color = color
        self.label_view.weight = WeightScale.LG if self.selected else WeightScale.MD
        
        if self.selected:
            self.bgcolor = theme.nav_hover_bg
        else:
            self.bgcolor = "transparent"
            
        # Update ink color for ripple effect
        self.ink_color = theme.nav_hover_bg

        if do_update and self.page:
            self.update()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._update_state()

    def on_theme_changed(self) -> None:
        self._update_state(do_update=False)
