"""
Text Chunker
Splits SRT content into chunks with sliding window for LLM processing.
Single Responsibility: Text chunking only.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .token_estimator import TokenEstimator

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """Configuration for text chunking.
    
    All values are configurable to support different model limits.
    """
    max_tokens: int = 65536           # Maximum input tokens for LLM
    overlap_segments: int = 5         # Number of segments to overlap between chunks
    reserved_for_output: int = 8192   # Reserved tokens for LLM output
    reserved_for_prompt: int = 2048   # Reserved for system prompt
    
    @property
    def available_tokens(self) -> int:
        """Tokens available for content after reservations."""
        return self.max_tokens - self.reserved_for_output - self.reserved_for_prompt


@dataclass
class SRTSegment:
    """Represents a single SRT subtitle segment."""
    index: int
    start_time: float      # Start time in seconds
    end_time: float        # End time in seconds
    text: str              # Subtitle text
    raw_time_str: str = "" # Original time string for reconstruction
    
    def to_srt_block(self) -> str:
        """Convert segment back to SRT format."""
        if self.raw_time_str:
            return f"{self.index}\n{self.raw_time_str}\n{self.text}\n"
        else:
            start = self._seconds_to_srt_time(self.start_time)
            end = self._seconds_to_srt_time(self.end_time)
            return f"{self.index}\n{start} --> {end}\n{self.text}\n"
    
    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@dataclass
class Chunk:
    """Represents a chunk of SRT content for LLM processing."""
    content: str                          # SRT text for this chunk
    segments: List[SRTSegment]            # Parsed segments in this chunk
    overlap_count: int = 0                # Number of overlap segments from previous
    token_count: int = 0                  # Estimated tokens
    chunk_index: int = 0                  # Position in chunk sequence
    total_chunks: int = 1                 # Total number of chunks


class SRTParser:
    """Parses SRT content into segments."""
    
    # SRT time format: 00:00:00,000 --> 00:00:00,000
    TIME_PATTERN = re.compile(
        r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})'
    )
    
    @classmethod
    def parse(cls, srt_content: str) -> List[SRTSegment]:
        """Parse SRT content into list of segments.
        
        Args:
            srt_content: Raw SRT file content
            
        Returns:
            List of SRTSegment objects
        """
        segments = []
        blocks = re.split(r'\n\n+', srt_content.strip())
        
        for block in blocks:
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if len(lines) < 2:
                continue
            
            # Try to find time line
            time_line_idx = -1
            for i, line in enumerate(lines):
                if cls.TIME_PATTERN.search(line):
                    time_line_idx = i
                    break
            
            if time_line_idx == -1:
                continue
            
            # Parse index (line before time, if exists and is numeric)
            index = 0
            if time_line_idx > 0:
                try:
                    index = int(lines[time_line_idx - 1].strip())
                except ValueError:
                    pass
            
            # Parse time
            time_match = cls.TIME_PATTERN.search(lines[time_line_idx])
            if not time_match:
                continue
                
            start_time = cls._parse_time(time_match, 1)
            end_time = cls._parse_time(time_match, 5)
            
            # Get text (everything after time line)
            text_lines = lines[time_line_idx + 1:]
            text = '\n'.join(text_lines)
            
            segments.append(SRTSegment(
                index=index or len(segments) + 1,
                start_time=start_time,
                end_time=end_time,
                text=text,
                raw_time_str=lines[time_line_idx]
            ))
        
        return segments
    
    @classmethod
    def _parse_time(cls, match: re.Match, start_group: int) -> float:
        """Parse time from regex match groups."""
        hours = int(match.group(start_group))
        minutes = int(match.group(start_group + 1))
        seconds = int(match.group(start_group + 2))
        millis = int(match.group(start_group + 3))
        return hours * 3600 + minutes * 60 + seconds + millis / 1000


class TextChunker:
    """Splits SRT content into chunks with sliding window.
    
    Implements sliding window chunking to handle long transcripts
    that exceed LLM token limits.
    """
    
    def __init__(
        self, 
        config: Optional[ChunkConfig] = None,
        estimator: Optional[TokenEstimator] = None
    ):
        """Initialize chunker.
        
        Args:
            config: Chunking configuration (uses defaults if None)
            estimator: Token estimator (creates new if None)
        """
        self.config = config or ChunkConfig()
        self.estimator = estimator or TokenEstimator()
    
    def needs_chunking(self, srt_content: str, prompt: str = "") -> bool:
        """Check if content needs to be chunked.
        
        Args:
            srt_content: SRT content to check
            prompt: System prompt that will be used
            
        Returns:
            True if content exceeds available token limit
        """
        total_tokens = self.estimator.count_tokens(srt_content + prompt)
        return total_tokens > self.config.available_tokens
    
    def chunk_srt(self, srt_content: str, prompt: str = "") -> List[Chunk]:
        """Split SRT content into chunks that fit within token limit.
        
        Each chunk includes overlap segments from previous chunk
        to maintain context and enable proper merging.
        
        Args:
            srt_content: Full SRT content
            prompt: System prompt (used to calculate available space)
            
        Returns:
            List of Chunk objects
        """
        # Parse SRT into segments
        segments = SRTParser.parse(srt_content)
        
        if not segments:
            return [Chunk(content=srt_content, segments=[], token_count=0)]
        
        # Calculate token budget
        prompt_tokens = self.estimator.count_tokens(prompt)
        available = self.config.available_tokens - prompt_tokens
        
        # Check if chunking is needed
        total_tokens = self.estimator.count_tokens(srt_content)
        if total_tokens <= available:
            return [Chunk(
                content=srt_content,
                segments=segments,
                token_count=total_tokens,
                chunk_index=0,
                total_chunks=1
            )]
        
        # Build chunks
        chunks = []
        current_segments: List[SRTSegment] = []
        current_tokens = 0
        overlap_segments: List[SRTSegment] = []
        
        for segment in segments:
            segment_srt = segment.to_srt_block()
            segment_tokens = self.estimator.count_tokens(segment_srt)
            
            # Check if adding this segment would exceed limit
            if current_tokens + segment_tokens > available and current_segments:
                # Create chunk from current segments
                chunk_content = self._segments_to_srt(current_segments)
                chunks.append(Chunk(
                    content=chunk_content,
                    segments=current_segments.copy(),
                    overlap_count=len(overlap_segments),
                    token_count=current_tokens,
                    chunk_index=len(chunks)
                ))
                
                # Prepare overlap for next chunk
                overlap_segments = current_segments[-self.config.overlap_segments:]
                current_segments = overlap_segments.copy()
                current_tokens = sum(
                    self.estimator.count_tokens(s.to_srt_block()) 
                    for s in current_segments
                )
            
            current_segments.append(segment)
            current_tokens += segment_tokens
        
        # Add final chunk
        if current_segments:
            chunk_content = self._segments_to_srt(current_segments)
            chunks.append(Chunk(
                content=chunk_content,
                segments=current_segments.copy(),
                overlap_count=len(overlap_segments) if chunks else 0,
                token_count=current_tokens,
                chunk_index=len(chunks)
            ))
        
        # Update total_chunks in all chunks
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        logger.info(f"Split SRT into {total} chunks (total tokens: {total_tokens})")
        return chunks
    
    def chunk_text(self, text: str, prompt: str = "") -> List[Chunk]:
        """Split plain text into chunks that fit within token limit.
        
        Args:
            text: Full text content
            prompt: System prompt
            
        Returns:
            List of Chunk objects
        """
        # Calculate budget
        prompt_tokens = self.estimator.count_tokens(prompt)
        available = self.config.available_tokens - prompt_tokens
        
        total_tokens = self.estimator.count_tokens(text)
        if total_tokens <= available:
            return [Chunk(content=text, segments=[], token_count=total_tokens, total_chunks=1)]
            
        # Split by double newlines (paragraphs) first, then single newlines
        blocks = re.split(r'(\n\n+)', text)
        # Re-attach delimiters
        rebuilt_blocks = []
        for i in range(0, len(blocks)-1, 2):
            rebuilt_blocks.append(blocks[i] + blocks[i+1])
        if len(blocks) % 2 == 1:
            rebuilt_blocks.append(blocks[-1])
            
        chunks = []
        current_text = ""
        current_tokens = 0
        
        # Simple accumulation, no overlap for now (complex to dedupe text without timestamps)
        for block in rebuilt_blocks:
            block_tokens = self.estimator.count_tokens(block)
            
            if current_tokens + block_tokens > available and current_text:
                chunks.append(Chunk(
                    content=current_text,
                    segments=[],
                    token_count=current_tokens,
                    chunk_index=len(chunks)
                ))
                current_text = ""
                current_tokens = 0
            
            current_text += block
            current_tokens += block_tokens
            
        # Final connection
        if current_text:
            chunks.append(Chunk(
                content=current_text,
                segments=[],
                token_count=current_tokens,
                chunk_index=len(chunks)
            ))
            
        # Update total
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
            
        logger.info(f"Split text into {total} chunks")
        return chunks

    def _segments_to_srt(self, segments: List[SRTSegment]) -> str:
        """Convert list of segments back to SRT format."""
        blocks = []
        for i, segment in enumerate(segments, 1):
            # Re-index for clean output
            segment_copy = SRTSegment(
                index=i,
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.text,
                raw_time_str=segment.raw_time_str
            )
            blocks.append(segment_copy.to_srt_block())
        return '\n'.join(blocks)
