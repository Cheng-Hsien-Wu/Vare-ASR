"""
Task Page
Page for managing transcription tasks.
"""

import flet as ft
from typing import TYPE_CHECKING
from pathlib import Path

from ui.theme import ThemeManager, WeightScale
from ui.components import FluentButton, FluentTextField
from core.i18n.localization import DesktopLocale
from features.transcription.models import TranscriptionTask
from .base_page import BasePage

if TYPE_CHECKING:
    from app import VareApp


class TaskPage(BasePage):
    """Task management page.
    
    Displays:
    - Add file/folder buttons
    - Task list table with status
    - Start/Stop transcription buttons
    - Web download button
    """
    
    def __init__(self, page: ft.Page, app: "VareApp"):
        """Initialize task page.
        
        Args:
            page: Flet page reference
            app: VareApp reference for shared state and callbacks
        """
        super().__init__(page)
        self.app = app
    
    
    def build(self) -> ft.Container:
        """Build the task page UI."""
        # Title section
        title_section = ft.Column([
            ft.Text(DesktopLocale.get("drag_drop_title"), style=ThemeManager.get_text_style(14, weight=WeightScale.XL)),
            ft.Text(DesktopLocale.get("drag_drop_hint"), style=ThemeManager.get_text_style(-1, color=ThemeManager.current.text_tertiary, weight=WeightScale.LG)),
        ], spacing=8)
        
        # File picker - Flet 0.80 Service Pattern
        # FilePicker must be added to page.services (not overlay)
        self.app.file_picker = ft.FilePicker()
        self.page.services.append(self.app.file_picker)
        self.page.update()  # Ensure service is registered
        
        # Action buttons - separate buttons for files and folders
        # We attach these to self (TaskPage) instead of self.app
        self.btn_add_file = FluentButton(DesktopLocale.get("add_file"), ft.Icons.INSERT_DRIVE_FILE_OUTLINED, on_click=self.app._pick_files_click)
        self.btn_add_folder = FluentButton(DesktopLocale.get("add_folder"), ft.Icons.FOLDER_OPEN_ROUNDED, on_click=self.app._pick_folder_click)
        self.btn_clear_list = FluentButton(DesktopLocale.get("clear_list"), ft.Icons.DELETE_OUTLINE_ROUNDED, on_click=self.app._clear_tasks, disabled=self.app.is_processing)

        # Empty State - shown when no files are added
        self.drop_zone_empty = ft.Container(
            content=ft.Column([
                ft.Icon(ft.Icons.FOLDER_OPEN_OUTLINED, size=72, color=ThemeManager.current.accent),
                ft.Container(height=16),
                ft.Text(DesktopLocale.get("drag_drop_hint"), style=ThemeManager.get_text_style(2, color=ThemeManager.current.text_secondary, weight=WeightScale.LG)),
                ft.Container(height=24),
                ft.Text("MP4, MP3, WAV, M4A, MKV, MOV, FLAC, WEBM, OGG", style=ThemeManager.get_text_style(color=ThemeManager.current.text_tertiary, weight=WeightScale.LG)),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0, alignment=ft.MainAxisAlignment.CENTER),
            border=ft.Border.all(2, ThemeManager.current.border),
            border_radius=12,
            bgcolor=ThemeManager.current.card_bg,
            alignment=ft.Alignment.CENTER,
            expand=True,
            on_click=self.app._pick_files_click,  # Click to add files
            ink=True,  # Visual feedback
        )
        
        # Task table
        self.task_table = ft.DataTable(
            width=float("inf"),
            columns=[
                ft.DataColumn(ft.Text(DesktopLocale.get("col_filename"), size=ThemeManager.get_font_size(), weight=WeightScale.LG, color=ThemeManager.current.text_primary)),
                ft.DataColumn(ft.Text(DesktopLocale.get("col_output"), size=ThemeManager.get_font_size(), weight=WeightScale.LG, color=ThemeManager.current.text_primary)),
                ft.DataColumn(ft.Text(DesktopLocale.get("col_status"), size=ThemeManager.get_font_size(), weight=WeightScale.LG, color=ThemeManager.current.text_primary)),
                ft.DataColumn(ft.Text(DesktopLocale.get("col_action"), size=ThemeManager.get_font_size(), weight=WeightScale.LG, color=ThemeManager.current.text_primary)),
            ],
            rows=self._get_task_rows(),
            border=ft.Border.all(1, ThemeManager.current.border),
            border_radius=8,
            horizontal_lines=ft.BorderSide(1, ThemeManager.current.divider),
            heading_row_color=ThemeManager.current.card_bg_secondary,
            data_row_color={ft.ControlState.HOVERED: ThemeManager.current.hover_bg},
            column_spacing=20,
        )
        
        self.table_container = ft.Container(
            content=ft.Column([self.task_table], scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor=ThemeManager.current.card_bg,
            border_radius=8,
            border=ft.Border.all(1, ThemeManager.current.border),
            padding=ft.Padding.only(left=15, top=15, bottom=15, right=5),
            expand=True,
        )
        
        # Start/Stop buttons
        self.start_btn = FluentButton(DesktopLocale.get("start_transcribe"), ft.Icons.PLAY_ARROW_ROUNDED, on_click=self.app._start_processing, primary=True)
        self.stop_btn = FluentButton(DesktopLocale.get("stop_process"), ft.Icons.STOP_ROUNDED, on_click=self.app._stop_processing)
        self.stop_btn.visible = self.app.is_processing
        self.start_btn.visible = not self.app.is_processing
        
        # Web download button
        self.btn_web_download = FluentButton(DesktopLocale.get("web_download"), ft.Icons.SMART_DISPLAY_ROUNDED, on_click=self.app._show_media_dialog)
        
        action_row = ft.Row([
            ft.Row([
                self.btn_add_file,
                self.btn_add_folder,
                self.btn_web_download,
                self.start_btn, 
                self.stop_btn
            ], spacing=10),
            self.btn_clear_list
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        # Dynamic content container - switches between empty state and task list
        self.task_content_container = ft.Column(expand=True)
        self.update_view()  # Set initial state
        
        # Content column with right padding
        return ft.Container(
            content=ft.Column([
                title_section,
                ft.Container(height=20),
                action_row,
                ft.Container(height=15),
                self.task_content_container,
                ft.Container(height=20),
            ], spacing=0, expand=True),
            padding=ft.Padding.only(right=40),
            expand=True,
        )

    def _get_status_color(self, status: str) -> str:
        """Get color for status string"""
        if status == "status_completed":
            return ThemeManager.current.success
        elif status in ("status_failed", "status_error"):
            return ThemeManager.current.error
        elif status == "status_processing":
            return ThemeManager.current.accent
        elif status == "status_stopped":
            return ThemeManager.current.text_tertiary
        return ThemeManager.current.text_secondary

    def update_view(self) -> None:
        """Update task view based on empty state"""
        if not self.app.tasks:
            self.task_content_container.controls = [self.drop_zone_empty]
        else:
            self.task_content_container.controls = [self.table_container]
        
        try:
            if self.task_content_container.page:
                self.task_content_container.update()
        except Exception:
            pass

    def update_table(self) -> None:
        """Smart update of table rows"""
        if not hasattr(self, 'task_table') or not self.task_table:
            return

        current_count = len(self.task_table.rows)
        target_count = len(self.app.tasks)

        # Helper to force full rebuild (needed for removals/reorders to fix indices)
        def full_rebuild():
            self.task_table.rows = [
                self._create_row(i, task) 
                for i, task in enumerate(self.app.tasks)
            ]

        if target_count == 0:
            self.task_table.rows.clear()
        elif target_count > current_count:
            # Append optimization: Only create new rows
            # Existing rows 0..current_count-1 preserve their indices
            for i in range(current_count, target_count):
                self.task_table.rows.append(self._create_row(i, self.app.tasks[i]))
        else:
            # Removal or reorder: Indices shift, so we must rebuild callbacks
            # (Optimizing this further requires mutable row objects, Phase B consideration)
            full_rebuild()

        try:
            if self.task_table.page:
                self.task_table.update()
        except Exception:
            # Control might not be added to page yet
            pass

    def set_processing_state(self, is_processing: bool) -> None:
        """Update buttons state based on processing status - Optimized"""
        if hasattr(self, 'start_btn'):
            self.start_btn.visible = not is_processing
            self.start_btn.update()
            
        if hasattr(self, 'stop_btn'):
            self.stop_btn.visible = is_processing
            self.stop_btn.update()
        
        # Disable Action Buttons
        for btn in [self.btn_add_file, self.btn_add_folder, self.btn_web_download, self.btn_clear_list]:

            if btn: 
                if hasattr(btn, 'set_disabled'):
                    btn.set_disabled(is_processing)
                else:
                    btn.disabled = is_processing
                if btn.page: btn.update()

        # Optimize: Iterate existing rows to update state instead of full rebuild
        # This prevents UI flicker and massive object recreation
        if self.task_table and self.task_table.rows:
            for row in self.task_table.rows:
                # Row structure:
                # Cell 1: Output Filename (TextField) -> Content of Container
                # Cell 3: Actions (Row of IconButtons)
                
                # Update Output Filename ReadOnly
                try:
                    output_field = row.cells[1].content.content # DataCell -> Container -> TextField
                    output_field.read_only = is_processing
                    output_field.update()
                except:
                    pass

                # Update Delete Button Disabled
                try:
                    action_row = row.cells[3].content # DataCell -> Row
                    for ctrl in action_row.controls:
                        if isinstance(ctrl, ft.IconButton) and ctrl.icon == ft.Icons.DELETE_OUTLINE_ROUNDED:
                            ctrl.disabled = is_processing
                            ctrl.icon_color = ThemeManager.current.text_tertiary if not is_processing else ThemeManager.current.text_disabled
                            ctrl.update()
                except:
                    pass
        
        # We do NOT call update_table() here to avoid rebuild

    def _create_status_cell(self, task) -> ft.Column:
        """Create status cell content for a task (shared helper to avoid duplication)"""
        status_color = self._get_status_color(task.status)
        display_status = DesktopLocale.get(task.status)
        
        # Truncate long status text
        max_status_len = 25
        truncated_status = display_status[:max_status_len] + "..." if len(display_status) > max_status_len else display_status
        
        # Build tooltip (include error message for failed tasks)
        status_tooltip = display_status
        if task.status == "status_failed" and getattr(task, 'error_msg', None):
            status_tooltip = f"{display_status}\n{task.error_msg}"
        
        # Status text
        status_content = [
            ft.Text(truncated_status, size=ThemeManager.get_font_size(-1), color=status_color, weight=WeightScale.MD, tooltip=status_tooltip)
        ]
        
        # Progress bar for processing tasks
        if task.status == "status_processing":
            bar_value = task.progress if task.progress > 0 else None
            percent_text = f"{int(task.progress * 100)}%" if task.progress > 0 else "0%"
            status_content.append(
                ft.Row([
                    ft.ProgressBar(value=bar_value, width=60, color=ThemeManager.current.accent, bgcolor=ThemeManager.current.mica_bg, height=4),
                    ft.Text(percent_text, size=ThemeManager.get_font_size(-2), color=ThemeManager.current.text_secondary),
                ], spacing=6)
            )
        
        return ft.Column(status_content, alignment=ft.MainAxisAlignment.CENTER, spacing=4)

    def update_single_row(self, index: int) -> None:
        """Update only the status cell of a specific row"""
        if not hasattr(self, 'task_table') or not self.task_table or not self.app.tasks:
            return
            
        if index < 0 or index >= len(self.app.tasks):
            return

        task = self.app.tasks[index]
        if index < len(self.task_table.rows):
            row = self.task_table.rows[index]
            
            # Recreate entire row to update Status key and Action buttons (e.g. Open Folder)
            new_row = self._create_row(index, task)
            self.task_table.rows[index] = new_row
            
            if self.task_table.page:
                self.task_table.update()

    def _get_task_rows(self) -> list[ft.DataRow]:
        """Legacy wrapper for compatibility or initial build"""
        return [self._create_row(i, task) for i, task in enumerate(self.app.tasks)]

    def _create_row(self, i: int, task: TranscriptionTask) -> ft.DataRow:
        """Create a single DataRow for the table"""
        # Use shared helper for status cell
        status_cell = self._create_status_cell(task)

        # Editable Output Filename
        # Display only the stem (no extension) because the system outputs multiple formats (SRT + TXT)
        # Showing .srt might mislead users into thinking only SRT is produced.
        output_name = Path(task.output_path).stem
        output_field = FluentTextField(
            text_size_offset=-1,
            value=output_name,
            weight=WeightScale.BASE, # Adjustable: Change to MD for bolder text
            width=300,
            dense=True,
            content_padding=ft.Padding(10, 5, 10, 5),
            border="none", 
            bgcolor="transparent",
            # Use app callback
            on_change=lambda e, idx=i: self.app._update_output_filename(idx, e.control.value),
            read_only=self.app.is_processing, 
        )
        
        # Open Folder Button (only for completed tasks)
        open_folder_btn = None
        retry_llm_btn = None
        if task.status == "status_completed":
            open_folder_btn = ft.IconButton(
                ft.Icons.FOLDER_OPEN_ROUNDED,
                icon_color=ThemeManager.current.text_secondary,
                icon_size=18,
                on_click=lambda _, idx=i: self.app._open_task_folder(idx),
                tooltip=DesktopLocale.get("open_output_folder"),
                style=ft.ButtonStyle(
                    overlay_color={
                        ft.ControlState.HOVERED: ThemeManager.current.hover_bg,
                    },
                ),
            )
            # Retry LLM Correction button
            retry_llm_btn = ft.IconButton(
                ft.Icons.EDIT_NOTE_ROUNDED,
                icon_color=ThemeManager.current.text_secondary,
                icon_size=18,
                on_click=lambda _, idx=i: self.app._retry_llm_correction(idx),
                tooltip=DesktopLocale.get("retry_llm_correction"),
                style=ft.ButtonStyle(
                    overlay_color={
                        ft.ControlState.HOVERED: ThemeManager.current.hover_bg,
                    },
                ),
            )

        del_btn = ft.IconButton(
            ft.Icons.DELETE_OUTLINE_ROUNDED,
            icon_color=ThemeManager.current.text_tertiary if not self.app.is_processing else ThemeManager.current.text_disabled,
            icon_size=18,
            # Use app callback
            on_click=lambda _, idx=i: self.app._remove_task(idx) if not self.app.is_processing else None,
            tooltip=DesktopLocale.get("delete_task_tooltip"),
            disabled=self.app.is_processing,
            style=ft.ButtonStyle(
                overlay_color={
                    ft.ControlState.HOVERED: ThemeManager.current.hover_bg,
                },
            ),
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Container(
                    content=ft.Text(
                        Path(task.input_path).name, 
                        size=ThemeManager.get_font_size(-1), 
                        weight=WeightScale.MD,  # Bolder for readability
                        color=ThemeManager.current.text_primary,
                        overflow=ft.TextOverflow.ELLIPSIS,
                        max_lines=1,
                        tooltip=Path(task.input_path).name,
                    ),
                    width=250,  # Fixed width to prevent squeeze
                )),
                ft.DataCell(ft.Container(content=output_field, alignment=ft.Alignment(-1.0, 0.0))),
                ft.DataCell(status_cell),
                ft.DataCell(ft.Row(
                    [btn for btn in [retry_llm_btn, open_folder_btn, del_btn] if btn], 
                    spacing=2
                )),
            ]
        )
