
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Strict Allow-List: Formats known to work reliably with Gemini
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aiff', '.aac', '.ogg', '.flac'}

def get_ffmpeg_cmd() -> Optional[str]:
    """
    Get the command/path to invoke ffmpeg.
    Checks system PATH first, then current directory.
    Returns: 'ffmpeg', './ffmpeg.exe', or None if not found.
    """
    # 1. Try system PATH
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return "ffmpeg"
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # 2. Try current directory
    local_binary = Path(os.getcwd()) / "ffmpeg.exe"
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
            "-b:a", "192k",   # High quality speech
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
