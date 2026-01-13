import flet as ft
from typing import TYPE_CHECKING

from ui.theme import ThemeManager, WeightScale
from ui.nav_button import FluentNavButton
from core.i18n.localization import DesktopLocale

if TYPE_CHECKING:
    from app import VareApp

class MainLayout(ft.Container):
    """
    Main application layout encapsulating TitleBar, Sidebar, and Content Area.
    Uses Flet Refs for efficient updates and strict visual preservation.
    """
    def __init__(self, app: "VareApp", page_views: list[ft.Control]) -> None:
        super().__init__()
        self.app = app
        self.page_views = page_views
        self.expand = True
        self.bgcolor = ThemeManager.current.mica_bg
        self.border_radius = 8
        self.shadow = ft.BoxShadow(
            spread_radius=1,
            blur_radius=10,
            color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK),
        )
        
        # Refs for UI updates
        self.title_bar_icon = ft.Ref[ft.Icon]()
        self.title_bar_text = ft.Ref[ft.Text]()
        self.title_bar_bg = ft.Ref[ft.Container]()
        self.sidebar_ref = ft.Ref[ft.Container]()
        self.content_container = ft.Ref[ft.Container]()
        self.win_btn_row = ft.Ref[ft.Row]()
        
        self.nav_buttons = []
        
        # Build strict layout
        self.content = self._build_structure()

    def _build_structure(self) -> ft.Column:
        import platform
        system = platform.system()
        is_windows = system == "Windows"
        is_macos = system == "Darwin"
        
        main_col_controls = []
        
        # 1. Custom Title Bar (Windows & macOS United)
        # Windows: Full custom buttons
        # macOS: Custom header with left padding, no buttons (traffic lights native)
        if is_windows or is_macos:
            title_bar = self._build_title_bar(is_macos=is_macos)
            main_col_controls.append(title_bar)
        
        # 2. Sidebar & Content
        sidebar = self._build_sidebar()
        
        # 3. Content Container
        # Fixed padding preserved: left=60, top=10, bottom=20
        # No right padding (handled by pages)
        content_area = ft.Container(
            ref=self.content_container,
            content=self.page_views[0], # Default to first page
            expand=True,
            padding=ft.Padding.only(left=60, top=10, bottom=20),
            bgcolor=ThemeManager.current.mica_bg,
            border_radius=ft.BorderRadius.only(top_left=8),
        )
        
        # Main Layout Body (Sidebar + Content)
        body = ft.Row(
            [sidebar, content_area],
            spacing=0,
            expand=True,
        )
        main_col_controls.append(body)
        
        # Main Layout Column
        return ft.Column(main_col_controls, spacing=0, expand=True)

    def _build_title_bar(self, is_macos: bool = False) -> ft.Row:
        # Icon and Text (Windows Only)
        # on macOS, standard apps usually don't show window icon, and title is often centered or hidden in unified bars.
        # We will keep it clean (Hidden) for macOS as requested.
        
        content_controls = []
        
        if not is_macos:
            # Windows: Icon + Text (use rounded square icon)
            icon = ft.Image(src="vare_dark_round_corner_sqaure_icon.png", width=24, height=24)
            text = ft.Text("    Vare", size=14, weight=WeightScale.BASE, color=ThemeManager.current.text_primary, ref=self.title_bar_text)
            
            content_controls = [
                ft.Container(width=16),
                icon,
                text
            ]
        else:
            # macOS: Just empty spacing to push content away from traffic lights, or just empty if purely drag area
            # Empty drag area requires Container height without padding content.
            # But the row needs alignment.
            content_controls = [] 

        bg_container = ft.Container(
            ref=self.title_bar_bg,
            bgcolor=ThemeManager.current.mica_bg,
            height=32,
            content=ft.Row(
                content_controls, 
                alignment=ft.MainAxisAlignment.START, 
                spacing=0
            ),
        )
        
        # Drag Content Wrapper
        drag_content = ft.GestureDetector(
            content=bg_container,
            on_double_tap=lambda _: self.page.run_task(self._maximize_window),
        )
        
        title_bar_row_controls = [
            ft.WindowDragArea(
                content=drag_content,
                expand=True,
                maximizable=False,
            )
        ]
        
        # Window Buttons (Windows Only)
        if not is_macos:
            win_buttons = self._build_window_buttons()
            title_bar_row_controls.append(win_buttons)
            
        # Final Row
        return ft.Row(title_bar_row_controls, spacing=0, height=32)

    def _build_window_buttons(self) -> ft.Row:
        # Styles
        win_btn_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            padding=0,
            overlay_color={
                ft.ControlState.HOVERED: ThemeManager.current.win_btn_hover_overlay,
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
            },
        )
        
        close_btn_style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=0),
            padding=0,
            overlay_color={
                ft.ControlState.HOVERED: ThemeManager.current.win_close_hover_bg,
                ft.ControlState.DEFAULT: ft.Colors.TRANSPARENT,
            },
        )
        
        buttons = ft.Row([
            ft.IconButton(
                icon=ft.Icons.REMOVE, icon_size=16, icon_color=ThemeManager.current.text_primary,
                width=46, height=32, style=win_btn_style,
                on_click=lambda _: self.page.run_task(self._minimize_window),
                data="min"
            ),
            ft.IconButton(
                icon=ft.Icons.SQUARE_OUTLINED, icon_size=12, icon_color=ThemeManager.current.text_primary,
                width=46, height=32, style=win_btn_style,
                on_click=lambda _: self.page.run_task(self._maximize_window),
                data="max"
            ),
            ft.IconButton(
                icon=ft.Icons.CLEAR, icon_size=16, icon_color=ThemeManager.current.text_primary,
                width=46, height=32, style=close_btn_style,
                on_click=lambda _: self.page.run_task(self._close_window),
                data="close"
            )
        ], spacing=0, ref=self.win_btn_row)
        
        return buttons

    def _build_sidebar_content(self) -> ft.Column:
        """Helper to build sidebar content (nav buttons + footer)"""
        nav_items = [
            (ft.Icons.HOME_ROUNDED, "home", 0),
            (ft.Icons.SETTINGS_ROUNDED, "settings", 1),
            (ft.Icons.TERMINAL_ROUNDED, "logs", 2),
        ]
        
        self.nav_buttons = []
        current_page = self.app.current_page if hasattr(self.app, 'current_page') else 0
        
        for icon, label_key, idx in nav_items:
            label_text = DesktopLocale.get(label_key)
            btn = FluentNavButton(icon, label_text, idx, self.switch_page, selected=(idx == current_page))
            self.nav_buttons.append(btn)
            
        nav_column = ft.Column(self.nav_buttons, spacing=4)
        
        footer = ft.Column([
            FluentNavButton(ft.Icons.INFO_OUTLINE_ROUNDED, DesktopLocale.get("about"), 3, 
                           lambda _: self.app._show_about_dialog(None)),
        ], spacing=4)
        
        return ft.Column([
            ft.Container(height=10),
            ft.Container(height=10),
            nav_column,
            ft.Container(expand=True),
            footer,
            ft.Container(height=10),
        ], spacing=0)

    def _build_sidebar(self) -> ft.Container:
        # Sidebar Construction
        content_col = self._build_sidebar_content()
        
        # New Reference for Sidebar Container update
        return ft.Container(
            ref=self.sidebar_ref,
            content=content_col,
            width=240,
            bgcolor=ThemeManager.current.nav_bg,
            padding=ft.Padding.symmetric(horizontal=4),
        )

    # Window Actions
    async def _minimize_window(self) -> None:
        self.page.window.minimized = True
        self.page.update()

    async def _maximize_window(self) -> None:
        self.page.window.maximized = not self.page.window.maximized
        self.page.update()

    async def _close_window(self) -> None:
        # Delegate close logic to app if complex (e.g. saving state)
        # Using the logic from app.py
        if hasattr(self.app, '_close_window'):
            await self.app._close_window()
        else:
            self.page.window.close()

    # Navigation
    def switch_page(self, index: int, force_update: bool = False) -> None:
        if self.app.current_page == index and not force_update:
            return
            
        # Update buttons
        for i, btn in enumerate(self.nav_buttons):
            btn.set_selected(i == index)
        
        # Reset settings page state if leaving settings (Index 1 is Settings)
        if self.app.current_page == 1 and index != 1:
            if hasattr(self.app, '_settings_page') and self.app._settings_page:
                 self.app._settings_page.reset_state()
            
        # Switch content
        self.app.current_page = index
        if self.content_container.current:
            self.content_container.current.content = self.page_views[index]
            
            # Read-only check for settings
            if index == 1 and getattr(self.app, 'is_processing', False):
                if hasattr(self.app, '_settings_page'):
                    self.app._settings_page.set_read_only(True)
            
            self.content_container.current.update()

    # Theme Update
    def update_theme(self) -> None:
        theme = ThemeManager.current
        
        # Main Container
        self.bgcolor = theme.mica_bg
        
        # Title Bar
        if self.title_bar_bg.current:
            self.title_bar_bg.current.bgcolor = theme.mica_bg
        # Note: title_bar_icon is now ft.Image, no color update needed
        if self.title_bar_text.current:
            self.title_bar_text.current.color = theme.text_primary
            
        # Window Buttons
        if self.win_btn_row.current:
             hover_color = theme.win_btn_hover_overlay
             for btn in self.win_btn_row.current.controls:
                 if isinstance(btn, ft.IconButton):
                     btn.icon_color = theme.text_primary
                     
                     if btn.data in ("min", "max"):
                         if btn.style and btn.style.overlay_color:
                             btn.style.overlay_color[ft.ControlState.HOVERED] = hover_color
                     elif btn.data == "close":
                         if btn.style and btn.style.overlay_color:
                             # Close button uses distinct hover color (red)
                             btn.style.overlay_color[ft.ControlState.HOVERED] = theme.win_close_hover_bg
                     
                     btn.update()

        # Sidebar
        if self.sidebar_ref.current:
            self.sidebar_ref.current.bgcolor = theme.nav_bg
            # Note: NavButtons handle their own theme updates via ThemeManager subscription


        # Content Container
        if self.content_container.current:
            self.content_container.current.bgcolor = theme.mica_bg
            
        # Rebuild pages Logic:
        # Currently, layout updates colors directly. Page content updates are handled by
        # individual components subscribing to ThemeManager or via app-level rebuilds.
        
        self.update()

    def update_labels(self) -> None:
        """Update localized labels on language change"""
        # Rebuild Nav Buttons with new locale
        nav_items = [
            ("home", 0),
            ("settings", 1),
            ("logs", 2),
        ]
        
        # We need to iterate existing buttons and update their text.
        # But FluentNavButton structure might be complex (icon + text).
        # Assuming FluentNavButton has a 'label' property or we can rebuild.
        # Looking at _build_sidebar, self.nav_buttons holds the buttons.
        
        # Iterate existing buttons to update text.
        # Since _build_sidebar returns a Container(ref=self.sidebar_ref),
        # we rebuild the content of that container.
        
        
        if self.sidebar_ref.current:
             # Re-run logic from helper
             new_content = self._build_sidebar_content()
             
             self.sidebar_ref.current.content = new_content
             self.sidebar_ref.current.update()
