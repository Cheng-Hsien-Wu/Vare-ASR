"""
Base Page
Abstract base class for all application pages.
"""

import flet as ft
from abc import ABC, abstractmethod
from typing import Optional

from ui.theme import ThemeManager
from core.events import EventBus


class BasePage(ABC):
    """Abstract base class for application pages.
    
    Pages should:
    1. Subscribe to relevant EventBus events
    2. Implement build() to construct UI
    3. Implement on_theme_changed() for theme updates
    """
    
    def __init__(self, page: ft.Page):
        self.page = page
        self._content: Optional[ft.Control] = None
    
    @abstractmethod
    def build(self) -> ft.Control:
        """Build and return the page content."""
        pass
    
    def on_theme_changed(self) -> None:
        """Called when theme changes. Override to handle theme updates."""
        pass
    
    def on_mount(self) -> None:
        """Called when page is displayed. Override for initialization."""
        pass
    
    def on_unmount(self) -> None:
        """Called when page is hidden. Override for cleanup."""
        pass
    
    @property
    def content(self) -> ft.Control:
        """Get the page content, building if necessary."""
        if self._content is None:
            self._content = self.build()
        return self._content
    
    def refresh(self) -> None:
        """Rebuild the page content."""
        self._content = self.build()
