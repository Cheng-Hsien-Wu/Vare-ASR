"""
SRT Subtitle Format Utilities
Handles conversion of transcription segments to SRT format
"""
import logging
from typing import List
from features.transcription.engines.base import TranscriptionSegment

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm)
    
    Args:
        seconds: Time in seconds
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def segments_to_srt(segments: List[TranscriptionSegment]) -> str:
    """
    Convert transcription segments to SRT format
    
    Args:
        segments: List of TranscriptionSegment objects
        
    Returns:
        SRT formatted string
    """
    srt_lines = []
    
    for idx, segment in enumerate(segments, start=1):
        # Subtitle index
        srt_lines.append(str(idx))
        
        # Timestamp line
        start = format_timestamp(segment.start)
        end = format_timestamp(segment.end)
        srt_lines.append(f"{start} --> {end}")
        
        # Text content
        srt_lines.append(segment.text)
        
        # Blank line separator
        srt_lines.append("")
    
    return "\n".join(srt_lines)


def save_srt(segments: List[TranscriptionSegment], output_path: str) -> None:
    """
    Save transcription segments to SRT file
    
    Args:
        segments: List of TranscriptionSegment objects
        output_path: Path to output .srt file
    """
    srt_content = segments_to_srt(segments)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    logger.info(f"SRT saved to: {output_path}")


def segments_to_txt(segments: List[TranscriptionSegment]) -> str:
    """
    Convert segments to plain text (no timestamps)
    
    Args:
        segments: List of TranscriptionSegment objects
        
    Returns:
        Plain text string
    """
    return "\n".join(seg.text for seg in segments)


def save_txt(segments: List[TranscriptionSegment], output_path: str) -> None:
    """
    Save transcription as plain text file
    
    Args:
        segments: List of TranscriptionSegment objects
        output_path: Path to output .txt file
    """
    txt_content = segments_to_txt(segments)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(txt_content)
    
    logger.info(f"Text saved to: {output_path}")


