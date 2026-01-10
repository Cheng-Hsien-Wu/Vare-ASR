"""
Advanced Settings Section
Settings for beam search, hallucination control, VAD, and system settings.
Built lazily on first expand.
"""

import flet as ft
from typing import Optional

from ui.theme import ThemeManager, WeightScale
from ui.components import FluentCard, FluentDropdown, FluentTextField
from core.i18n.localization import DesktopLocale
from core.settings import UserSettings
from .widgets import SettingsHelper, SETTINGS_SECTION_SPACING


class AdvancedSection:
    """Advanced transcription settings section (lazy loaded)"""
    
    def __init__(self, label_area_width: int) -> None:
        self.label_area_width = label_area_width
        
        # State
        self._content_built = False
        self._expanded = False
        self._pending_disabled = None  # Track disabled state before content is built
        
        # UI containers
        self.content_container: Optional[ft.Column] = None
        self.card: Optional[FluentCard] = None
        self.toggle_icon: Optional[ft.Icon] = None
        self.toggle_text: Optional[ft.Text] = None
        
        # Controls (created lazily)
        self.switch_vad: Optional[ft.Switch] = None
        self.text_vad_threshold: Optional[FluentTextField] = None
        self.text_vad_min_speech: Optional[FluentTextField] = None
        self.text_max_speech: Optional[FluentTextField] = None
        self.text_min_silence: Optional[FluentTextField] = None
        self.text_vad_pad: Optional[FluentTextField] = None
        self.text_beam: Optional[FluentTextField] = None
        self.text_best_of: Optional[FluentTextField] = None
        self.text_patience: Optional[FluentTextField] = None
        self.text_length_penalty: Optional[FluentTextField] = None
        self.text_temperature: Optional[FluentTextField] = None
        self.text_rep_penalty: Optional[FluentTextField] = None
        self.text_no_repeat: Optional[FluentTextField] = None
        self.switch_condition: Optional[ft.Switch] = None
        self.switch_suppress_blank: Optional[ft.Switch] = None
        self.text_log_prob: Optional[FluentTextField] = None
        self.text_no_speech: Optional[FluentTextField] = None
        self.text_compress: Optional[FluentTextField] = None
        self.text_halluc_silence: Optional[FluentTextField] = None
        self.combo_dtype: Optional[FluentDropdown] = None
        self.text_cpu_threads: Optional[FluentTextField] = None
        self.cpu_threads_container: Optional[ft.Container] = None
        self.text_num_workers: Optional[FluentTextField] = None
        self.switch_local_only: Optional[ft.Switch] = None
    
    def build(self) -> ft.Column:
        """Build the advanced settings collapsible section"""
        h = SettingsHelper
        
        # Content container (empty until expanded, with spacing between sections)
        self.content_container = ft.Column([], spacing=SETTINGS_SECTION_SPACING)
        
        # Card (hidden until expanded)
        self.card = FluentCard(self.content_container, padding=ft.Padding(20, 20, 20, 10), visible=False)
        
        # Toggle elements
        self.toggle_icon = ft.Icon(
            ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED,
            size=24,
            color=ThemeManager.current.text_primary
        )
        self.toggle_text = ft.Text(
            DesktopLocale.get("advanced_settings"),
            size=ThemeManager.get_font_size(4),
            weight=WeightScale.XL,
            color=ThemeManager.current.text_primary
        )
        
        toggle = ft.Container(
            content=ft.Row(
                [self.toggle_text, self.toggle_icon],
                spacing=8,
                alignment=ft.MainAxisAlignment.START,
                tight=True
            ),
            on_click=self._toggle_advanced,
            padding=ft.Padding.symmetric(vertical=10, horizontal=12),
            border_radius=4,
            ink=True,
            ink_color=ft.Colors.with_opacity(0.1, ThemeManager.current.text_primary),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        
        return ft.Column([toggle, self.card])
    
    def _toggle_advanced(self, e: ft.ControlEvent | None) -> None:
        """Toggle advanced settings visibility"""
        self._expanded = not self._expanded
        
        if self._expanded:
            # Expanding: build content if needed
            if not self._content_built:
                self._build_content()
            # Apply pending disabled state if set before build
            if self._pending_disabled is not None:
                self.set_disabled(self._pending_disabled)
        else:
            # Collapsing: release controls for performance (reduces resize overhead)
            self.content_container.controls = []
            self._content_built = False
        
        self.card.visible = self._expanded
        self.toggle_icon.icon = (
            ft.Icons.KEYBOARD_ARROW_UP_ROUNDED if self._expanded 
            else ft.Icons.KEYBOARD_ARROW_DOWN_ROUNDED
        )
        self.toggle_icon.update()
        self.card.update()
    
    def collapse(self) -> None:
        """Force collapse the section"""
        if self._expanded:
            self._toggle_advanced(None)
    
    def _build_content(self) -> None:
        """Build advanced settings content (called once on first expand)"""
        h = SettingsHelper
        
        # === VAD Settings ===
        saved_vad = UserSettings.get("vad_enabled", True)
        self.switch_vad = ft.Switch(
            value=saved_vad,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("vad_enabled", e.control.value)
        )
        
        saved_vad_threshold = UserSettings.get("vad_threshold", 0.5)
        self.text_vad_threshold = FluentTextField(
            value=str(saved_vad_threshold),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("vad_threshold", float(e.control.value or 0.5)),
        )
        
        saved_vad_min_speech = UserSettings.get("vad_min_speech_duration_ms", 250)
        self.text_vad_min_speech = FluentTextField(
            value=str(saved_vad_min_speech),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix=ft.Text("ms", size=ThemeManager.get_font_size(), color=ThemeManager.current.text_secondary),
            on_blur=lambda e: UserSettings.set("vad_min_speech_duration_ms", int(e.control.value or 250)),
        )
        
        saved_max_speech = UserSettings.get("vad_max_speech_duration_s", 15.0)
        self.text_max_speech = FluentTextField(
            value=str(saved_max_speech),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix=ft.Text("s", size=ThemeManager.get_font_size(), color=ThemeManager.current.text_secondary),
            on_blur=lambda e: UserSettings.set("vad_max_speech_duration_s", float(e.control.value or 15.0)),
        )
        
        saved_min_silence = UserSettings.get("vad_min_silence_duration_ms", 300)
        self.text_min_silence = FluentTextField(
            value=str(saved_min_silence),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix=ft.Text("ms", size=ThemeManager.get_font_size(), color=ThemeManager.current.text_secondary),
            on_blur=lambda e: UserSettings.set("vad_min_silence_duration_ms", int(e.control.value or 300)),
        )
        
        saved_vad_pad = UserSettings.get("vad_speech_pad_ms", 400)
        self.text_vad_pad = FluentTextField(
            value=str(saved_vad_pad),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix=ft.Text("ms", size=ThemeManager.get_font_size(), color=ThemeManager.current.text_secondary),
            on_blur=lambda e: UserSettings.set("vad_speech_pad_ms", int(e.control.value or 400)),
        )
        
        # === Beam Search Settings ===
        saved_beam = UserSettings.get("beam_size", 5)
        self.text_beam = FluentTextField(
            value=str(saved_beam),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("beam_size", int(e.control.value or 5))
        )
        
        saved_best_of = UserSettings.get("best_of", 5)
        self.text_best_of = FluentTextField(
            value=str(saved_best_of),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("best_of", int(e.control.value or 5)),
        )
        
        saved_patience = UserSettings.get("patience", 1.0)
        self.text_patience = FluentTextField(
            value=str(saved_patience),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("patience", float(e.control.value or 1.0)),
        )
        
        saved_length_penalty = UserSettings.get("length_penalty", 1.0)
        self.text_length_penalty = FluentTextField(
            value=str(saved_length_penalty),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("length_penalty", float(e.control.value or 1.0)),
        )
        
        saved_temperature = UserSettings.get("temperature", "0")
        self.text_temperature = FluentTextField(
            value=str(saved_temperature),
            width=150,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("temperature", e.control.value or "0"),
        )
        
        # === Hallucination Control ===
        saved_rep_penalty = UserSettings.get("repetition_penalty", 1.0)
        self.text_rep_penalty = FluentTextField(
            value=str(saved_rep_penalty),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("repetition_penalty", float(e.control.value or 1.0)),
        )
        
        saved_no_repeat = UserSettings.get("no_repeat_ngram_size", 0)
        self.text_no_repeat = FluentTextField(
            value=str(saved_no_repeat),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("no_repeat_ngram_size", int(e.control.value or 0)),
        )
        
        saved_condition = UserSettings.get("condition_on_previous_text", True)
        self.switch_condition = ft.Switch(
            value=saved_condition,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("condition_on_previous_text", e.control.value),
        )
        
        saved_suppress_blank = UserSettings.get("suppress_blank", True)
        self.switch_suppress_blank = ft.Switch(
            value=saved_suppress_blank,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("suppress_blank", e.control.value),
        )
        
        saved_log_prob = UserSettings.get("log_prob_threshold", -1.0)
        self.text_log_prob = FluentTextField(
            value=str(saved_log_prob),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("log_prob_threshold", float(e.control.value or -1.0)),
        )
        
        saved_no_speech = UserSettings.get("no_speech_threshold", 0.6)
        self.text_no_speech = FluentTextField(
            value=str(saved_no_speech),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("no_speech_threshold", float(e.control.value or 0.6)),
        )
        
        saved_compress = UserSettings.get("compression_ratio_threshold", 2.4)
        self.text_compress = FluentTextField(
            value=str(saved_compress),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("compression_ratio_threshold", float(e.control.value or 2.4)),
        )
        
        saved_halluc_silence = UserSettings.get("hallucination_silence_threshold", 0.0)
        self.text_halluc_silence = FluentTextField(
            value=str(saved_halluc_silence),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            suffix=ft.Text("s", size=ThemeManager.get_font_size(), color=ThemeManager.current.text_secondary),
            on_blur=lambda e: UserSettings.set("hallucination_silence_threshold", float(e.control.value or 0.0)),
        )
        
        # === System Settings ===
        saved_cpu_threads = UserSettings.get("cpu_threads", 4)
        self.text_cpu_threads = FluentTextField(
            value=str(saved_cpu_threads),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("cpu_threads", int(e.control.value or 4))
        )
        is_cpu = UserSettings.get("asr_device", "cuda") == "cpu"
        self.cpu_threads_container = ft.Container(
            content=h.setting_row("cpu_threads", self.text_cpu_threads, self.label_area_width, "cpu_threads_tooltip"),
            visible=is_cpu,
            padding=ft.Padding.only(top=8),
        )
        
        saved_num_workers = UserSettings.get("num_workers", 1)
        self.text_num_workers = FluentTextField(
            value=str(saved_num_workers),
            width=100,
            text_align=ft.TextAlign.RIGHT,
            on_blur=lambda e: UserSettings.set("num_workers", int(e.control.value or 1)),
        )
        
        saved_local_only = UserSettings.get("local_files_only", False)
        self.switch_local_only = ft.Switch(
            value=saved_local_only,
            active_color=ThemeManager.current.accent,
            on_change=lambda e: UserSettings.set("local_files_only", e.control.value),
        )
        
        saved_dtype = UserSettings.get("compute_type", "float16")
        
        # Get compute types from cache (or use fallback if not ready yet)
        from core.device_detection import ComputeTypeCache
        current_device = UserSettings.get("asr_device", "cuda")
        cached_types = ComputeTypeCache.get_cached_types(current_device)
        dtype_opts = [ft.dropdown.Option(t) for t in cached_types]
        
        self.combo_dtype = FluentDropdown(
            options=dtype_opts,
            value=saved_dtype if saved_dtype in cached_types else (cached_types[0] if cached_types else "float16"),
            width=h.get_adaptive_width(dtype_opts),
            on_change=lambda e: UserSettings.set("compute_type", e.control.value),
        )

        # Method to refresh options when device changes (called from external callback)
        def refresh_compute_type_options(device: str):
            """Update dropdown options based on the selected device."""
            # Safety check: Only update if control is created AND attached to page
            if not self.combo_dtype or not self.combo_dtype.page:
                return  # Control not mounted yet, skip update
            
            types = ComputeTypeCache.get_cached_types(device)
            self.combo_dtype.options = [ft.dropdown.Option(t) for t in types]
            
            # Auto-select best available if current value is invalid
            current_val = self.combo_dtype.value
            if current_val not in types and types:
                self.combo_dtype.value = types[0]
                UserSettings.set("compute_type", types[0])
            
            self.combo_dtype.update()
        
        # Store refresh method for external access (e.g., from BasicSection device dropdown)
        self._refresh_compute_type_options = refresh_compute_type_options
        
        # Subscribe to device changes from BasicSection
        from core.events import EventBus, Events
        
        def on_device_changed(device):
            """Handle device change event from BasicSection - refresh compute options"""
            refresh_compute_type_options(device)
        
        EventBus.subscribe(Events.DEVICE_CHANGED, on_device_changed)

        # If cache isn't ready yet, add a listener to update when it's done
        def on_cache_ready():
            async def do_refresh():
                refresh_compute_type_options(UserSettings.get("asr_device", "cuda"))
            if self.combo_dtype.page:
                self.combo_dtype.page.run_task(do_refresh)
        
        if not ComputeTypeCache.is_ready():
            ComputeTypeCache.add_listener(on_cache_ready)


        
        # Build sections - Header is outside rows Column to prevent spacing interference
        beam_header = h.section_header("beam_search_settings", ft.Icons.SEARCH_ROUNDED)
        beam_rows = ft.Column([
            h.setting_row("beam_size", self.text_beam, self.label_area_width, "beam_tooltip"),
            h.setting_row("best_of", self.text_best_of, self.label_area_width, "best_of_tooltip"),
            h.setting_row("patience", self.text_patience, self.label_area_width, "patience_tooltip"),
            h.setting_row("length_penalty", self.text_length_penalty, self.label_area_width, "length_penalty_tooltip"),
            h.setting_row("temperature", self.text_temperature, self.label_area_width, "temperature_tooltip"),
        ], spacing=0)
        beam_section = ft.Column([beam_header, beam_rows], spacing=0)
        
        halluc_header = h.section_header("hallucination_control", ft.Icons.DO_NOT_DISTURB_ON_ROUNDED)
        halluc_rows = ft.Column([
            h.setting_row("repetition_penalty", self.text_rep_penalty, self.label_area_width, "repetition_penalty_tooltip"),
            h.setting_row("no_repeat_ngram_size", self.text_no_repeat, self.label_area_width, "no_repeat_ngram_size_tooltip"),
            h.setting_row("condition_on_previous_text", self.switch_condition, self.label_area_width, "condition_on_previous_text_tooltip"),
            h.setting_row("suppress_blank", self.switch_suppress_blank, self.label_area_width, "suppress_blank_tooltip"),
            h.setting_row("log_prob_threshold", self.text_log_prob, self.label_area_width, "log_prob_threshold_tooltip"),
            h.setting_row("no_speech_threshold", self.text_no_speech, self.label_area_width, "no_speech_threshold_tooltip"),
            h.setting_row("compression_ratio_threshold", self.text_compress, self.label_area_width, "compression_ratio_threshold_tooltip"),
            h.setting_row("hallucination_silence_threshold", self.text_halluc_silence, self.label_area_width, "hallucination_silence_threshold_tooltip"),
        ], spacing=0)
        halluc_section = ft.Column([halluc_header, halluc_rows], spacing=0)
        
        vad_header = h.section_header("vad_settings", ft.Icons.GRAPHIC_EQ_ROUNDED)
        vad_rows = ft.Column([
            h.setting_row("vad_enable", self.switch_vad, self.label_area_width, "vad_tooltip"),
            h.setting_row("vad_threshold", self.text_vad_threshold, self.label_area_width, "vad_threshold_tooltip"),
            h.setting_row("vad_min_speech_duration", self.text_vad_min_speech, self.label_area_width, "vad_min_speech_duration_tooltip"),
            h.setting_row("vad_max_speech_duration", self.text_max_speech, self.label_area_width, "vad_max_speech_duration_tooltip"),
            h.setting_row("vad_min_silence_duration", self.text_min_silence, self.label_area_width, "vad_min_silence_duration_tooltip"),
            h.setting_row("vad_speech_pad", self.text_vad_pad, self.label_area_width, "vad_speech_pad_tooltip"),
        ], spacing=0)
        vad_section = ft.Column([vad_header, vad_rows], spacing=0)
        
        system_header = h.section_header("system_settings", ft.Icons.MEMORY_ROUNDED)
        system_rows = ft.Column([
            h.setting_row("precision", self.combo_dtype, self.label_area_width, "precision_tooltip"),
            self.cpu_threads_container,
            h.setting_row("num_workers", self.text_num_workers, self.label_area_width, "num_workers_tooltip"),
            h.setting_row("local_files_only", self.switch_local_only, self.label_area_width, "local_files_only_tooltip"),
        ], spacing=0)
        system_section = ft.Column([system_header, system_rows], spacing=0)
        
        # Populate content container
        self.content_container.controls = [
            beam_section,
            halluc_section,
            vad_section,
            system_section,
        ]
        self.content_container.update()
        self._content_built = True
    
    def set_disabled(self, disabled: bool) -> None:
        """Enable/disable all controls in this section"""
        # Always update pending state
        self._pending_disabled = disabled
        
        if not self._content_built:
            return  # Nothing to disable if not built yet, will apply on expand
        
        controls = [
            self.switch_vad, self.text_vad_threshold, self.text_vad_min_speech,
            self.text_max_speech, self.text_min_silence, self.text_vad_pad,
            self.text_beam, self.text_best_of, self.text_patience, self.text_length_penalty,
            self.text_temperature, self.text_rep_penalty, self.text_no_repeat,
            self.switch_condition, self.switch_suppress_blank, self.text_log_prob,
            self.text_no_speech, self.text_compress, self.text_halluc_silence,
            self.combo_dtype, self.text_cpu_threads, self.text_num_workers, self.switch_local_only,
        ]
        for ctrl in controls:
            if ctrl:
                 if hasattr(ctrl, 'set_disabled'):
                     ctrl.set_disabled(disabled)
                 else:
                     ctrl.disabled = disabled
                
        # Also update card look if needed? No, separate controls handle it.
    
    def get_controls(self) -> dict:
        """Deprecated: Return empty dict"""
        return {}
