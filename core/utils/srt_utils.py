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



def segments_to_dicts(segments: List[TranscriptionSegment]) -> List[dict]:
    """
    Convert segments to list of dictionaries for JSON serialization
    """
    results = []
    for seg in segments:
        seg_dict = {
            "start": seg.start,
            "end": seg.end,
            "text": seg.text
        }
        if seg.words:
            # Format word objects (they are usually named tuples or objects from faster_whisper)
            words_list = []
            for w in seg.words:
                # Handle both object (CTranslate2) and dict formats safely
                if isinstance(w, dict):
                     w_start = w.get('start', 0)
                     w_end = w.get('end', 0)
                     w_word = w.get('word', '')
                     w_prob = w.get('probability', 0)
                else:
                     w_start = getattr(w, 'start', 0)
                     w_end = getattr(w, 'end', 0)
                     w_word = getattr(w, 'word', '')
                     w_prob = getattr(w, 'probability', 0)
                
                words_list.append({
                    "start": w_start,
                    "end": w_end,
                    "word": w_word,
                    "probability": w_prob
                })
            seg_dict["words"] = words_list
        results.append(seg_dict)
    return results


def save_json(segments: List[TranscriptionSegment], output_path: str) -> None:
    """
    Save full transcription data (including word timestamps) to JSON
    """
    import json
    data = segments_to_dicts(segments)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"JSON data saved to: {output_path}")

def srt_str_to_txt(srt_content: str) -> str:
    """
    Convert SRT string content to plain text (stripping timestamps and indices)
    for auto-derivation.
    """
    import re
    lines = srt_content.strip().split('\n')
    text_lines = []
    
    # Simple state machine or regex approach
    # Identifying timestamp lines: 00:00:00,000 --> 00:00:00,000 (allowing flexible whitespace)
    timestamp_pattern = re.compile(r'^\s*\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}\s*$')
    
    is_text = False
    
    for line in lines:
        line = line.strip()
        if not line:
            is_text = False
            continue
            
        if line.isdigit():
            # Potential index, look ahead check usually safer but for standard SRT simple check works
            # If previous was empty, this is likely index
            is_text = False
            continue
            
        if timestamp_pattern.match(line):
            is_text = True
            continue
            
        if is_text:
            # Strip line numbers added by LLM correction (format: "123. text")
            line_num_match = re.match(r'^\d+\.\s*', line)
            if line_num_match:
                line = line[line_num_match.end():].strip()
            text_lines.append(line)
            
    return "\n".join(text_lines)
