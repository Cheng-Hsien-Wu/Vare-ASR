
import os
import subprocess
import tempfile
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Strict Allow-List: Formats known to work reliably with Gemini
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aiff', '.aac', '.ogg', '.flac'}

def get_ffmpeg_cmd() -> Optional[str]:
    """
    Get the command/path to invoke ffmpeg.
    Checks system PATH first, then bundled app dir (PyInstaller), then current directory.
    Returns: 'ffmpeg', './ffmpeg.exe', or None if not found.
    """
    # 1. Try system PATH
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    binary_name = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"

    # 2. Try bundled path (PyInstaller/Flet)
    # When running as .exe, files are extracted to sys._MEIPASS
    if hasattr(sys, '_MEIPASS'):
        bundled_binary = Path(sys._MEIPASS) / binary_name
        if bundled_binary.exists():
            logger.info(f"Found bundled FFmpeg: {bundled_binary}")
            return str(bundled_binary)

    # 3. Try current directory (Dev mode or portable)
    local_binary = Path(os.getcwd()) / binary_name
    if local_binary.exists():
        return str(local_binary)
        
    return None

def ensure_audio_format(file_path: str, target_ext: str = ".mp3", max_size_mb: int = 20) -> str:
    """
    Ensure the audio file is in a supported format and within reasonable size.
    If the file is a video or unsupported audio format, it extracts/converts to MP3.
    
    Args:
        file_path: Absolute path to the input file.
        target_ext: Target extension for conversion (default: .mp3).
        max_size_mb: Max size in MB. If larger, try to convert/compress (not yet strictly verified).
        
    Returns:
        Path to the compatible audio file (original or temporary converted file).
        
    Raises:
        RuntimeError: If conversion is required but ffmpeg is missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Check extension (case insensitive)
    ext = path.suffix.lower()
    
    # 1. Direct Pass: If supported and small enough
    if ext in ALLOWED_AUDIO_EXTENSIONS:
        return str(path)

    # 2. Conversion needed
    logger.info(f"Format {ext} not in allow-list {ALLOWED_AUDIO_EXTENSIONS}. Converting to {target_ext}...")
    
    # Check FFmpeg availability
    ffmpeg_cmd = get_ffmpeg_cmd()
    if not ffmpeg_cmd:
        error_msg = "FFmpeg not found. Cannot convert audio. Please install FFmpeg to use Audio Grounding with video/unsupported formats."
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    # Create a temporary file
    temp_dir = tempfile.gettempdir()
    temp_filename = f"converted_{path.stem}{target_ext}"
    output_path = Path(temp_dir) / temp_filename
    
    try:
        cmd = [
            ffmpeg_cmd,
            "-y",
            "-i", str(path),
            "-vn",            # Disable video recording
            "-acodec", "libmp3lame",
            "-b:a", "128k",   # Sufficient for speech, smaller file
            str(output_path)
        ]
        
        # Suppress output unless error
        process = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        logger.info(f"Successfully converted to: {output_path}")
        return str(output_path)

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        logger.error(f"FFmpeg conversion failed: {error_msg}")
        raise RuntimeError(f"Failed to convert audio format: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error during audio conversion: {e}")
        raise


def _seconds_to_ffmpeg_time(seconds: float) -> str:
    """Convert seconds to FFmpeg time format (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def slice_audio(input_path: str, start_seconds: float, end_seconds: float) -> str:
    """
    Slice audio file to a specific time range using FFmpeg stream copy (fast).
    
    Args:
        input_path: Path to source audio file
        start_seconds: Start time in seconds
        end_seconds: End time in seconds
        
    Returns:
        Path to temporary sliced audio file
        
    Raises:
        RuntimeError: If FFmpeg is not available or slicing fails
    """
    ffmpeg_cmd = get_ffmpeg_cmd()
    if not ffmpeg_cmd:
        raise RuntimeError("FFmpeg not found. Cannot slice audio.")
    
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")
    
    # Create temp file with descriptive name
    temp_dir = tempfile.gettempdir()
    temp_filename = f"slice_{int(start_seconds)}_{int(end_seconds)}_{path.stem}{path.suffix}"
    output_path = Path(temp_dir) / temp_filename
    
    # Convert seconds to FFmpeg time format
    start_str = _seconds_to_ffmpeg_time(start_seconds)
    end_str = _seconds_to_ffmpeg_time(end_seconds)
    
    try:
        cmd = [
            ffmpeg_cmd,
            "-y",                    # Overwrite output
            "-i", str(path),         # Input file
            "-ss", start_str,        # Start time
            "-to", end_str,          # End time
            "-c", "copy",            # Stream copy (fast, no re-encode)
            str(output_path)
        ]
        
        logger.info(f"Slicing audio: {start_str} -> {end_str}")
        
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        logger.info(f"Audio sliced successfully: {output_path}")
        return str(output_path)
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
        logger.error(f"FFmpeg slicing failed: {error_msg}")
        raise RuntimeError(f"Failed to slice audio: {error_msg}")
    except Exception as e:
        logger.error(f"Unexpected error during audio slicing: {e}")
        raise
