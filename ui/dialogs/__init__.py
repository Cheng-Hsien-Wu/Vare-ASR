"""
UI Dialogs Package
Centralized dialog components following SOLID principles.

All dialogs are contained in this package:
- AboutDialog: Application about dialog
- show_reset_defaults_dialog: Reset to defaults confirmation dialog
"""

from .about_dialog import AboutDialog
from .reset_defaults_dialog import show_reset_defaults_dialog

__all__ = ["AboutDialog", "show_reset_defaults_dialog"]
