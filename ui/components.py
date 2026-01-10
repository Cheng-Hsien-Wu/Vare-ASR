"""
Fluent Design UI Components
Contains FluentCard, FluentButton, FluentTextField, FluentDropdown.
"""

import flet as ft
from typing import Any, Callable

from .theme import ThemeManager, FluentStyles, WeightScale


class FluentCard(ft.Container):
    """Fluent Design styled card container"""
    def __init__(self, content: ft.Control, padding: int = 20, width: int | None = None, height: int | None = None, **kwargs: Any) -> None:
        super().__init__(
            content=content,
            padding=padding,
            border=ft.Border.all(1, ThemeManager.current.border),
            border_radius=FluentStyles.BORDER_RADIUS,
            bgcolor=ThemeManager.current.card_bg,
            width=width,
            height=height,
            **kwargs,
        )

    def on_theme_changed(self) -> None:
        self.border = ft.Border.all(1, ThemeManager.current.border)
        self.bgcolor = ThemeManager.current.card_bg


class FluentButton(ft.Button):
    """Fluent Design styled button using native Button with ButtonStyle"""
    
    # Class-level style cache: key = (theme_mode, is_primary, font_size)
    _style_cache: dict = {}
    
    @classmethod
    def _get_cached_style(cls, is_primary: bool) -> ft.ButtonStyle:
        """Get cached style or create and cache new one"""
        cache_key = (ThemeManager.mode, is_primary, ThemeManager.get_font_size())
        
        if cache_key not in cls._style_cache:
            cls._style_cache[cache_key] = cls._create_style(is_primary)
        
        return cls._style_cache[cache_key]
    
    @classmethod
    def _create_style(cls, is_primary: bool) -> ft.ButtonStyle:
        """Create a new ButtonStyle (internal, use _get_cached_style instead)"""
        theme = ThemeManager.current
        font_size = ThemeManager.get_font_size()
        
        if is_primary:
            return ft.ButtonStyle(
                color={
                    ft.ControlState.DEFAULT: theme.accent_text,
                    ft.ControlState.HOVERED: theme.accent_text,
                    ft.ControlState.DISABLED: theme.text_disabled,
                },
                bgcolor={
                    ft.ControlState.DEFAULT: theme.accent,
                    ft.ControlState.HOVERED: theme.accent_light,
                    ft.ControlState.PRESSED: theme.accent_dark,
                    ft.ControlState.DISABLED: theme.mica_bg,
                },
                overlay_color=None,
                elevation={ft.ControlState.DEFAULT: 0, ft.ControlState.HOVERED: 1},
                animation_duration=150,
                padding=ft.Padding.symmetric(
                    horizontal=max(12, int(16 * font_size/16)), 
                    vertical=max(6, int(8 * font_size/16))
                ),
                shape=ft.RoundedRectangleBorder(radius=4),
            )
        else:
            return ft.ButtonStyle(
                color={
                    ft.ControlState.DEFAULT: theme.text_primary,
                    ft.ControlState.HOVERED: theme.text_primary,
                    ft.ControlState.DISABLED: theme.text_disabled,
                },
                bgcolor={
                    ft.ControlState.DEFAULT: theme.card_bg_secondary,
                    ft.ControlState.HOVERED: theme.hover_bg,
                    ft.ControlState.PRESSED: theme.pressed_bg,
                    ft.ControlState.DISABLED: theme.mica_bg,
                },
                overlay_color=None,
                elevation={ft.ControlState.DEFAULT: 0, ft.ControlState.HOVERED: 0},
                animation_duration=150,
                padding=ft.Padding.symmetric(
                    horizontal=max(12, int(16 * font_size/16)), 
                    vertical=max(6, int(8 * font_size/16))
                ),
                shape=ft.RoundedRectangleBorder(radius=4),
                side={
                    ft.ControlState.DEFAULT: ft.BorderSide(1, theme.border),
                    ft.ControlState.HOVERED: ft.BorderSide(1, theme.border_active),
                },
            )
    
    @classmethod
    def clear_style_cache(cls) -> None:
        """Clear style cache (call on theme/font change)"""
        cls._style_cache.clear()
    
    def __init__(self, text: str, icon: str | None = None, on_click: Callable | None = None, primary: bool = False, width: int | None = None, disabled: bool = False, tooltip: str | None = None) -> None:
        self.text_val = text
        self.icon_val = icon
        self.primary = primary
        self.disabled_state = disabled
        self.click_fn = on_click
        
        style = self._get_cached_style(primary)
        
        content_controls = []
        if icon:
            icon_size = ThemeManager.get_font_size() + 2
            self.icon_control = ft.Icon(icon, size=icon_size)
            content_controls.append(self.icon_control)
        
        self.text_control = ft.Text(
            text, 
            weight=WeightScale.MD, 
            size=ThemeManager.get_font_size(),
            font_family=FluentStyles.FONT_FAMILY
        )
        content_controls.append(self.text_control)
        
        super().__init__(
            content=ft.Row(content_controls, alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            on_click=self._handle_click,
            disabled=disabled,
            width=width,
            style=style,
            tooltip=tooltip
        )

    async def _handle_click(self, e: ft.ControlEvent) -> None:
        if self.click_fn:
            import inspect
            res = self.click_fn(e)
            if inspect.isawaitable(res):
                await res

    def on_theme_changed(self) -> None:
        # Cache is invalidated on theme change, get fresh cached style
        self.style = self._get_cached_style(self.primary)
        
        current_font_size = ThemeManager.get_font_size()
        
        if getattr(self, 'text_control', None):
             self.text_control.size = current_font_size
             
        if getattr(self, 'icon_control', None):
            self.icon_control.size = current_font_size + 2
        
    def set_disabled(self, disabled: bool) -> None:
        self.disabled_state = disabled
        self.disabled = disabled
        self.style = self._get_cached_style(self.primary)
        try:
            if self.page:
                self.update()
        except Exception:
            pass


class FluentDropdown(ft.Dropdown):
    """Fluent styled dropdown"""
    def __init__(self, **kwargs: Any) -> None:
        on_change_handler = kwargs.pop('on_change', None)
        super().__init__(
            bgcolor=ThemeManager.current.card_bg_secondary,  # Unified with TextField
            border_color=ThemeManager.current.border,
            focused_border_color=ThemeManager.current.accent,
            text_style=ft.TextStyle(color=ThemeManager.current.text_primary, size=ThemeManager.get_font_size(), weight=WeightScale.BASE),
            text_size=ThemeManager.get_font_size(),
            border_radius=4,
            **kwargs
        )
        # Note: We rely on text_style for native look and better performance.
        # Overriding individual option content with ft.Text creates massive overhead (e.g. 100+ controls for languages).

        if on_change_handler:
            self.on_select = on_change_handler
            
        # Subscribe to theme changes to handle font size updates dynamically
        ThemeManager.subscribe(self)
        
        # Apply initial styles
        self._apply_option_styles()

    def _apply_option_styles(self) -> None:
        """Ensure all options have correct text style in the dropdown list"""
        if not self.options:
            return
            
        font_size = ThemeManager.get_font_size()
        text_color = ThemeManager.current.text_primary
        
        for opt in self.options:
            # If option has text but no content (or content is auto-generated), wrap it
            # We check if content is None or if we previously set it (by checking type)
            if opt.text and (opt.content is None or isinstance(opt.content, ft.Text)):
                # We use ft.Text as content to control size in the list
                opt.content = ft.Text(
                    opt.text, 
                    size=font_size, 
                    color=text_color,
                    weight=WeightScale.BASE,
                    font_family=FluentStyles.FONT_FAMILY
                )

    def update(self) -> None:
        """Override update to ensure styles are applied before rendering"""
        self._apply_option_styles()
        super().update()

    def on_theme_changed(self) -> None:
        self.bgcolor = ThemeManager.current.card_bg_secondary
        self.border_color = ThemeManager.current.border
        self.focused_border_color = ThemeManager.current.accent
        self.text_style.color = ThemeManager.current.text_primary
        self.text_style.size = ThemeManager.get_font_size()
        self.text_size = ThemeManager.get_font_size() 
        self._apply_option_styles()
        try:
            if self.page:
                self.update()
        except Exception:
            pass


class FluentTextField(ft.TextField):
    """Fluent styled text field"""
    def __init__(self, text_size_offset: int = 0, **kwargs: Any) -> None:
        self.text_size_offset = text_size_offset
        
        defaults = {
            "bgcolor": ThemeManager.current.card_bg_secondary,
            "border_color": ThemeManager.current.border,
            "focused_border_color": ThemeManager.current.accent,
            "text_style": ft.TextStyle(color=ThemeManager.current.text_primary, size=ThemeManager.get_font_size(text_size_offset), weight=WeightScale.BASE),
            "border_radius": 4,
            "selection_color": "#b3d4fc" if ThemeManager.mode == "light" else "#4a6785",  
            "cursor_color": ThemeManager.current.accent,
            "hint_style": ft.TextStyle(color=ThemeManager.current.text_tertiary),
        }
        
        for key, value in kwargs.items():
            defaults[key] = value
            
        super().__init__(**defaults)

    def on_theme_changed(self) -> None:
        self.bgcolor = ThemeManager.current.card_bg_secondary
        self.border_color = ThemeManager.current.border
        self.focused_border_color = ThemeManager.current.accent
        self.text_style.color = ThemeManager.current.text_primary
        self.text_style.size = ThemeManager.get_font_size(self.text_size_offset)
        self.selection_color = ThemeManager.current.accent_dark
        self.cursor_color = ThemeManager.current.accent
        self.hint_style.color = ThemeManager.current.text_tertiary

    def set_disabled(self, disabled: bool) -> None:
        """Set disabled state with visual feedback"""
        self.disabled = disabled
        # Visually show disabled state by changing opacity
        self.opacity = 0.5 if disabled else 1.0
        try:
            if self.page:
                self.update()
        except Exception:
            pass
