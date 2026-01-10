"""
Settings Package
Modular settings page with separate sections for maintainability.
"""

from .widgets import ScrollablePathText, SettingsHelper, STANDARD_LABEL_KEYS
from .appearance_section import AppearanceSection
from .basic_section import BasicSection
from .output_section import OutputSection
from .llm_section import LLMSection
from .advanced_section import AdvancedSection
