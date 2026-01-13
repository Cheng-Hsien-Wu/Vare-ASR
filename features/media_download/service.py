"""
Media Downloader Module
Downloads audio/video from supported sites using yt-dlp.
"""

import yt_dlp
import os
import re
import logging
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
from core.i18n.localization import DesktopLocale

logger = logging.getLogger(__name__)

class YtDlpLogger:
    """Custom logger to redirect yt-dlp output to standard logging and avoid stdout/stderr access in frozen apps."""
    def debug(self, msg):
        # Filter out verbose debug logs if needed, or log as debug
        if not msg.startswith('[debug] '):
            logger.debug(msg)

    def info(self, msg):
        pass # Ignore info messages to keep logs clean, or log as info if needed

    def warning(self, msg):
        logger.warning(msg)

    def error(self, msg):
        logger.error(msg)

class MediaDownloader:
    """Downloads audio/video from supported sites using yt-dlp."""
    
    def __init__(self, output_dir: str, lang: str = "zh-TW") -> None:
        """
        Initialize the downloader.
        
        Args:
            output_dir: Directory to save downloaded audio files.
            lang: Language code for localized titles (e.g., 'zh-TW', 'en').
        """
        self.output_dir = output_dir
        self.lang = lang
        os.makedirs(output_dir, exist_ok=True)

    def _get_ydl_opts(self, base_opts: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get base yt-dlp options with localization and ffmpeg path."""
        opts = base_opts or {}
        
        # IMPORTANT: Use a custom logger to prevent yt-dlp from writing to sys.stdout/sys.stderr
        # In frozen noconsole apps, sys.stdout is None, causing "AttributeError: 'NoneType' object has no attribute 'flush'"
        opts['logger'] = YtDlpLogger()
        
        # Set ffmpeg location for format conversion (important for frozen apps)
        try:
            from core.utils.audio_utils import get_ffmpeg_cmd
            ffmpeg_path = get_ffmpeg_cmd()
            if ffmpeg_path and Path(ffmpeg_path).is_absolute():
                # yt-dlp expects the directory containing ffmpeg, not the binary itself
                opts['ffmpeg_location'] = str(Path(ffmpeg_path).parent)
                logger.info(f"Set ffmpeg_location: {opts['ffmpeg_location']}")
        except Exception as e:
            logger.warning(f"Could not set ffmpeg_location: {e}")
        
        if self.lang:
            # Normalize language code for yt-dlp (case-sensitive)
            lang_map = {
                'zh-tw': 'zh-TW',
                'zh-cn': 'zh-CN',
                'zh-hk': 'zh-HK',
                'en-us': 'en-US',
                'en-gb': 'en-GB',
            }
            # Use mapped code or fallback to original (pass-through)
            target_lang = lang_map.get(self.lang.lower(), self.lang)
            opts['extractor_args'] = {'youtube': {'lang': [target_lang]}}
        return opts
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if URL looks like a valid URL (yt-dlp supports many sites)."""
        # yt-dlp supports thousands of sites, so we just check if it's a URL
        return url.startswith('http://') or url.startswith('https://')
    
    @staticmethod
    def is_playlist(url: str) -> bool:
        """Check if URL is a playlist."""
        return 'playlist?list=' in url or '&list=' in url
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Get video information including available audio tracks.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with video info: {title, length, author, thumbnail_url, audio_tracks}
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        ydl_opts = self._get_ydl_opts(ydl_opts)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                # Extract audio tracks (different languages)
                audio_tracks = self._extract_audio_tracks(info.get('formats', []))
                
                return {
                    'title': info.get('title', DesktopLocale.get('unknown')),
                    'length': info.get('duration', 0),
                    'author': info.get('uploader', DesktopLocale.get('unknown')),
                    'thumbnail_url': info.get('thumbnail', ''),
                    'url': url,
                    'audio_tracks': audio_tracks,
                }
        except Exception as e:
            raise ValueError(f"{DesktopLocale.get('media_video_info_error')}: {str(e)}")
    
    def _extract_audio_tracks(self, formats: List[Dict]) -> List[Dict[str, str]]:
        """
        Extract unique audio tracks (languages) from format list.
        Uses Babel for proper BCP-47 language name localization.
        
        Returns:
            List of {id, language, name} dicts - one per unique language
        """
        # Get app locale for display names
        app_locale = self.lang.replace('-', '_') if self.lang else 'en'
        
        # Group formats by language, keep the best quality for each
        lang_formats = {}
        
        for fmt in formats:
            # Only consider audio-only formats
            if fmt.get('vcodec') == 'none' and fmt.get('acodec') != 'none':
                lang = fmt.get('language') or 'default'
                abr = fmt.get('abr') or 0  # audio bitrate
                
                # Keep the highest bitrate for each language
                if lang not in lang_formats or abr > lang_formats[lang].get('abr', 0):
                    lang_formats[lang] = fmt
        
        # Build clean display names (using pure yt-dlp data)
        audio_tracks = []
        for lang, fmt in lang_formats.items():
            lang_display = fmt.get('language') or 'default'
            
            # 1. Try to use format_note directly (primary source, matches YouTube UI)
            name = ""
            format_note = fmt.get('format_note', '') or ''
            if format_note:
                name = format_note.split(',')[0]
                name = name.replace('(default)', '').strip()
            
            # 2. Fallback to language code
            if not name:
                if lang == 'default' or not lang:
                    name = DesktopLocale.get('media_default_track')
                elif lang in ('und', 'undetermined', 'zxx'):
                    name = DesktopLocale.get('media_undetermined')
                else:
                    name = lang

            audio_tracks.append({
                'id': lang,
                'language': lang_display,
                'name': name,
            })
        
        if not audio_tracks:
            audio_tracks.append({
                'id': 'default',
                'language': 'default',
                'name': DesktopLocale.get('media_default_track'),
            })
        
        return audio_tracks
    
    def get_playlist_info(self, url: str) -> Dict[str, Any]:
        """
        Get playlist information.
        
        Args:
            url: YouTube playlist URL
            
        Returns:
            Dictionary with playlist info and video list
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,  # Don't download, just get info
            'ignoreerrors': True,
        }
        ydl_opts = self._get_ydl_opts(ydl_opts)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                videos = []
                entries = info.get('entries', [])
                for i, entry in enumerate(entries):
                    if entry:  # Skip None entries (unavailable videos)
                        # Always construct URL from video ID for reliability
                        video_id = entry.get('id', '')
                        if video_id:
                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                        else:
                            # Fallback: try to use url field or webpage_url
                            video_url = entry.get('webpage_url') or entry.get('url') or ''
                        
                        if video_url:  # Only add if we have a valid URL
                            videos.append({
                                'index': i,
                                'title': entry.get('title', f'Video {i+1}'),
                                'length': entry.get('duration', 0) or 0,
                                'author': entry.get('uploader') or info.get('uploader', 'Unknown'),
                                'url': video_url,
                            })
                
                return {
                    'title': info.get('title', 'Unknown Playlist'),
                    'video_count': len(videos),
                    'videos': videos,
                    'url': url,
                }
        except Exception as e:
            raise ValueError(f"{DesktopLocale.get('media_playlist_info_error')}: {str(e)}")
    
    def download_audio(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[int, int], None]] = None,
        audio_track: str = 'default',
        filename_prefix: Optional[str] = None,
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> str:
        """
        Download audio from a YouTube video.
        
        Args:
            url: YouTube video URL
            progress_callback: Callback function (bytes_downloaded, total_bytes)
            audio_track: Language code of audio track to download (e.g., 'en', 'zh', 'default')
            filename_prefix: Optional prefix for the filename
            
        Returns:
            Path to the downloaded audio file
        """
        
        # Build format string for specific audio track
        if audio_track and audio_track != 'default':
            format_str = f'bestaudio[language={audio_track}]/bestaudio/best'
        else:
            format_str = 'bestaudio/best'
        
        # Progress hook
        def progress_hook(d):
            if cancel_check and cancel_check():
                raise ValueError(DesktopLocale.get('operation_cancelled'))
                
            if progress_callback and d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                if total > 0:
                    progress_callback(downloaded, total)
        
        # Get video title first for filename
        # Get video title first for filename
        opts = {'quiet': True}
        opts = self._get_ydl_opts(opts)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                title = info.get('title', 'audio')
        except Exception:
            # Fallback title if extraction fails
            title = 'audio_download'
        
        safe_title = self._sanitize_filename(title)
        if filename_prefix:
            safe_title = f"{filename_prefix}_{safe_title}"
        
        output_template = str(Path(self.output_dir) / f"{safe_title}.%(ext)s")
        
        ydl_opts = {
            'format': format_str,
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [progress_hook] if progress_callback else [],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        ydl_opts = self._get_ydl_opts(ydl_opts)
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Find the downloaded file (extension might vary: m4a, webm, etc.)
            output_path = ""
            for f in os.listdir(self.output_dir):
                if f.startswith(safe_title):
                    # Check if it's the file we just likely downloaded (ignoring par/temp files)
                    if not f.endswith('.part') and not f.endswith('.ytdl'):
                         output_path = str(Path(self.output_dir) / f)
                         break
            
            if not output_path:
                 # Fallback: try to guess common extensions
                 for ext in ['m4a', 'webm', 'mp3', 'opus', 'wav']:
                     p = Path(self.output_dir) / f"{safe_title}.{ext}"
                     if p.exists():
                         output_path = str(p)
                         break
            
            if not output_path:
                raise ValueError(DesktopLocale.get('media_audio_not_found'))
            
            return output_path
            
        except Exception as e:
            # Cleanup on error or cancellation
            # Try to delete any partial or complete files matching the title to avoid corruption
            try:
                for f in os.listdir(self.output_dir):
                    if f.startswith(safe_title):
                        file_path = Path(self.output_dir) / f
                        try:
                            if file_path.exists():
                                logger.info(f"Cleaning up file after error: {file_path}")
                                os.remove(file_path)
                        except OSError:
                            pass
            except Exception:
                pass
                
            raise ValueError(f"{DesktopLocale.get('media_download_error')}: {str(e)}")
    
    def download_playlist(
        self,
        url: str,
        selected_indices: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        audio_track: str = 'default',
        cancel_check: Optional[Callable[[], bool]] = None
    ) -> List[str]:
        try:
            # Get playlist info first
            playlist_info = self.get_playlist_info(url)
            videos = playlist_info['videos']
            
            if selected_indices is not None:
                videos = [videos[i] for i in selected_indices if i < len(videos)]
            
            downloaded_files = []
            total = len(videos)
            
            for i, video in enumerate(videos):
                # Check cancellation
                if cancel_check and cancel_check():
                    break
                    
                try:
                    if progress_callback:
                        progress_callback(i + 1, total, video['title'])
                    
                    if not video.get('url'):
                        logger.warning(f"{DesktopLocale.get('media_skip_no_url')}: {video.get('title')}")
                        continue
                        
                    # Download individual video
                    output_path = self.download_audio(
                        video['url'],
                        audio_track=audio_track,
                        filename_prefix=f"{i+1:03d}",
                        cancel_check=cancel_check
                    )
                    downloaded_files.append(output_path)
                    
                except Exception as e:
                    logger.error(f"{DesktopLocale.get('media_skip_video')} {video.get('title', 'Unknown')}: {str(e)}")
                    continue
            
            return downloaded_files
            
        except Exception as e:
            raise ValueError(f"{DesktopLocale.get('media_playlist_download_error')}: {str(e)}")
    
    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove invalid characters from filename."""
        # Remove characters that are invalid in Windows filenames
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, '', filename)
        # Limit length
        return sanitized[:100].strip()
    
    @staticmethod
    def format_duration(seconds: int | float | None) -> str:
        """Format duration in seconds to HH:MM:SS or MM:SS."""
        if not seconds:
            return DesktopLocale.get("unknown")
        # Ensure integer for formatting
        seconds = int(seconds)
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes}:{secs:02d}"
