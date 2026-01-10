"""
LLM Correction Section
Settings for LLM-based transcription correction.
"""

import flet as ft
from typing import Optional

from ui.theme import ThemeManager, TextScale
from ui.components import FluentCard, FluentButton, FluentDropdown, FluentTextField
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from core.events import EventBus, Events
from core.constants.defaults import DEFAULT_LLM_MODEL
from core import secure_storage
from .widgets import SettingsHelper, SETTINGS_ROW_SPACING


class LLMSection:
    """LLM correction settings section"""
    
    def __init__(self, label_area_width: int) -> None:
        self.label_area_width = label_area_width
        
        # Controls
        self.switch_llm_enabled: Optional[ft.Switch] = None
        self.switch_llm_web_search: Optional[ft.Switch] = None
        self.web_search_container: Optional[ft.Container] = None
        self.combo_llm_provider: Optional[FluentDropdown] = None
        self.text_llm_api_key: Optional[FluentTextField] = None
        self.combo_llm_model: Optional[FluentDropdown] = None
        self.text_llm_custom_model: Optional[FluentTextField] = None
        self.text_llm_temperature: Optional[FluentTextField] = None
        self.text_llm_system_prompt: Optional[FluentTextField] = None
        self.text_llm_base_url: Optional[FluentTextField] = None
        self.llm_api_key_container: Optional[ft.Container] = None
        self.llm_base_url_container: Optional[ft.Container] = None
        self.btn_llm_test: Optional[FluentButton] = None
        self.llm_limit_ring: Optional[ft.ProgressRing] = None
        self.llm_success_icon: Optional[ft.Icon] = None
        self.llm_fail_icon: Optional[ft.Icon] = None
        
        # Subscribe to connection results
        EventBus.subscribe(Events.LLM_CONNECTION_RESULT, self._on_connection_result)
        
    def __del__(self) -> None:
        try:
            EventBus.unsubscribe(Events.LLM_CONNECTION_RESULT, self._on_connection_result)
        except (ImportError, Exception):
            pass
    
    def build(self) -> FluentCard:
        """Build the LLM settings card"""
        h = SettingsHelper
        
        # Section header
        header = h.section_header("llm_settings", ft.Icons.SMART_TOY_ROUNDED)
        
        # Enable switch
        saved_llm_enabled = UserSettings.get("llm_enabled", False)
        self.switch_llm_enabled = ft.Switch(
            value=saved_llm_enabled,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("llm_enabled", e.control.value),
        )
        
        # Provider selection
        saved_llm_provider = UserSettings.get("llm_provider", "gemini")
        provider_opts = [
            ft.dropdown.Option("gemini", "Gemini"),
            ft.dropdown.Option("claude", "Claude"),
            ft.dropdown.Option("openai", "OpenAI"),
            ft.dropdown.Option("ollama", "Ollama")
        ]
        self.combo_llm_provider = FluentDropdown(
            options=provider_opts,
            value=saved_llm_provider,
            width=h.get_adaptive_width(provider_opts),
            on_change=self._on_provider_changed,
        )
        
        # API Key (per-provider, stored in OS secure storage)
        saved_llm_api_key = secure_storage.get_api_key(saved_llm_provider)
        self.text_llm_api_key = FluentTextField(
            value=saved_llm_api_key,
            password=True,
            can_reveal_password=True,
            width=350,
            on_blur=self._on_api_key_blur,
        )
        
        # Model selection
        saved_llm_model = UserSettings.get("llm_model", DEFAULT_LLM_MODEL)
        
        # Initialize options based on provider
        model_opts = self._get_model_options(saved_llm_provider)
        # Check if saved model is in options (ignoring custom)
        is_known_model = any(opt.key == saved_llm_model for opt in model_opts if opt.key != "__custom__")
        is_custom_model = not is_known_model and saved_llm_model not in ["", None]
        
        self.combo_llm_model = FluentDropdown(
            options=model_opts,
            value="__custom__" if is_custom_model else saved_llm_model,
            width=h.get_adaptive_width(model_opts),
            on_change=self._on_model_changed,
        )
        
        # Custom model input
        self.text_llm_custom_model = FluentTextField(
            value=saved_llm_model if is_custom_model else "",
            width=250,
            on_blur=lambda e: UserSettings.set("llm_model", e.control.value),
            visible=is_custom_model
        )
        
        # Temperature
        saved_temperature = UserSettings.get("llm_temperature", 0.3)
        self.text_llm_temperature = FluentTextField(
            value=str(saved_temperature),
            width=80,
            text_align=ft.TextAlign.CENTER,
            hint_text="0.0-1.0",
            on_blur=self._on_temperature_changed,
        )
        
        # System Prompt
        saved_system_prompt = UserSettings.get("llm_system_prompt", "")
        # Get default prompt for hint text
        from features.llm.prompts import get_correction_prompt
        default_prompt_hint = get_correction_prompt(DesktopLocale.current_lang)
        
        # Pre-fill with default if empty so it's editable
        if not saved_system_prompt:
            saved_system_prompt = default_prompt_hint
        
        # Text field with fixed height container to trap scroll
        self.text_llm_system_prompt = FluentTextField(
            value=saved_system_prompt,
            hint_text=default_prompt_hint[:100] + "...", 
            multiline=True,
            min_lines=6,
            max_lines=12,
            width=600,
            on_blur=lambda e: UserSettings.set("llm_system_prompt", e.control.value),
        )
        
        # Base URL (Ollama)
        saved_llm_base_url = UserSettings.get("llm_base_url", "http://localhost:11434")
        self.text_llm_base_url = FluentTextField(
            value=saved_llm_base_url,
            width=350,
            on_blur=lambda e: UserSettings.set("llm_base_url", e.control.value),
        )
        
        # Provider-specific containers
        is_ollama = saved_llm_provider == "ollama"
        self.llm_base_url_container = ft.Container(
            content=ft.Column([
                h.setting_row("llm_base_url", self.text_llm_base_url, self.label_area_width),
            ]),
            visible=is_ollama,
        )
        # Test connection button + status icons (placed next to API key)
        self.btn_llm_test = FluentButton(
            DesktopLocale.get("llm_test"),
            ft.Icons.WIFI_TETHERING_ROUNDED,
            on_click=self._on_test_connection,
        )
        self.llm_limit_ring = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
        self.llm_success_icon = ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color="#6ccb5f", size=20, visible=False)
        self.llm_fail_icon = ft.Icon(ft.Icons.CANCEL_ROUNDED, color="#ff6b6b", size=20, visible=False)
        
        api_key_row = ft.Row([
            self.text_llm_api_key,
            self.btn_llm_test,
            self.llm_limit_ring,
            self.llm_success_icon,
            self.llm_fail_icon,
        ], spacing=10)
        
        self.llm_api_key_container = ft.Container(
            content=ft.Column([
                h.setting_row("llm_api_key", api_key_row, self.label_area_width),
            ]),
            visible=not is_ollama,
        )
        
        # Web Search toggle (not available for Ollama/local models)
        saved_llm_web_search = UserSettings.get("llm_web_search", False)
        self.switch_llm_web_search = ft.Switch(
            value=saved_llm_web_search,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("llm_web_search", e.control.value),
        )
        self.web_search_container = ft.Container(
            content=h.setting_row("llm_web_search", self.switch_llm_web_search, self.label_area_width, "llm_web_search_tooltip"),
            visible=not is_ollama,  # Hide for local models
        )
        
        return FluentCard(
            ft.Column([
                header,
                h.setting_row("llm_enabled", self.switch_llm_enabled, self.label_area_width),
                h.setting_row("llm_provider", self.combo_llm_provider, self.label_area_width),
                self.llm_api_key_container,
                self.llm_base_url_container,
                h.setting_row("llm_model", ft.Row([
                    self.combo_llm_model,
                    self.text_llm_custom_model
                ]), self.label_area_width),
                self.web_search_container,
                h.setting_row("llm_temperature", self.text_llm_temperature, self.label_area_width, "llm_temperature_tooltip"),
                h.setting_row("llm_system_prompt", self.text_llm_system_prompt, self.label_area_width, "llm_system_prompt_tooltip"),
            ], spacing=0),
            padding=ft.Padding(20, 20, 20, 10)
        )
    
    # === Logic ===
    
    def _get_model_options(self, provider: str) -> list:
        """
        Get dropdown options for a provider's models.
        
        Uses factory.get_provider_models() to ensure UI stays in sync
        with provider class definitions (SOLID DIP compliance).
        """
        from features.llm.factory import get_provider_models
        
        common_custom = ft.dropdown.Option("__custom__", DesktopLocale.get("custom_model"))
        
        models = get_provider_models(provider)
        if not models:
            return [common_custom]
        
        # Convert model names to dropdown options
        options = [ft.dropdown.Option(m, m) for m in models]
        options.append(common_custom)
        return options

    def _on_provider_changed(self, e: ft.ControlEvent) -> None:
        """Handle provider change: update UI visibility and model options"""
        provider = e.control.value
        UserSettings.set("llm_provider", provider)
        
        is_ollama = provider == "ollama"
        
        # Visibility updates
        if self.llm_base_url_container:
            self.llm_base_url_container.visible = is_ollama
        if self.llm_api_key_container:
            self.llm_api_key_container.visible = not is_ollama
        if self.web_search_container:
            self.web_search_container.visible = not is_ollama
        
        # Load API key for the selected provider from secure storage
        if self.text_llm_api_key:
            stored_key = secure_storage.get_api_key(provider)
            self.text_llm_api_key.value = stored_key
            
        # Update Model Options
        if self.combo_llm_model:
            self.combo_llm_model.options = self._get_model_options(provider)
            
            # Default model from factory (SOLID compliant)
            from features.llm.factory import get_default_model
            new_val = get_default_model(provider)
            self.combo_llm_model.value = new_val
            UserSettings.set("llm_model", new_val)
            
            # Hide custom field
            # Hide custom field
            if self.text_llm_custom_model:
                self.text_llm_custom_model.visible = False
                self.text_llm_custom_model.update()
            
            # CRITICAL: Must use control.update() to trigger FluentDropdown style application
            self.combo_llm_model.update()
                
        # Update visibility of containers
        if self.llm_base_url_container: self.llm_base_url_container.update()
        if self.llm_api_key_container: self.llm_api_key_container.update()
        if self.web_search_container: self.web_search_container.update()
        if self.text_llm_api_key: self.text_llm_api_key.update() # Update value
        
        # Finally update switch (trigger source) just in case
        if self.switch_llm_enabled:
            self.switch_llm_enabled.update()

    def _on_api_key_blur(self, e: ft.ControlEvent) -> None:
        """Save API key to OS secure storage when field loses focus"""
        provider = self.combo_llm_provider.value if self.combo_llm_provider else "gemini"
        secure_storage.set_api_key(provider, e.control.value)

    def _on_model_changed(self, e: ft.ControlEvent) -> None:
        """Handle model change"""
        val = e.control.value
        is_custom = val == "__custom__"
        
        if self.text_llm_custom_model:
            self.text_llm_custom_model.visible = is_custom
            self.text_llm_custom_model.update()
        
        if not is_custom:
            UserSettings.set("llm_model", val)

    def _on_test_connection(self, e: ft.ControlEvent) -> None:
        """Emit event to request connection test"""
        # Emitting event so App or Controller can handle async test logic
        # without coupling this View to network logic.
        # We pass callbacks or refs so the handler can update the UI?
        # Better: The handler emits back a 'LLM_TEST_RESULT' event.
        # But for simplicity in Phase B, let's just log a todo.
        # OR: We can implement a naive test here? No, stick to decoupling.
        # Let's emit an event.
        EventBus.emit(Events.LLM_TEST_CONNECTION_REQUESTED, {
            "provider": self.combo_llm_provider.value,
            "api_key": self.text_llm_api_key.value,
            "llm_model": self.combo_llm_model.value if self.combo_llm_model.value != "__custom__" else self.text_llm_custom_model.value,
            "llm_base_url": self.text_llm_base_url.value
        })
        
        # Show loading state
        if self.llm_limit_ring: self.llm_limit_ring.visible = True
        if self.llm_success_icon: self.llm_success_icon.visible = False
        if self.llm_fail_icon: self.llm_fail_icon.visible = False
        if self.btn_llm_test: self.btn_llm_test.disabled = True
        
        # Update UI
        if self.llm_limit_ring and self.llm_limit_ring.page:
            self.llm_limit_ring.update()
            self.llm_success_icon.update()
            self.llm_fail_icon.update()
            self.btn_llm_test.update()

    def _on_connection_result(self, data: dict) -> None:
        """Handle connection test result"""
        success = data.get("success", False)
        message = data.get("message", "")
        
        # Reset UI state
        if self.llm_limit_ring: self.llm_limit_ring.visible = False
        if self.btn_llm_test: self.btn_llm_test.disabled = False
        
        if success:
            if self.llm_success_icon: self.llm_success_icon.visible = True
            if self.llm_fail_icon: self.llm_fail_icon.visible = False
        else:
            if self.llm_success_icon: self.llm_success_icon.visible = False
            if self.llm_fail_icon: 
                self.llm_fail_icon.visible = True
                self.llm_fail_icon.tooltip = message # Show error on hover
        
        # Update UI
        if self.llm_limit_ring and self.llm_limit_ring.page:
            self.llm_limit_ring.update()
            self.llm_success_icon.update()
            self.llm_fail_icon.update()
            self.btn_llm_test.update()
            
            # Show global snackbar if possible? 
            # Ideally the Event emitter (App) handles the global notification 
            # or we rely on the tooltip for error details.
            
            # Update model list if provided
            models = data.get("models", [])
            if models and self.combo_llm_model:
                # Convert strings to dropdown options logic
                # Need to merge with existing logic or replace?
                # Usually providers return raw strings.
                # Let's rebuild the options.
                
                # Check provider to decide labeling strategy
                # Or just use the string as key and text for consistency
                new_opts = []
                for m in models:
                    new_opts.append(ft.dropdown.Option(m, m))
                
                # Retrieve "Custom" and add it back
                common_custom = ft.dropdown.Option("__custom__", DesktopLocale.get("custom_model"))
                new_opts.append(common_custom)
                
                self.combo_llm_model.options = new_opts
                self.combo_llm_model.update()


    def _on_temperature_changed(self, e: ft.ControlEvent) -> None:
        """Validate and save temperature"""
        try:
            val = float(e.control.value)
            val = max(0.0, min(1.0, val))
            val = round(val, 2)
            UserSettings.set("llm_temperature", val)
            e.control.value = str(val)
            e.control.update()
        except ValueError:
            e.control.value = str(UserSettings.get("llm_temperature", 0.3))
            e.control.update()
    
    def set_disabled(self, disabled: bool) -> None:
        """Enable/disable all controls in this section"""
        controls = [
            self.switch_llm_enabled, self.switch_llm_web_search,
            self.combo_llm_provider, self.text_llm_api_key, 
            self.combo_llm_model, self.text_llm_custom_model, 
            self.text_llm_temperature, self.text_llm_system_prompt, 
            self.text_llm_base_url,
        ]
        for ctrl in controls:
            if ctrl:
                if hasattr(ctrl, 'set_disabled'):
                    ctrl.set_disabled(disabled)
                else:
                    ctrl.disabled = disabled
        
        if self.btn_llm_test:
            self.btn_llm_test.set_disabled(disabled) if hasattr(self.btn_llm_test, 'set_disabled') else setattr(self.btn_llm_test, 'disabled', disabled)
