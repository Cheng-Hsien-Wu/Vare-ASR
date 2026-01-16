"""
Media Dialog
UI component for media download dialog (supports YouTube and others).
"""

import flet as ft
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
import threading
import time

from ui.theme import ThemeManager, WeightScale
from ui.components import FluentButton, FluentTextField, FluentDropdown
from core.settings import UserSettings
from .service import MediaDownloader
from core.i18n.localization import DesktopLocale
from .utils import MediaUrlValidator
import sys
import asyncio
import logging

logger = logging.getLogger(__name__)


class MediaDownloadDialog:
    """Media download dialog UI component."""
    
    def __init__(self, page: ft.Page, on_files_added: Callable[[list], None]) -> None:
        self.page = page
        self.on_files_added = on_files_added
        
        # UI controls
        self.dialog_container: Optional[ft.Container] = None
        self.url_field: Optional[FluentTextField] = None
        self.status_text: Optional[ft.Text] = None
        self.download_btn: Optional[FluentButton] = None
        self.parse_btn: Optional[FluentButton] = None
        self.content_column: Optional[ft.Column] = None
        
        # State
        self.current_info: Optional[Dict[str, Any]] = None
        self.is_playlist = False
        self.selected_indices: List[int] = []
        self.selected_audio_track: str = 'default'
        self.audio_track_dropdown: Optional[ft.Dropdown] = None
        self.progress_bar: Optional[ft.ProgressBar] = None
        self.progress_text: Optional[ft.Text] = None  # Progress percentage text
        self.is_cancelled = False
    
    def show(self) -> None:
        """Show the Media download dialog."""
        
        self.url_field = FluentTextField(
            hint_text=DesktopLocale.get("media_url_hint"),
            width=400,
            autofocus=True,
            on_submit=self._on_parse_click
        )
        
        self.parse_btn = FluentButton(
            DesktopLocale.get("media_parse"),
            ft.Icons.SEARCH_OUTLINED,
            on_click=self._on_parse_click
        )
        
        self.paste_btn = FluentButton(
             DesktopLocale.get("media_paste"),
             icon=ft.Icons.CONTENT_PASTE_ROUNDED,
             on_click=self._on_paste_click,
             tooltip=DesktopLocale.get("paste_tooltip")
        )
        self.paste_btn.visible = False # Hidden by default, shown if clipboard matches URL
        
        self.status_text = ft.Text(
            "", 
            style=ThemeManager.get_text_style(-1, color=ThemeManager.current.text_secondary, weight=WeightScale.LG)
        )
        
        self.content_column = ft.Column(
            [], 
            spacing=10, 
            scroll=ft.ScrollMode.AUTO, 
            height=300
        )
        
        self.download_btn = FluentButton(
            DesktopLocale.get("media_download_add"),
            ft.Icons.DOWNLOAD_ROUNDED,
            on_click=self._on_download_click,
            primary=True,
            disabled=True  # Disabled until parsed
        )
        
        # Progress bar (hidden by default)
        self.progress_bar = ft.ProgressBar(
            visible=False,
            color=ThemeManager.current.accent,
            value=0,  # Determinate progress
        )
        
        # Progress text (hidden by default)
        self.progress_text = ft.Text(
            "",
            style=ThemeManager.get_text_style(-1, color=ThemeManager.current.text_secondary, weight=WeightScale.LG),
            visible=False,
        )
        
        cancel_btn = FluentButton(
            DesktopLocale.get("cancel"),
            on_click=lambda _: self.close()
        )
        
        dialog_content = ft.Container(
            content=ft.Column([
                # Title
                ft.Row([
                    ft.Text(
                        DesktopLocale.get("media_download"),
                        size=ThemeManager.get_font_size(4),
                        weight=WeightScale.XL,
                        color=ThemeManager.current.text_primary
                    ),
                    ft.Container(expand=True),
                    ft.IconButton(
                        ft.Icons.CLOSE, 
                        on_click=lambda _: self.close(),
                        icon_color=ThemeManager.current.text_secondary,
                        style=ft.ButtonStyle(
                            overlay_color={
                                ft.ControlState.HOVERED: ThemeManager.current.hover_bg,
                            },
                        ),
                    ),
                ]),
                ft.Divider(height=1),
                ft.Container(height=10),
                
                # Input Row
                ft.Text(
                    DesktopLocale.get("media_url_hint"),
                    style=ThemeManager.get_text_style(color=ThemeManager.current.text_secondary, weight=WeightScale.LG)
                ),
                ft.Container(height=5),
                ft.Row([self.url_field, self.paste_btn, self.parse_btn], spacing=10),
                
                # Status & Content
                ft.Container(height=8),
                self.status_text,
                ft.Container(height=8),
                self.content_column,
                
                # Actions
                ft.Container(height=8),
                self.progress_text,
                ft.Container(height=4),
                self.progress_bar,
                ft.Container(height=8),
                ft.Row([
                    ft.Container(expand=True),
                    cancel_btn,
                    self.download_btn,
                ], spacing=10),
            ], spacing=0),
            width=700,
            height=600,
            padding=25,
            bgcolor=ThemeManager.current.card_bg,
            border_radius=12,
            border=ft.Border.all(1, ThemeManager.current.border),
            shadow=ft.BoxShadow(blur_radius=20, color=ft.Colors.BLACK26),
        )
        
        # Modal overlay
        self.dialog_container = ft.Container(
            content=ft.Stack([
                ft.Container(
                    bgcolor=ft.Colors.with_opacity(0.5, ft.Colors.BLACK),
                    expand=True,
                    on_click=lambda _: self.close(),
                ),
                ft.Container(
                    content=dialog_content,
                    alignment=ft.Alignment(0, 0),
                ),
            ]),
            expand=True,
            
        )
        
        self.page.overlay.append(self.dialog_container)
        self.page.update()
        
        # Smart Paste: Check clipboard for URL during show
        self._check_clipboard_for_url()

    def _check_clipboard_for_url(self) -> None:
        """Continuously check if clipboard contains a URL and show paste button if so."""
        async def monitor_clipboard():
            while not self.is_cancelled:
                try:
                    # Small delay to prevent high CPU usage
                    await asyncio.sleep(1.0)
                    
                    if not self.page:
                        break
                        
                    text = ""
                    # Compatibility check for Flet clipboard API
                    if hasattr(self.page, 'get_clipboard'):
                        text = await self.page.get_clipboard()
                    elif hasattr(self.page, 'clipboard'):
                        text = await self.page.clipboard.get()
                    
                    if MediaUrlValidator.is_valid_url(text):
                        if self.paste_btn and not self.paste_btn.visible:
                            self.paste_btn.visible = True
                            self.page.update()
                            # Optional: Auto-fill if field is empty? 
                            # self.url_field.value = text
                            # self.url_field.update()

                except Exception as e:
                    # Silently fail for clipboard access specific errors
                    logger.debug(f"Clipboard check failed: {e}")
                    pass
        
        self.page.run_task(monitor_clipboard)
    
    def close(self) -> None:
        """Close the dialog."""
        self.is_cancelled = True
        if self.dialog_container and self.dialog_container in self.page.overlay:
            self.page.overlay.remove(self.dialog_container)
            self.page.update()
        self.dialog_container = None
    
    def _on_paste_click(self, e: ft.ControlEvent) -> None:
        """Handle paste button click using async clipboard access."""
        async def paste_async():
            try:
                text = ""
                if hasattr(self.page, 'get_clipboard'):
                    text = await self.page.get_clipboard()
                elif hasattr(self.page, 'clipboard'):
                    text = await self.page.clipboard.get()
                
                if MediaUrlValidator.is_valid_url(text):
                    self.url_field.value = text.strip()
                    self.url_field.update()
            except Exception as ex:
                pass
                
        self.page.run_task(paste_async)
    
    def _on_parse_click(self, e: ft.ControlEvent) -> None:
        """Handle parse button click."""
        url = self.url_field.value.strip()
        if not url:
            self._set_status(DesktopLocale.get("media_url_hint"), error=True)
            return

        self._set_status(DesktopLocale.get("media_parsing") + "...", error=False)
        self.parse_btn.disabled = True
        self.download_btn.disabled = True
        self.page.update()

        def parse_thread():
            try:
                # Use current app language for localized titles
                lang = DesktopLocale.current_lang
                downloader = MediaDownloader(".", lang=lang) 
                self.is_playlist = downloader.is_playlist(url)
                
                if self.is_playlist:
                    info = downloader.get_playlist_info(url)
                    # For playlists, fetch audio tracks from first video if available
                    if info.get('videos') and len(info['videos']) > 0:
                        try:
                            first_video_info = downloader.get_video_info(info['videos'][0]['url'])
                            info['audio_tracks'] = first_video_info.get('audio_tracks', [])
                        except Exception:
                            info['audio_tracks'] = []  # Fallback if can't get tracks
                else:
                    info = downloader.get_video_info(url)
                    
                self._run_on_ui(lambda i=info: self._on_parse_success(i))
            except Exception as ex:
                from core.utils.text_utils import clean_error_message
                error_msg = clean_error_message(str(ex))
                self._run_on_ui(lambda msg=error_msg: self._set_status(f"Error: {msg}", error=True))
                def reset_btn():
                    if self.parse_btn: self.parse_btn.disabled = False
                    self.page.update()
                self._run_on_ui(reset_btn)

        threading.Thread(target=parse_thread, daemon=True).start()

    def _on_parse_success(self, info: Dict) -> None:
        """Handle successful parsing."""
        self.current_info = info
        self.parse_btn.disabled = False
        self._set_status("", error=False)
        self.download_btn.disabled = False
        
        # Build UI
        self.content_column.controls.clear()
        
        if self.is_playlist:
            # Playlist UI
            self.selected_indices = [] # Reset
            
            playlist_label = DesktopLocale.get("media_playlist_info").format(info['title'], info['video_count'])
            self.content_column.controls.append(
                ft.Text(playlist_label, weight=WeightScale.XL, size=16)
            )
            
            def create_video_item(idx, video):
                checkbox = ft.Checkbox(
                    value=True,
                    on_change=lambda e: self._on_video_check(e.control.value, idx)
                )
                text = ft.Text(
                    f"{idx+1}. {video['title']} ({MediaDownloader.format_duration(video['length'])})",
                    size=ThemeManager.get_font_size(1),
                    color=ThemeManager.current.text_primary
                )
                return ft.Row([checkbox, text], alignment=ft.MainAxisAlignment.START, spacing=10)

            for video in info['videos']:
                self.content_column.controls.append(create_video_item(video['index'], video))
                self.selected_indices.append(video['index']) # Select all by default
                
        else:
            # Safe thumbnail handling
            thumbnail_url = info.get('thumbnail_url')
            if thumbnail_url:
                image_control = ft.Image(src=thumbnail_url, width=160, border_radius=8)
            else:
                image_control = ft.Container(
                    content=ft.Icon(ft.Icons.VIDEO_FILE_OUTLINED, size=40, color=ThemeManager.current.text_secondary),
                    width=160, height=90, 
                    bgcolor=ThemeManager.current.card_bg_secondary,
                    border_radius=8,
                    alignment=ft.Alignment(0, 0)
                )

            # Single Video UI
            self.content_column.controls.append(
                ft.Row([
                    image_control,
                    ft.Column([
                        ft.Text(info['title'], weight=WeightScale.XL, size=ThemeManager.get_font_size(3)),
                        ft.Text(
                            spans=[
                                ft.TextSpan(f"{DesktopLocale.get('media_channel')}: ", style=ft.TextStyle(weight=WeightScale.MD)),
                                ft.TextSpan(info['author'], style=ft.TextStyle(weight=WeightScale.MD))
                            ],
                            size=ThemeManager.get_font_size(1),
                            color=ThemeManager.current.text_secondary
                        ),
                        ft.Text(
                            spans=[
                                ft.TextSpan(f"{DesktopLocale.get('media_length')}: ", style=ft.TextStyle(weight=WeightScale.MD)),
                                ft.TextSpan(MediaDownloader.format_duration(info['length']), style=ft.TextStyle(weight=WeightScale.MD))
                            ],
                            size=ThemeManager.get_font_size(1),
                            color=ThemeManager.current.text_secondary
                        ),
                    ], expand=True)
                ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.START)
            )
        
        # Add audio track selector if multiple tracks available
        audio_tracks = info.get('audio_tracks', [])
        if len(audio_tracks) > 1:
            self.selected_audio_track = audio_tracks[0]['id']  # Default to first
            
            track_options = []
            for track in audio_tracks:
                lang_code = track['id']
                lower_code = lang_code.lower()
                base_code = lower_code.split('-')[0] if '-' in lower_code else lower_code
                
                # Use the name provided by service.py (which uses pure yt-dlp data)
                display_text = track.get('name', 'Unknown')
                
                track_options.append(ft.dropdown.Option(key=lang_code, text=display_text))
            
            self.audio_track_dropdown = FluentDropdown(
                label=DesktopLocale.get("media_audio_track") if DesktopLocale.get("media_audio_track") != "media_audio_track" else "Audio Track",
                options=track_options,
                value=self.selected_audio_track,
                width=300,
                on_change=lambda e: setattr(self, 'selected_audio_track', e.control.value),
                label_style=ft.TextStyle(size=ThemeManager.get_font_size(1), weight=WeightScale.XL),
            )
            
            self.content_column.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.AUDIOTRACK_ROUNDED, color=ThemeManager.current.accent),
                        self.audio_track_dropdown,
                    ], spacing=10),
                    margin=ft.margin.only(top=15),
                )
            )
        else:
            self.selected_audio_track = 'default'
            self.audio_track_dropdown = None
            
        self.page.update()

    def _on_video_check(self, checked: bool, index: int) -> None:
        """Handle video checkbox change in playlist."""
        if checked:
            if index not in self.selected_indices:
                self.selected_indices.append(index)
        else:
            if index in self.selected_indices:
                self.selected_indices.remove(index)

    def _on_audio_track_change(self, e: ft.ControlEvent) -> None:
        """Handle audio track dropdown change."""
        self.selected_audio_track = e.control.value

    def _on_download_click(self, e) -> None:
        """Handle download button click."""
        if not self.current_info:
            self._set_status(DesktopLocale.get("media_url_hint"), error=True)
            return
            
        if self.is_playlist and not self.selected_indices:
            self._set_status(DesktopLocale.get("media_select_one"), error=True)
            return

        self.download_btn.disabled = True
        self.parse_btn.disabled = True
        self._set_status(DesktopLocale.get("processing") + "...", error=False)
        # Show progress UI
        if self.progress_bar:
            self.progress_bar.visible = True
            self.progress_bar.value = 0
        if self.progress_text:
            self.progress_text.visible = True
            self.progress_text.value = "0%"
        self.page.update()
        
        def download_thread():
            try:
                # Download to User Settings output directory or System Downloads
                output_dir_setting = UserSettings.get("output_directory")
                if output_dir_setting:
                    dl_path = Path(output_dir_setting)
                else:
                    dl_path = Path.home() / "Downloads"
                
                dl_path.mkdir(parents=True, exist_ok=True)
                
                # Use current app language
                lang = DesktopLocale.current_lang
                downloader = MediaDownloader(str(dl_path), lang=lang)
                
                start_time = time.time()
                
                if self.is_playlist:
                    files = downloader.download_playlist(
                        self.current_info['url'], # Use original info URL or one from parsing
                        selected_indices=self.selected_indices,
                        progress_callback=lambda idx, total, title: self._run_on_ui(
                            lambda: self._set_status(DesktopLocale.get("media_downloading_progress").format(idx, total, title))
                        ),
                        audio_track=self.selected_audio_track,
                        cancel_check=lambda: self.is_cancelled
                    )
                else:
                    self._run_on_ui(lambda: self._set_status(DesktopLocale.get("media_downloading")))
                    files = [downloader.download_audio(
                        self.current_info['url'],
                        progress_callback=self._on_download_progress,
                        audio_track=self.selected_audio_track,
                        cancel_check=lambda: self.is_cancelled
                    )]
                
                # Return absolute paths
                abs_files = [str(Path(f).absolute()) for f in files]
                
                self._run_on_ui(lambda: self.on_files_added(abs_files))
                self._run_on_ui(lambda: self.close())
                
            except Exception as ex:
                from core.utils.text_utils import clean_error_message
                error_msg = f"{DesktopLocale.get('media_download_failed')}: {clean_error_message(str(ex))}"
                self._run_on_ui(lambda msg=error_msg: self._set_status(msg, error=True))
                def reset_btns():
                    if self.download_btn: self.download_btn.disabled = False
                    if self.parse_btn: self.parse_btn.disabled = False
                    if self.progress_bar: self.progress_bar.visible = False
                    if self.progress_text: self.progress_text.visible = False
                    self.page.update()
                self._run_on_ui(reset_btns)

        threading.Thread(target=download_thread, daemon=True).start()

    def _on_download_progress(self, downloaded: int, total: int) -> None:
        """Handle download progress updates from yt-dlp."""
        if total > 0:
            percent = downloaded / total
            percent_int = int(percent * 100)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total / (1024 * 1024)
            progress_str = f"{percent_int}% - {downloaded_mb:.1f} MB / {total_mb:.1f} MB"
            
            def update_ui():
                if self.progress_bar:
                    self.progress_bar.value = percent
                if self.progress_text:
                    self.progress_text.value = progress_str
                self.page.update()
            
            self._run_on_ui(update_ui)

    def _set_status(self, message: str, error: bool = False) -> None:
        if self.status_text:
            self.status_text.value = message
            self.status_text.color = ThemeManager.current.error if error else ThemeManager.current.text_secondary
            self.page.update()

    def _run_on_ui(self, func: Callable) -> None:
        """Run function on UI thread using Flet's built-in mechanism."""
        # Skip if dialog is cancelled or page is gone
        if self.is_cancelled or not self.page:
            return
        
        try:
            self.page.run_task(self._async_run, func)
        except Exception as e:
            # Silently ignore errors during shutdown
            pass
    
    async def _async_run(self, func: Callable) -> None:
        """Async wrapper that safely runs the function."""
        # Skip if cancelled
        if self.is_cancelled:
            return
            
        try:
            result = func()
            # If func returns a coroutine, await it
            import inspect
            if inspect.iscoroutine(result):
                await result
        except Exception as e:
            # Only log if not during shutdown
            if not self.is_cancelled:
                logger.warning(f"UI callback error: {e}")
