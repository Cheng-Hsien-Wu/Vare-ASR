"""
Notifications - Centralized notification system.
Handles snackbars, logs, and dialogs.
"""

import flet as ft
from typing import Optional, Callable
from datetime import datetime


class NotificationManager:
    """Centralized notification management"""
    
    _page: Optional[ft.Page] = None
    _log_callback: Optional[Callable[[str], None]] = None
    _snackbar: Optional[ft.SnackBar] = None
    
    @classmethod
    def set_page(cls, page: ft.Page) -> None:
        """Set the page reference for UI notifications"""
        cls._page = page
    
    @classmethod
    def set_log_callback(cls, callback: Callable[[str], None]) -> None:
        """Set callback for log messages"""
        cls._log_callback = callback
    
    @classmethod
    def log(cls, message: str, timestamp: bool = True) -> None:
        """Add a log message.
        
        Args:
            message: Log message
            timestamp: Whether to prepend timestamp
        """
        if timestamp:
            ts = datetime.now().strftime("%H:%M:%S")
            full_msg = f"[{ts}] {message}"
        else:
            full_msg = message
        
        if cls._log_callback:
            cls._log_callback(full_msg)
        else:
            print(full_msg)
    
    @classmethod
    def show_snackbar(cls, message: str, success: bool = True, duration_ms: int = 3000) -> None:
        """Show a snackbar notification.
        
        Args:
            message: Message to display
            success: True for success style, False for error style
            duration_ms: Duration in milliseconds
        """
        if not cls._page:
            print(f"Snackbar (no page): {message}")
            return
        
        from ui.theme import ThemeManager
        
        bgcolor = ThemeManager.current.success if success else ThemeManager.current.error
        
        # Remove old snackbar from overlay to prevent memory leak
        if cls._snackbar and cls._snackbar in cls._page.overlay:
            cls._page.overlay.remove(cls._snackbar)
        
        cls._snackbar = ft.SnackBar(
            content=ft.Text(message, color=ft.Colors.WHITE),  # Always white on colored bg
            bgcolor=bgcolor,
            duration=duration_ms,
        )
        
        cls._page.overlay.append(cls._snackbar)
        cls._snackbar.open = True
        cls._page.update()
    
    @classmethod
    def show_error(cls, message: str) -> None:
        """Show an error snackbar"""
        cls.show_snackbar(message, success=False, duration_ms=5000)
    
    @classmethod
    def show_success(cls, message: str) -> None:
        """Show a success snackbar"""
        cls.show_snackbar(message, success=True, duration_ms=3000)
