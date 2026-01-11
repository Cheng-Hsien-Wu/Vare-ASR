import flet as ft
import sys
import logging
import threading
import json
import asyncio
from pathlib import Path
from typing import List, Optional
from core.i18n.localization import DesktopLocale
from core.constants.srt_languages import WHISPER_LANGUAGES
from core.settings import UserSettings
from datetime import datetime

# UI Components

from ui.theme import FluentColors, FontScale, TextScale, FluentStyles, ThemeManager, WeightScale
from ui.components import FluentCard, FluentButton, FluentDropdown, FluentTextField
from ui.nav_button import FluentNavButton
from ui.layout import MainLayout

# Core modules
from core.events import EventBus, Events
from core.notifications import NotificationManager
from core import secure_storage

# Controllers
from controllers.task_controller import TaskController

# Features
from features.transcription.models import TranscriptionTask
from features.transcription.worker import TranscriptionWorker

# Pages
from pages.logs_page import LogsPage
from pages.settings_page import SettingsPage
from pages.task_page import TaskPage

# ==========================================
# Main Application
# ==========================================

logger = logging.getLogger(__name__)

class VareApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        
        self.current_worker: Optional[TranscriptionWorker] = None
        self.processing_index = 0
        self.is_processing = False
        
        # UI References
        self.nav_buttons = []
        self.page_views = []
        self.current_page = 0
        
        # Task interface controls
        self.task_table = None
        self.start_btn = None
        self.stop_btn = None
        
        # Log control
        self.log_view = None
        
        # Flag to prevent event handling during startup
        self._init_complete = False
        
        # Initialize controllers and managers
        self.task_controller = TaskController(page)
        NotificationManager.set_page(page)
        NotificationManager.set_log_callback(self._log)
        
        # Setup TaskController callbacks
        self.task_controller.set_log_callback(self._log)
        
        
        # Subscribe to EventBus events for UI updates
        EventBus.subscribe(Events.PROCESSING_STARTED, self._on_processing_started)
        EventBus.subscribe(Events.PROCESSING_STOPPED, self._on_processing_stopped)
        EventBus.subscribe(Events.PROCESSING_FINISHED, self._on_processing_finished)
        EventBus.subscribe(Events.TASK_STATUS_CHANGED, self._on_task_status_changed)
        EventBus.subscribe(Events.TASKS_CHANGED, self._on_tasks_changed)
        
        # Subscribe to Settings Events
        EventBus.subscribe(Events.APP_LANGUAGE_CHANGED, self._on_language_changed)
        EventBus.subscribe(Events.THEME_CHANGED, self._on_theme_changed_evt)
        EventBus.subscribe(Events.TEXT_SCALE_CHANGED, self._on_text_scale_changed_evt)
        EventBus.subscribe(Events.BROWSE_MODEL_DIR_REQUESTED, self._on_browse_model_dir_requested)
        EventBus.subscribe(Events.BROWSE_OUTPUT_DIR_REQUESTED, self._on_browse_output_dir_requested)
        EventBus.subscribe(Events.LLM_TEST_CONNECTION_REQUESTED, self._on_llm_test_connection_requested)
        EventBus.subscribe(Events.OUTPUT_FORMAT_CHANGED, self._on_output_format_changed)
        
        self.setup_page()
        self.build_ui()
    
    def __del__(self):
        # Cleanup subscriptions
        try:
            ThemeManager.unsubscribe(self)
            EventBus.unsubscribe(Events.APP_LANGUAGE_CHANGED, self._on_language_changed)
            EventBus.unsubscribe(Events.BROWSE_MODEL_DIR_REQUESTED, self._on_browse_model_dir_requested)
            EventBus.unsubscribe(Events.BROWSE_OUTPUT_DIR_REQUESTED, self._on_browse_output_dir_requested)
            EventBus.unsubscribe(Events.LLM_TEST_CONNECTION_REQUESTED, self._on_llm_test_connection_requested)
        except (ImportError, Exception):
            pass

    @property
    def tasks(self) -> List[TranscriptionTask]:
        """Get tasks from controller (Single Source of Truth)"""
        if getattr(self, 'task_controller', None):
            return self.task_controller.tasks
        return []

    def setup_page(self) -> None:
        """Configure page settings"""
        # Window attributes (Cross-platform logic)
        import platform
        system = platform.system()
        is_windows = system == "Windows"
        is_macos = system == "Darwin"
        
        # Unified Title Bar Strategy:
        # Windows: Hidden frame + Custom drawn buttons
        # macOS: Hidden frame + Native Traffic Lights (buttons visible)
        # Linux: Native frame
        
        if is_windows:
            self.page.window.title_bar_hidden = True
            self.page.window.title_bar_buttons_hidden = True
        elif is_macos:
            self.page.window.title_bar_hidden = True
            self.page.window.title_bar_buttons_hidden = False
        else:
            self.page.window.title_bar_hidden = False
            self.page.window.title_bar_buttons_hidden = False
        
        # Auto-detect language
        DesktopLocale.init()
        self.page.locale = DesktopLocale.current_lang # Set Flet internal locale
        
        self.page.title = DesktopLocale.get("app_title")
        
        # Set window icon (using black-background version for taskbar visibility)
        import os
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")
        icon_path = os.path.join(assets_dir, "vare_dark_sqaure_icon.png")  # Black bg for system
        if os.path.exists(icon_path):
            self.page.window.icon = icon_path
        
        self.page.window.min_width = 960
        self.page.window.min_height = 540
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = ft.Colors.TRANSPARENT
        self.page.window.bgcolor = ft.Colors.TRANSPARENT
        self.page.padding = 0
        
        # Register custom fonts
        self.page.fonts = {
            #"Inter": "Inter-VariableFont_opsz,wght.ttf",
            "Noto Sans TC": "NotoSansTC-VariableFont_wght.ttf",
        }
        
        # Configure tooltips and scrollbars
        tooltip_style = ThemeManager.get_text_style("SM", color=ft.Colors.WHITE, weight=WeightScale.BASE)
        self.page.theme = ft.Theme(
            tooltip_theme=ft.TooltipTheme(
                text_style=tooltip_style,
                decoration=ft.BoxDecoration(
                    bgcolor=ft.Colors.with_opacity(0.95, ThemeManager.current.tooltip_bg), # Slightly more opaque
                    border_radius=6,
                ),
                padding=8, # Tighter padding
                wait_duration=500, # Delay before showing
            ),
            scrollbar_theme=ft.ScrollbarTheme(
                thumb_color=ThemeManager.current.scrollbar_thumb,  # Visible gray thumb from theme
                track_color=ThemeManager.current.scrollbar_track,  # Light/Dark track from theme
                thickness=8,
                radius=4,
            ),
            font_family=FluentStyles.FONT_FAMILY
        )
        
        # Initialize user settings persistence
        UserSettings.init()
        
        # Restore saved window state (position, size, maximized)
        self._restore_window_state()
        
        # Init ThemeManager with saved theme preference
        ThemeManager.page = self.page
        saved_theme = UserSettings.get("theme", "dark")
        ThemeManager.set_theme(saved_theme)
        
        # Load saved language preference
        saved_lang = UserSettings.get("language", "zh-tw")
        DesktopLocale.set_locale(saved_lang)
        
        # Load saved font size preference
        saved_font = UserSettings.get("font_size", "default")
        TextScale.current = saved_font
        
        # Start background detection of supported compute types (CPU + GPU)
        # This runs in a daemon thread and caches results for instant access later
        from core.device_detection import ComputeTypeCache
        ComputeTypeCache.start_detection()
        
        # One-time migration: transfer API key from settings.json to keyring
        if secure_storage.migrate_from_settings(UserSettings.get_all()):
            # Clear the old key from settings.json after successful migration
            if "llm_api_key" in UserSettings._settings:
                del UserSettings._settings["llm_api_key"]
                UserSettings.save()
        
        # Prevent default close - we handle it ourselves
        self.page.window.prevent_close = True
        
        # Enable window events (file drop handled by Dropzone control)
        # Unified Window Event Handler
        self.page.window.on_event = self._handle_window_event        
        # Track maximize state for reliable detection
        self._last_maximized = False

        # Debounce timer for window saving
        self._save_timer = None
        
        # Pre-initialize SnackBar for performance (re-use instance)
        self._snackbar_content = ft.Row(spacing=10)
        self._snackbar = ft.SnackBar(
            content=self._snackbar_content,
            bgcolor=ThemeManager.current.card_bg,
            duration=3000,
        )
        self.page.snack_bar = self._snackbar
    def build_ui(self) -> None:
        """Build main UI layout"""
        # Initialize tooltip theme
        self._update_tooltip_theme()
        
        # Create page class instances with app reference
        self._task_page = TaskPage(self.page, self)
        self._settings_page = SettingsPage(self.page, self)
        self._logs_page = LogsPage(self.page, self)
        
        self.page_views = [
            self._task_page.build(),
            self._settings_page.build(),
            self._logs_page.build(),
        ]
        
        # Instantiate Main Layout
        self.main_container = MainLayout(self, self.page_views)
        self.page.add(self.main_container)
        
        ThemeManager.subscribe(self)
        
        # Pre-load heavy modules in background for faster first use
        self._warmup_heavy_modules()
    
    def _warmup_heavy_modules(self) -> None:
        """Pre-load heavy modules in background to eliminate first-click delay"""
        def warmup():
            import time
            time.sleep(2)  # Wait for app to fully start
            try:
                # Pre-import media download dialog (loads yt_dlp)
                from features.media_download.dialog import MediaDownloadDialog
                logger.debug("Heavy modules pre-loaded successfully")
            except Exception:
                pass  # Non-critical, ignore failures
        
        import threading
        threading.Thread(target=warmup, daemon=True, name="ModuleWarmup").start()

    def on_theme_changed(self) -> None:
        """Handle theme change for app-level structure (called by ThemeManager)"""
        # Clear old component subscriptions (keep only this app)
        ThemeManager.clear_component_listeners(keep_app=self)
        
        # Delegate update to MainLayout
        if getattr(self, 'main_container', None):
            self.main_container.update_theme()
        
        # Rebuild all pages to apply new theme
        self.page_views = [
            self._task_page.build(),
            self._settings_page.build(),
            self._logs_page.build(),
        ]
        
        # Update MainLayout content with new pages
        if getattr(self, 'main_container', None):
            self.main_container.page_views = self.page_views
            self.main_container.switch_page(self.current_page, force_update=True)
        
        # Update scrollbar theme (keep this, it's page-level)
        if self.page.theme and self.page.theme.scrollbar_theme:
            self.page.theme.scrollbar_theme.thumb_color = ThemeManager.current.scrollbar_thumb
            self.page.theme.scrollbar_theme.track_color = ThemeManager.current.scrollbar_track
        
        self.page.update()

    def update_ui_state(self, is_processing: bool) -> None:
        """Unified UI state management for processing/idle states"""
        self.is_processing = is_processing
        
        # 1. Update internal state if controller is present
        if getattr(self, 'task_controller', None):
            self.task_controller.is_processing = is_processing
            
        # 2. Lock/Unlock Task Page (Buttons, Action Rows)
        if self._task_page:
            self._task_page.set_processing_state(is_processing)
            
        # 3. Lock/Unlock Settings Page (All inputs)
        if self._settings_page:
            self._settings_page.set_read_only(is_processing)
            
        # 4. Update Page (apply changes)
        if self.page:
            self.page.update()


    def _close_dialog(self) -> None:
        """Close current dialog"""
        if self.page.dialog:
            self.page.dialog.open = False
            self.page.update()
    

    
    # ==========================================
    # Config Collection for TaskController
    # ==========================================
    

    
    
    # ==========================================
    # EventBus Event Handlers (UI Updates)
    # ==========================================
    
    def _on_processing_started(self, data: dict | None) -> None:
        """Handle PROCESSING_STARTED event - update UI state."""
        # Ensure UI updates run on main thread
        if self.page:
            self.page.run_task(self._do_processing_started)
    
    async def _do_processing_started(self) -> None:
        """Actual UI update for processing started."""
        self.update_ui_state(True)
    
    def _on_processing_stopped(self, data: dict | None) -> None:
        """Handle PROCESSING_STOPPED event - restore UI state."""
        if self.page:
            self.page.run_task(self._do_processing_stopped)
    
    async def _do_processing_stopped(self) -> None:
        """Actual UI update for processing stopped."""
        self.update_ui_state(False)
        self._show_snackbar(DesktopLocale.get("processing_stopped"), success=True)
    
    def _on_processing_finished(self, data: dict | None) -> None:
        """Handle PROCESSING_FINISHED event - show results and restore UI."""
        if self.page:
            self.page.run_task(self._do_processing_finished, data)
    
    async def _do_processing_finished(self, data: dict | None) -> None:
        """Actual UI update for processing finished."""
        self.update_ui_state(False)
        
        completed = data.get('completed', 0) if data else 0
        failed = data.get('failed', 0) if data else 0
        
        if completed > 0:
            msg = f"{completed} {DesktopLocale.get('processing_completed')}, {failed} {DesktopLocale.get('processing_failed')}"
            self._show_snackbar(msg, success=True)
            


    
    def _on_task_status_changed(self, data: dict | None) -> None:
        """Handle TASK_STATUS_CHANGED event - update table."""
        if self.page and self._task_page:
            # Delegate to TaskPage using proper async wrapper
            async def update_row():
                if isinstance(data, dict) and 'index' in data:
                    self._task_page.update_single_row(data['index'])
                else:
                    self._task_page.update_table()
            self.page.run_task(update_row)
    
    def _on_tasks_changed(self, data: list | None) -> None:
        """Handle TASKS_CHANGED event - sync tasks and update view."""
        if self.page:
            self.page.run_task(self._do_tasks_changed, data)
    
    async def _do_tasks_changed(self, data: list | None) -> None:
        """Actual UI update for tasks changed."""
        # Note: self.tasks refers to controller.tasks using property, no sync needed.
        if self._task_page:
            self._task_page.update_view()
            self._task_page.update_table()
    
    # ==========================================
    # Processing Control (delegates to TaskController)
    # ==========================================

    def _start_processing(self, e: ft.ControlEvent) -> None:
        """Start batch processing - delegates to TaskController."""

        
        if not self.tasks:
            self._show_snackbar(DesktopLocale.get("no_files_found"), success=False)
            return
        
        # Start processing via controller
        self.task_controller.start_processing()

    def _stop_processing(self, e: ft.ControlEvent) -> None:
        """Stop processing - delegates to TaskController."""
        self.task_controller.stop_processing()

    async def _close_window(self) -> None:
        """Close the window using workaround for Flet issue #5180"""
        self.page.window.prevent_close = False
        self.page.window.on_event = None # Remove event listener to prevent recursion
        self.page.update()
        await self.page.window.close()
        import sys
        sys.exit(0)

    async def _graceful_shutdown(self) -> None:
        """Perform graceful shutdown to reduce async warnings"""
        # Prevent re-entry
        if getattr(self, '_shutting_down', False):
            return
        self._shutting_down = True
        
        # Cancel any pending save timer
        if getattr(self, '_save_timer', None) and self._save_timer.is_alive():
            self._save_timer.cancel()
        
        # Stop any ongoing processing
        if getattr(self, 'task_controller', None):
            try:
                self.task_controller.stop_processing()
            except Exception:
                pass
        
        # Save window state
        self._save_window_state()
        
        # Cancel all pending asyncio tasks except this one
        try:
            current_task = asyncio.current_task()
            pending = [t for t in asyncio.all_tasks() if t is not current_task and not t.done()]
            
            for task in pending:
                task.cancel()
            
            # Wait briefly for tasks to handle cancellation
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
        except Exception:
            pass
        
        # Disable prevent_close and use close for proper cleanup
        try:
            self.page.window.prevent_close = False
            self.page.window.on_event = None  # Remove event handler to prevent recursion
            await asyncio.sleep(0.05)  # Small delay for Flet socket cleanup
            await self.page.window.close()
        except Exception:
            # Fallback to destroy if close fails
            self.page.window.destroy()

    def _show_about_dialog(self, e: ft.ControlEvent | None) -> None:
        """Show about dialog"""
        from ui.dialogs import AboutDialog
        dialog = AboutDialog(self.page)
        dialog.show()

    def _show_dialog(self, title: str, message: str) -> None:
        """Show alert dialog"""
        dialog = ft.AlertDialog(
            title=ft.Text(title, color=ThemeManager.current.text_primary),
            content=ft.Text(message, color=ThemeManager.current.text_secondary),
            bgcolor=ThemeManager.current.card_bg,
            actions=[
                ft.TextButton(
                    DesktopLocale.get("ok"),
                    on_click=lambda _: self._close_dialog(),
                    style=ft.ButtonStyle(color=ThemeManager.current.accent)
                )
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _show_snackbar(self, message: str, success: bool = True) -> None:
        """Show snackbar notification (optimized reuse)"""
        # Update colors based on current theme
        self._snackbar.bgcolor = ThemeManager.current.card_bg
        color = ThemeManager.current.text_primary
        icon_color = ThemeManager.current.success if success else ThemeManager.current.error
        
        # Update content directly
        self._snackbar_content.controls = [
            ft.Icon(
                ft.Icons.CHECK_CIRCLE_ROUNDED if success else ft.Icons.ERROR_ROUNDED,
                color=icon_color
            ),
            ft.Text(message, color=color),
        ]
        self._snackbar.open = True
        
        # Force page update from any thread (Flet 0.25+ supports this)
        try:
            self.page.snack_bar.open = True
            self.page.update()
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"DEBUG: Failed to update snackbar: {e}")
            pass



    def _on_theme_changed(self) -> None:
        """Handle theme change for app-level structure (called by ThemeManager)"""
        theme = ThemeManager.current
        
        # Main Window Frame
        if getattr(self, 'main_container', None):
            self.main_container.bgcolor = theme.mica_bg
            self.main_container.border = ft.border.all(1, theme.border)
            
            # Title Bar (Index 0 of Column)
            try:
                title_bar_drag = self.main_container.content.controls[0]
                if isinstance(title_bar_drag, ft.WindowDragArea):
                    title_bar_container = title_bar_drag.content
                    title_bar_container.bgcolor = theme.mica_bg
                    # Update icons in title bar
                    title_row = title_bar_container.content
                    # Icon: controls[1]
                    title_row.controls[1].color = theme.text_secondary
                    # Text: controls[2]
                    title_row.controls[2].color = theme.text_secondary
                    # Min/Close buttons: controls[4], controls[5]
                    title_row.controls[4].icon_color = theme.text_primary
                    title_row.controls[5].icon_color = theme.text_primary
            except Exception:
                pass  # structure might differ
        
        # Content Container
        if getattr(self, 'content_container', None):
            self.content_container.bgcolor = theme.mica_bg
            
        self.page.update()

    def _on_theme_changed_evt(self, theme_mode: str) -> None:
        """Handle theme change event from EventBus"""
        # ThemeManager already updated by sender, just need to update UI
        # (Actually, ThemeManager updates components automatically, but we might have app-specific logic)
        self.page.update()

    def _on_language_changed(self, lang_code: str) -> None:
        """Handle app language change event from EventBus"""
        try:
            DesktopLocale.set_locale(lang_code)
            ThemeManager.notify_listeners()
            self.page.update()
            
            # Rebuild sidebar (MainLayout logic)
            if self.main_container:
                self.main_container.update_labels()
                self.main_container.switch_page(self.current_page, force_update=True)
                
            self._show_snackbar(DesktopLocale.get("settings_title"), success=True)
        except Exception as e:
            logger.error(f"Error handling language change: {e}")
    
    def _on_text_scale_changed_evt(self, scale: float) -> None:
        """Handle text scale change event from EventBus"""
        self._update_tooltip_theme()
        ThemeManager.notify_listeners()
        self.page.update()
        
    # Deprecated handlers (unused now)




    def _update_tooltip_theme(self) -> None:
        """Update global tooltip theme to match text scale"""
        try:
            scale = TextScale.get_multiplier()
            font_size = int(14 * scale)
            if self.page:
                if not self.page.theme:
                    self.page.theme = ft.Theme()
                
                # Check if TooltipTheme is supported
                if hasattr(ft, "TooltipTheme") and hasattr(self.page.theme, "tooltip_theme"):
                    if not self.page.theme.tooltip_theme:
                        self.page.theme.tooltip_theme = ft.TooltipTheme()
                    
                    self.page.theme.tooltip_theme.text_style = ft.TextStyle(size=font_size)
                    # Update page to apply changes if visible
                    # self.page.update() 
        except Exception:
            # Helper feature - safe to ignore on older Flet versions
            pass



    
    def _log(self, message: str | tuple) -> None:
        """Add message to log view with timestamp"""
        # Handle tuple messages from worker (locale key, *args)
        if isinstance(message, tuple):
            key = message[0]
            args = message[1:] if len(message) > 1 else ()
            localized = DesktopLocale.get(key)
            # Format with positional args if present
            if args and '{' in localized:
                try:
                    message = localized.format(*args)
                except (IndexError, KeyError):
                    message = f"{localized}: {args}"
            elif args:
                message = f"{localized}: {args[0]}"
            else:
                message = localized
        
        # Format: [HH:MM:SS] message
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {message}"
        
        # Log to system logger as well
        logger.info(message)
        
        # Flet 0.80: accessing .page on unmounted control raises RuntimeError
        try:
            if self.log_view and self.log_view.page:
                self.log_view.value += f"{formatted_msg}\n"
                self.log_view.update()
            elif self.log_view:
                # Store value even if not mounted, so it's there when mounted
                self.log_view.value += f"{formatted_msg}\n"
        except Exception:
            # Fallback for safety
            if self.log_view:
                 self.log_view.value += f"{formatted_msg}\n"

    def _handle_window_event(self, e: ft.ControlEvent) -> None:
        """Unified window event handler (replaces _on_window_event, _on_window_resize)"""
        event_type = e.type
        
        # 1. Handle Close
        if event_type == ft.WindowEventType.CLOSE:
            asyncio.create_task(self._graceful_shutdown())
            return

        # 2. Performance Optimization: Collapse heavy UI on resize/state change
        collapse_events = [
            ft.WindowEventType.MINIMIZE, 
            ft.WindowEventType.MAXIMIZE,
            ft.WindowEventType.UNMAXIMIZE,
            ft.WindowEventType.RESIZE, 
        ]
        
        if event_type in collapse_events and hasattr(self, '_settings_page') and self._settings_page:
             self._settings_page.reset_state()

        # 3. Validation: Maximize State & Borders
        # Update border radius (0 when maximized, 8 otherwise)
        is_maximized = self.page.window.maximized
        if getattr(self, '_last_maximized', None) is not None and is_maximized != self._last_maximized:
            self._update_maximize_border(is_maximized)
        self._last_maximized = is_maximized

        # 4. State Persistence (Debounced)
        if self._save_timer:
            self._save_timer.cancel()
        self._save_timer = threading.Timer(0.5, self._save_window_state)
        self._save_timer.start()

    
    def _restore_window_state(self) -> None:
        """Restore window state from saved settings"""
        # Get saved values with defaults
        width = UserSettings.get("window_width", 960)
        height = UserSettings.get("window_height", 600)
        top = UserSettings.get("window_top")
        left = UserSettings.get("window_left")
        maximized = UserSettings.get("window_maximized", False)
        
        # Set dimensions first (order matters per Flet docs)
        self.page.window.width = width
        self.page.window.height = height
        
        # Set position if saved (None means first run, let OS decide)
        if top is not None:
            self.page.window.top = top
        if left is not None:
            self.page.window.left = left
        
        # Set maximize state LAST - this is critical
        if maximized:
            self.page.window.maximized = True
            self._last_maximized = True
    
    def _save_window_state(self) -> None:
        """Save current window state to settings"""
        # Always save maximized state
        is_maximized = self.page.window.maximized
        UserSettings.set("window_maximized", is_maximized)
        
        # Only save dimensions when NOT maximized
        # This prevents saving fullscreen dimensions as user preference
        if not is_maximized:
            width = self.page.window.width
            height = self.page.window.height
            top = self.page.window.top
            left = self.page.window.left
            
            # Validate position is within reasonable bounds
            # Windows reports -32000 when window is minimized - filter these out
            if (top is not None and top > -1000 and 
                left is not None and left > -1000 and
                width is not None and width > 0 and
                height is not None and height > 0):
                UserSettings.set("window_width", width)
                UserSettings.set("window_height", height)
                UserSettings.set("window_top", top)
                UserSettings.set("window_left", left)

    def _on_win_btn_hover(self, e: ft.ControlEvent, idx: int, is_hover: bool) -> None:
        """Handle window button hover states"""
        try:
            container = e.control.content
            if is_hover:
                # Use red for close button, otherwise use theme-appropriate hover
                if idx == 2:  # Close button
                    container.bgcolor = ThemeManager.current.win_close_hover_bg
                    self.win_btn_icons[idx].color = ThemeManager.current.win_close_hover_icon
                else:
                    # Hover style from ThemeManager (handles light/dark specifics)
                    container.bgcolor = ThemeManager.current.win_btn_hover_bg
            else:
                container.bgcolor = None
                self.win_btn_icons[idx].color = ThemeManager.current.text_primary
            container.update()
            self.win_btn_icons[idx].update()
        except Exception:
            pass
    
    def _on_output_format_changed(self, new_format: str) -> None:
        """Handle output format change (called via EventBus)"""
        # Note: UserSettings is already updated by the sender (OutputSection)
        
        # Update existing tasks' output extensions
        for task in self.tasks:
            current_path = Path(task.output_path)
            # Ensure we are replacing the extension, not appending if one exists (or handle suffix correctly)
            # with_suffix replaces the last extension.
            task.output_path = str(current_path.with_suffix(f".{new_format}"))
        
        # Use TaskPage method instead of undefined _update_table
        if hasattr(self, '_task_page') and self._task_page:
            self._task_page.update_table()
        
        # Log or notify
        logger.info(f"Output format changed to: {new_format}")
        # self._show_snackbar(DesktopLocale.get("output_format") + ": " + new_format, success=True)
    



    
    def _on_vad_changed(self, e: ft.ControlEvent) -> None:
        """Handle VAD switch change"""
        UserSettings.set("vad_enabled", e.control.value)
    
    def _on_vad_max_speech_changed(self, e: ft.ControlEvent) -> None:
        """Handle VAD max speech duration change"""
        try:
            value = float(e.control.value)
            UserSettings.set("vad_max_speech", value)
        except ValueError:
            pass
    
    def _on_vad_min_silence_changed(self, e: ft.ControlEvent) -> None:
        """Handle VAD min silence duration change"""
        try:
            value = int(e.control.value)
            UserSettings.set("vad_min_silence", value)
        except ValueError:
            pass
    
    def _on_beam_size_changed(self, e: ft.ControlEvent) -> None:
        """Handle beam size change"""
        try:
            value = int(e.control.value)
            UserSettings.set("beam_size", value)
        except ValueError:
            pass
    
    def _on_cpu_threads_changed(self, e: ft.ControlEvent) -> None:
        """Handle CPU threads change"""
        try:
            value = int(e.control.value)
            if value > 0:
                UserSettings.set("cpu_threads", value)
        except ValueError:
            pass
    
    def _on_compute_type_changed(self, e: ft.ControlEvent) -> None:
        """Handle compute type change"""
        UserSettings.set("compute_type", e.control.value)
    
    # _browse_model_cache_dir moved to BasicSection/EventBus in Phase B.3


    def _open_task_folder(self, index: int) -> None:
        """Open the output folder for a specific task"""
        if index < 0 or index >= len(self.tasks):
            return
            
        task = self.tasks[index]
        output_dir = task.output_dir
        
        try:
            from core.platform_utils import open_file_or_folder
            
            if not open_file_or_folder(output_dir):
                self._show_dialog(DesktopLocale.get("error"), f"Folder not found or failed to open: {output_dir}")
                return
                
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")
            self._show_snackbar(f"Failed to open folder: {e}", success=False)
    
    # _browse_output_dir moved to OutputSection/EventBus in Phase B.3

    
    def _reset_to_defaults(self, e: ft.ControlEvent) -> None:
        """Show confirmation dialog before resetting settings"""
        from ui.dialogs import show_reset_defaults_dialog
        
        def do_reset():
            UserSettings.reset_to_defaults()
            ThemeManager.notify_listeners()
            self._show_snackbar(DesktopLocale.get("reset_confirm"), success=True)
        
        # Delegate to dialog module (SOLID: SRP compliance)
        show_reset_defaults_dialog(page=self.page, on_confirm_callback=do_reset)


    
    
    # _on_window_resize removed (merged into _handle_window_event)

    
    def _update_maximize_border(self, is_maximized: bool) -> None:
        """Update border radius based on maximize state"""
        if getattr(self, 'main_container', None):
            new_radius = 0 if is_maximized else 8
            # Always update without condition check - ensures radius is correct
            self.main_container.border_radius = new_radius
            self.main_container.update()

    def _on_window_state_change(self, e: ft.WindowEvent) -> None:
        """Handle window state changes (maximize/unmaximize) from double-click"""
        logger.debug(f"Window state event: {e.data} type: {type(e)}")  # Debug
        # Check if e.data is missing, maybe status is elsewhere in Flet 0.80
        # Flet 0.80 workaround: e.data might be None, check window state directly
        is_maximized = self.page.window.maximized
        if e.data == "maximize" or (e.data is None and is_maximized):
            self._update_maximize_border(True)
        elif e.data in ("unmaximize", "restore") or (e.data is None and not is_maximized):
            self._update_maximize_border(False)

    def _pick_files_click(self, e: ft.ControlEvent) -> None:
        """Handle click on Add Files button"""
        self.page.run_task(self._pick_files)
    
    def _pick_folder_click(self, e: ft.ControlEvent) -> None:
        """Handle click on Add Folder button"""
        self.page.run_task(self._pick_folder)
    
    async def _pick_files(self) -> None:
        """Open file picker dialog for individual files"""
        import traceback
        try:
            result = await self.file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=[ext.lstrip('.') for ext in TaskController.SUPPORTED_EXTENSIONS]
            )
            
            if result:
                file_paths = [f.path for f in result]
                # Delegate to TaskController
                self.task_controller.add_files(file_paths)
                
        except Exception:
            self._log(f"Error in _pick_files: {traceback.format_exc()}")
    
    async def _pick_folder(self) -> None:
        """Open folder picker and scan for supported files"""
        import traceback
        try:
            result = await self.file_picker.get_directory_path()
            
            if result:
                # Delegate to TaskController
                self.task_controller.add_folder(result)
                
        except Exception:
            self._log(f"Error in _pick_folder: {traceback.format_exc()}")

    def _clear_tasks(self, e: ft.ControlEvent) -> None:
        """Clear all tasks"""
        self.task_controller.clear_tasks() 
        # UI update happens via event listener (TASKS_CHANGED)


    def _remove_task(self, index: int) -> None:
        """Remove a specific task"""
        self.task_controller.remove_task(index)
        # UI update happens via event listener (TASK_REMOVED/TASKS_CHANGED)

    def _open_task_folder(self, index):
        """Open the configured output folder for transcription results"""
        import os
        import subprocess
        from core.settings import UserSettings
        
        # Get output directory from settings (this is where transcriptions are saved)
        output_dir = UserSettings.get("output_directory", "")
        
        # Fallback: if no output_directory set, use task's output path parent
        if not output_dir and 0 <= index < len(self.tasks):
            task = self.tasks[index]
            output_dir = str(Path(task.output_path).parent)
        
        if output_dir and Path(output_dir).exists():
            # Cross-platform folder opening
            import platform
            if platform.system() == "Windows":
                os.startfile(str(output_dir))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(output_dir)])
            else:  # Linux
                subprocess.run(["xdg-open", str(output_dir)])

    def _retry_llm_correction(self, index: int) -> None:
        """Retry LLM correction for a completed task without re-transcribing"""
        from core.settings import UserSettings
        
        if 0 <= index < len(self.tasks):
            task = self.tasks[index]
            
            # First, try the configured output directory
            output_dir = UserSettings.get("output_directory", "")
            output_filename = Path(task.output_path).name
            
            # Possible locations for the output file
            possible_paths = []
            
            if output_dir:
                # Check in configured output directory
                possible_paths.append(Path(output_dir) / output_filename)
            
            # Also check the task's original output path
            possible_paths.append(Path(task.output_path))
            
            # Find the actual file
            output_path = None
            for path in possible_paths:
                if path.exists():
                    output_path = path
                    break
            
            if not output_path:
                self._log(f"⚠️ {DesktopLocale.get('file_not_found')}: {output_filename}")
                return
            
            # Run LLM correction in background - use inner async to capture variables
            async def do_retry():
                await self._async_retry_llm(task, output_path)
            self.page.run_task(do_retry)
    
    async def _async_retry_llm(self, task: TranscriptionTask, output_path: Path) -> None:
        """Async handler for LLM retry"""
        import asyncio
        
        # Helper for consistent log formatting
        def log_llm(msg_key, *args, is_key=True):
            category = DesktopLocale.get("log_category_llm")
            if is_key:
                msg = DesktopLocale.get(msg_key)
                if args:
                    msg = msg.format(*args)
            else:
                msg = msg_key
            self._log(f"[{category}] {msg}")

        try:
            # Lazy imports to avoid circular dependency
            from core.settings import UserSettings
            from core.events import EventBus, Events
            from core import secure_storage
            from core import device_detection
            from core.constants.defaults import DEFAULT_LLM_MODEL
            from features.llm.factory import create_provider

            # Lock UI
            self.update_ui_state(True)
            
            log_llm("retry_llm_starting")
            
            
            # Update task status to show LLM correction in progress
            task.status = "llm_correcting"
            EventBus.emit(Events.TASK_STATUS_CHANGED, (self.tasks.index(task), task.status))
            
            # Read original file
            with open(output_path, 'r', encoding='utf-8') as f:
                original_content = f.read()


            config = {
                'llm_provider': UserSettings.get("llm_provider", "gemini"),
                'llm_api_key': secure_storage.get_api_key(UserSettings.get("llm_provider", "gemini")),
                'llm_model': UserSettings.get("llm_model", DEFAULT_LLM_MODEL), # Use DEFAULT_LLM_MODEL here
                'llm_base_url': UserSettings.get("llm_base_url", "http://localhost:11434"),
                'llm_system_prompt': UserSettings.get("llm_system_prompt", ""),
                'llm_temperature': float(UserSettings.get("llm_temperature", 0.3)),
                'llm_web_search': UserSettings.get("llm_web_search", False),
            }

            provider = create_provider(config)
            language = UserSettings.get("asr_language", "zh")
            
            # Run LLM call in thread to not block UI
            def do_llm_call():
                return provider.correct_text(
                    original_content,
                    language=language,
                    system_prompt=config.get('llm_system_prompt'),
                    temperature=config.get('llm_temperature', 0.3),
                    enable_web_search=config.get('llm_web_search', False)
                )
            
            corrected_content = await asyncio.to_thread(do_llm_call)
            
            # Save corrected version
            corrected_path = str(output_path).replace('.srt', '_corrected.srt').replace('.txt', '_corrected.txt')
            with open(corrected_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content)
            
            # Restore task status
            task.status = "status_completed"
            EventBus.emit(Events.TASK_STATUS_CHANGED, (self.tasks.index(task), task.status))
            
            filename = Path(corrected_path).name
            log_llm(f"{DesktopLocale.get('retry_llm_success')}: {filename}", is_key=False)
            
        except Exception as e:
            # Restore task status on error
            task.status = "status_completed"
            EventBus.emit(Events.TASK_STATUS_CHANGED, (self.tasks.index(task), task.status))
            
            error_msg = str(e)
            # Provide friendly message for rate limit errors
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                log_llm("api_quota_exceeded")
            else:
                log_llm(f"{DesktopLocale.get('retry_llm_failed')}: {error_msg}", is_key=False)
        
        finally:
            # Unlock UI
            self.update_ui_state(False)

    async def _async_browse_output_dir(self) -> None:
        """Async folder picker for output directory"""

        result = await self.file_picker.get_directory_path()
        if result:
            UserSettings.set("output_directory", result)
            EventBus.emit(Events.OUTPUT_DIR_CHANGED, result)
    
    # === EventBus Handlers for File Picking ===
    
    def _on_browse_model_dir_requested(self, _: dict) -> None:
        """Handle request to browse model directory (from BasicSection)
        
        On Windows, shows admin warning dialog if not running elevated.
        Follows DIP: delegates to platform_utils for admin check and dialog for UI.
        """
        from core.platform_utils import is_windows, is_admin
        
        # Non-Windows or already admin: proceed directly
        if not is_windows() or is_admin():
            self.page.run_task(self._async_browse_model_cache_dir)
            return
        
        # Windows non-admin: show warning dialog
        from ui.dialogs.admin_required_dialog import show_admin_required_dialog
        show_admin_required_dialog(
            self.page,
            on_restart_callback=self._restart_as_admin,
            on_cancel_callback=None  # Just close dialog on cancel
        )
        
    def _on_browse_output_dir_requested(self, _: dict) -> None:
        """Handle request to browse output directory (from OutputSection)"""
        self.page.run_task(self._async_browse_output_dir)

    async def _async_browse_model_cache_dir(self) -> None:
        """Async folder picker for model cache directory"""
        result = await self.file_picker.get_directory_path()
        if result:
            UserSettings.set("model_cache_directory", result)
            EventBus.emit(Events.MODEL_DIR_CHANGED, result)
    
    def _restart_as_admin(self) -> None:
        """Restart the application with administrator privileges (Windows only)"""
        from core.platform_utils import restart_as_admin
        success = restart_as_admin(close_callback=self._close_window)
        if not success:
            self._show_snackbar(DesktopLocale.get("retry_llm_failed"), success=False)




    def _on_llm_test_connection_requested(self, data: dict) -> None:
        """Handle request to test LLM connection"""
        self.page.run_task(self._async_test_llm_connection, data)
        
    async def _async_test_llm_connection(self, data: dict) -> None:
        """Async LLM connection test"""
        from features.llm.factory import create_provider
        
        provider_name = data.get("provider")
        
        # Prepare config for factory
        config = {
            "llm_provider": provider_name,
            "llm_api_key": data.get("api_key"),
            "llm_model": data.get("llm_model"),
            "llm_base_url": data.get("llm_base_url")
        }
        
        success = False
        message = ""
        
        try:
            provider = create_provider(config)
            success, message = provider.verify_connection()
        except Exception as e:
            success = False
            message = str(e)
            
        models = []
        if success:
            try:
                models = provider.get_available_models()
            except Exception:
                pass

        # Emit result back to UI
        EventBus.emit(Events.LLM_CONNECTION_RESULT, {
            "success": success,
            "message": message,
            "models": models
        })
        
        # Show snackbar
        if success:
            self._show_snackbar(DesktopLocale.get("llm_test_success"), success=True)
        else:
            self._show_snackbar(f"{DesktopLocale.get('llm_test_failed')}: {message}", success=False)



    def _clear_log(self) -> None:
        """Clear log view"""
        if getattr(self, 'log_view', None):
            self.log_view.value = ""
            try:
                if self.log_view.page:
                    self.log_view.update()
            except:
                pass

    def _update_output_filename(self, index: int, value: str) -> None:
        """Update task output filename"""
        # Delegate to controller
        self.task_controller.update_output_filename(index, value)


    def _show_media_dialog(self, e: ft.ControlEvent) -> None:
        """Show Media download dialog"""
        from features.media_download.dialog import MediaDownloadDialog
        
        def on_files_downloaded(files):
            if files:
                self.task_controller.add_files(files)
        
        dialog = MediaDownloadDialog(self.page, on_files_downloaded)
        dialog.show()
    
