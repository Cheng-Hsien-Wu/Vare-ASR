"""
Chunk Merger
Merges chunked LLM correction results and removes duplicates.
Single Responsibility: Result merging only.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .chunker import SRTParser, SRTSegment

logger = logging.getLogger(__name__)


@dataclass
class MergeConfig:
    """Configuration for chunk merging."""
    time_tolerance: float = 0.5      # Seconds tolerance for duplicate detection
    prefer_earlier: bool = True      # Prefer segments from earlier chunks when overlapping


class ChunkMerger:
    """Merges chunked LLM results and removes duplicates.
    
    After LLM processes multiple chunks with overlapping segments,
    this class merges them back into a single coherent transcript.
    """
    
    def __init__(self, config: Optional[MergeConfig] = None):
        """Initialize merger.
        
        Args:
            config: Merge configuration (uses defaults if None)
        """
        self.config = config or MergeConfig()
    
    def merge_results(
        self, 
        corrected_contents: List[str],
        overlap_counts: Optional[List[int]] = None
    ) -> str:
        """Merge corrected chunks into single SRT using monotonic splicing.
        
        Args:
            corrected_contents: List of corrected SRT content from each chunk
            overlap_counts: Unused in this robust implementation but kept for API compatibility.
            
        Returns:
            Merged SRT content with duplicates removed and time continuity enforced.
        """
        if not corrected_contents:
            return ""
        
        merged_segments: List[SRTSegment] = []
        
        for content in corrected_contents:
            chunk_segs = SRTParser.parse(content)
            if not chunk_segs:
                continue
                
            if not merged_segments:
                merged_segments.extend(chunk_segs)
                continue
            
            # Start of the new chunk is our "Cut Point"
            first_new_start = chunk_segs[0].start_time
            tolerance = 0.05 # Small tolerance for floating point
            
            # 1. Backtrack: Remove segments from previous chunks that start AFTER the new chunk starts
            #    (These are completely superseded by the new chunk's overlap region)
            while merged_segments and merged_segments[-1].start_time >= first_new_start - tolerance:
                merged_segments.pop()
                
            # 2. Trim: If the last remaining segment extends into the new chunk, trim it
            #    (Prevent partial overlaps)
            if merged_segments and merged_segments[-1].end_time > first_new_start:
                # Trim the end
                merged_segments[-1].end_time = first_new_start
                # If trimming made it empty/invalid, remove it
                if merged_segments[-1].end_time <= merged_segments[-1].start_time + tolerance:
                    merged_segments.pop()
            
            merged_segments.extend(chunk_segs)
        
        if not merged_segments:
            return ""
            
        # Rebuild SRT with sequential indices
        return self._build_srt(merged_segments)

    # Removed _deduplicate_segments as it is no longer used
    # _is_same_segment also unused but can be kept or removed. Removing for cleanliness.
    
    def _is_same_segment(self, seg1: SRTSegment, seg2: SRTSegment) -> bool:
        """Check if two segments are the same based on timestamps.
        
        Args:
            seg1: First segment
            seg2: Second segment
            
        Returns:
            True if segments are considered duplicates
        """
        tolerance = self.config.time_tolerance
        
        # Check if start times are within tolerance
        start_match = abs(seg1.start_time - seg2.start_time) <= tolerance
        end_match = abs(seg1.end_time - seg2.end_time) <= tolerance
        
        return start_match and end_match
    
    def _build_srt(self, segments: List[SRTSegment]) -> str:
        """Build SRT content from segments with sequential indices.
        
        Args:
            segments: List of segments (should be sorted)
            
        Returns:
            Valid SRT format string
        """
        blocks = []
        
        for i, segment in enumerate(segments, 1):
            # Create new segment with sequential index
            start = self._seconds_to_srt_time(segment.start_time)
            end = self._seconds_to_srt_time(segment.end_time)
            
            block = f"{i}\n{start} --> {end}\n{segment.text}\n"
            blocks.append(block)
        
        return '\n'.join(blocks)
    
    @staticmethod
    def _seconds_to_srt_time(seconds: float) -> str:
        """Convert seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


    def merge_text(self, corrected_contents: List[str]) -> str:
        """Merge corrected text chunks (simple concatenation).
        
        Args:
            corrected_contents: List of corrected strings
            
        Returns:
            Merged text
        """
        return "".join(corrected_contents)


class ChunkedCorrectionProcessor:
    """High-level processor for chunked LLM correction.
    
    Coordinates chunking, LLM calls, and merging.
    Open/Closed Principle: Uses dependency injection for LLM provider.
    """
    
    def __init__(self, chunker, merger, provider):
        """Initialize processor with dependencies.
        
        Args:
            chunker: TextChunker instance
            merger: ChunkMerger instance  
            provider: LLMProvider instance
        """
        self.chunker = chunker
        self.merger = merger
        self.provider = provider
    
    def process(
        self,
        srt_content: str,
        language: str = "zh-tw",
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        progress_callback: Optional[callable] = None
    ) -> str:
        """Process SRT content with chunked LLM correction.
        
        Args:
            srt_content: Full SRT content to correct
            language: Language code for prompts
            system_prompt: Optional custom system prompt
            temperature: LLM temperature
            progress_callback: Optional callback(current, total) for progress
            
        Returns:
            Corrected and merged SRT content
        """
        # Split into chunks
        chunks = self.chunker.chunk_srt(srt_content, system_prompt or "")
        
        if len(chunks) == 1:
            # No chunking needed
            logger.info("Content fits in single chunk, processing directly")
            return self.provider.correct_text(
                srt_content,
                language=language,
                system_prompt=system_prompt,
                temperature=temperature
            )
        
        logger.info(f"Processing {len(chunks)} chunks")
        
        # Process each chunk
        corrected_contents = []
        overlap_counts = []
        
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(i + 1, len(chunks))
            
            logger.info(f"Processing chunk {i+1}/{len(chunks)} ({chunk.token_count} tokens)")
            
            corrected = self.provider.correct_text(
                chunk.content,
                language=language,
                system_prompt=system_prompt,
                temperature=temperature
            )
            
            corrected_contents.append(corrected)
            overlap_counts.append(chunk.overlap_count)
        
        # Merge results
        logger.info("Merging corrected chunks")
        merged = self.merger.merge_results(corrected_contents, overlap_counts)
        
        return merged
