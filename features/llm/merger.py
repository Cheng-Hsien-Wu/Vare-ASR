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
        """Merge corrected chunks into single SRT.
        
        Args:
            corrected_contents: List of corrected SRT content from each chunk
            overlap_counts: Number of overlap segments per chunk (for dedup)
            
        Returns:
            Merged SRT content with duplicates removed
        """
        if not corrected_contents:
            return ""
        
        if len(corrected_contents) == 1:
            return corrected_contents[0]
        
        # Parse all chunks
        all_segments: List[Tuple[SRTSegment, int]] = []  # (segment, chunk_index)
        
        for chunk_idx, content in enumerate(corrected_contents):
            segments = SRTParser.parse(content)
            overlap = (overlap_counts[chunk_idx] if overlap_counts else 0)
            
            for seg_idx, segment in enumerate(segments):
                # Skip overlap segments from non-first chunks
                if chunk_idx > 0 and seg_idx < overlap:
                    continue
                all_segments.append((segment, chunk_idx))
        
        if not all_segments:
            return ""
        
        # Remove duplicates based on timestamp overlap
        merged_segments = self._deduplicate_segments(all_segments)
        
        # Sort by start time
        merged_segments.sort(key=lambda s: s.start_time)
        
        # Rebuild SRT with sequential indices
        return self._build_srt(merged_segments)
    
    def _deduplicate_segments(
        self, 
        segments: List[Tuple[SRTSegment, int]]
    ) -> List[SRTSegment]:
        """Remove duplicate segments based on timestamp overlap.
        
        Args:
            segments: List of (segment, chunk_index) tuples
            
        Returns:
            Deduplicated list of segments
        """
        if not segments:
            return []
        
        # Sort by start time, then by chunk index
        sorted_segments = sorted(segments, key=lambda x: (x[0].start_time, x[1]))
        
        result: List[SRTSegment] = []
        
        for segment, chunk_idx in sorted_segments:
            is_duplicate = False
            
            for existing in result:
                if self._is_same_segment(segment, existing):
                    is_duplicate = True
                    # If prefer_earlier is False, we could replace here
                    break
            
            if not is_duplicate:
                result.append(segment)
        
        return result
    
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
