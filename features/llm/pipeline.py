"""
LLM Correction Pipeline
Handles the end-to-end process of correcting transcripts using LLM,
including chunking, merging, and unified output derivation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from features.llm.factory import create_provider
from features.llm.token_estimator import TokenEstimator
from features.llm.chunker import TextChunker, ChunkConfig, SRTSegment
from features.llm.merger import ChunkMerger
from core.utils.srt_utils import srt_str_to_txt
from core.utils.audio_utils import slice_audio

logger = logging.getLogger(__name__)

class LLMCorrectionPipeline:
    """
    Unified pipeline for LLM-based transcript correction.
    Encapsulates logic for:
    - Token estimation & Chunking
    - LLM Interaction (with retries handled by provider)
    - Merging results
    - Auto-deriving separate formats (SRT -> TXT)
    """
    
    def __init__(self, config: Dict[str, Any], callbacks: Dict[str, Any]):
        self.config = config
        self.callbacks = callbacks
        self.log_cb = callbacks.get('log', lambda x: None)
        self.progress_cb = callbacks.get('progress', lambda x, y: None)
        
    def run(self, input_path: str, task_index: int) -> None:
        """
        Run the correction pipeline.
        
        Args:
            input_path: Path to the file to correct (usually the raw SRT or TXT)
            task_index: ID for progress updates
        """
        try:
            self.progress_cb(task_index, "llm_correcting")
            self.log_cb(('log_starting_ai_correction',))
            
            # 1. Read Original Content
            path_obj = Path(input_path)
            if not path_obj.exists():
                raise FileNotFoundError(f"Input file not found: {input_path}")
                
            with open(input_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
                
            is_srt = path_obj.suffix.lower() == '.srt'
            if not is_srt and path_obj.suffix.lower() != '.txt':
                # Unknown format: treat as TXT for robust fallback
                is_srt = False

            # 2. Setup LLM Provider & Tools
            provider_name = self.config.get('llm_provider', 'gemini')
            language = self.config.get('language', 'zh')
            
            provider = create_provider(self.config)
            
            # Advanced LLM Params
            system_prompt = self.config.get('llm_system_prompt', None)
            llm_temp = self.config.get('llm_temperature', 0.3)
            enable_web_search = self.config.get('llm_web_search', False)
            max_tokens = self.config.get('llm_max_tokens', 60000)

            # Advanced Context Params
            use_audio_grounding = self.config.get('llm_use_audio_grounding', False)
            audio_input_path = self.config.get('audio_input_path')
            
            # 3. Chunking Strategy
            estimator = TokenEstimator()
            
            # Configure chunking based on audio grounding setting
            # Duration limit only applies when audio grounding is enabled
            custom_max_tokens = self.config.get('llm_max_tokens')
            chunk_config = ChunkConfig(
                max_tokens=custom_max_tokens if custom_max_tokens else 1000000,
                use_audio_grounding=use_audio_grounding  # Duration limit conditional
            )
            
            # Log chunking mode
            if use_audio_grounding:
                self.log_cb(f"Audio grounding enabled: chunking by tokens AND duration (max {chunk_config.max_duration_seconds/60:.0f} min)")
            else:
                self.log_cb("Audio grounding disabled: chunking by tokens only")
                
            chunker = TextChunker(config=chunk_config, estimator=estimator)
            merger = ChunkMerger()
            
            chunks = []
            use_chunking = False
            
            if is_srt:
                if chunker.needs_chunking(original_content, system_prompt or ""):
                    chunks = chunker.chunk_srt(original_content, system_prompt or "")
                    use_chunking = True
            else:
                # For TXT, always chunk to check limits, but if fits in one, len(chunks)==1
                chunks = chunker.chunk_text(original_content, system_prompt or "")
                if len(chunks) > 1:
                    use_chunking = True
            
            # 4. Processing
            corrected_content = ""
            
            if use_chunking:
                self.log_cb(f"Large transcript: {len(chunks)} chunks")
                corrected_chunks = []
                overlap_counts = []
                
                for i, chunk in enumerate(chunks):
                    # Progress Log
                    chunk_info = f"Chunk {i+1}/{len(chunks)}"
                    chunk_info += f" | Tokens: {chunk.token_count}"
                    chunk_start_time = 0.0
                    chunk_end_time = 0.0
                    if chunk.segments:
                        chunk_start_time = chunk.segments[0].start_time
                        chunk_end_time = chunk.segments[-1].end_time
                        start_str = SRTSegment._seconds_to_srt_time(chunk_start_time)
                        end_str = SRTSegment._seconds_to_srt_time(chunk_end_time)
                        chunk_info += f" | Time: {start_str} -> {end_str}"
                    self.log_cb(chunk_info)
                    
                    # Slice audio for this chunk's time range
                    sliced_audio_path = None
                    if use_audio_grounding and audio_input_path and chunk.segments:
                        try:
                            sliced_audio_path = slice_audio(audio_input_path, chunk_start_time, chunk_end_time)
                        except Exception as e:
                            self.log_cb(f"!! Audio slicing failed: {e}. Skipping audio for this chunk.")
                    
                    try:
                        # Extract Plain Text for Correction
                        # Strategy: Text-Only Correction to preserve Timestamp integrity
                        correction_input = chunk.get_plain_text() if is_srt else chunk.content
                        
                        # Define status callback wrapper for this chunk
                        chunk_status_cb = lambda msg: self.progress_cb(task_index, msg)
                        
                        corrected_text = provider.correct_text(
                            correction_input,
                            language=language,
                            system_prompt=system_prompt,
                            temperature=llm_temp,
                            enable_web_search=enable_web_search,
                            max_output_tokens=chunk_config.reserved_for_output,
                            audio_path=sliced_audio_path,  # Use sliced audio instead of full
                            status_update_callback=chunk_status_cb
                        )
                        
                        # Debug: Save raw LLM input/output for troubleshooting
                        try:
                            import tempfile
                            debug_dir = Path(tempfile.gettempdir()) / "vare_llm_debug"
                            debug_dir.mkdir(exist_ok=True)
                            
                            input_lines = [l for l in correction_input.split('\n') if l.strip()]
                            output_lines = [l for l in corrected_text.split('\n') if l.strip()]
                            
                            with open(debug_dir / f"chunk_{i+1}_input.txt", "w", encoding="utf-8") as f:
                                f.write(correction_input)
                            with open(debug_dir / f"chunk_{i+1}_output.txt", "w", encoding="utf-8") as f:
                                f.write(corrected_text)
                            
                            logger.info(f"Debug: Chunk {i+1} input={len(input_lines)} lines, output={len(output_lines)} lines")
                            logger.info(f"Debug files saved to: {debug_dir}")
                        except Exception as debug_e:
                            logger.warning(f"Debug save failed: {debug_e}")
                        
                        if is_srt:
                            # Re-inject corrected text into original segments
                            # This guarantees timestamp preservation
                            chunk.update_from_text(corrected_text)
                            # Re-generate SRT block from updated segments
                            # We access the _segments_to_srt method from the chunker instance
                            corrected_block = chunker._segments_to_srt(chunk.segments)
                            corrected_chunks.append(corrected_block)
                        else:
                            corrected_chunks.append(corrected_text)
                        
                    except Exception as e:
                        self.log_cb(f"!! Chunk {i+1} Failed: {str(e)}")
                        self.log_cb(f"!! Fallback: Using original content for Chunk {i+1}")
                        corrected_chunks.append(chunk.content)
                    finally:
                        # Cleanup temp sliced audio
                        if sliced_audio_path:
                            try:
                                Path(sliced_audio_path).unlink(missing_ok=True)
                            except Exception:
                                pass
                        
                    overlap_counts.append(chunk.overlap_count)
                
                self.log_cb("Merging chunks...")
                if is_srt:
                    corrected_content = merger.merge_results(corrected_chunks, overlap_counts)
                else:
                    corrected_content = merger.merge_text(corrected_chunks)
            else:
                # Single Pass
                if is_srt:
                    # For single pass SRT, we still use the "Text Extraction -> Correction -> Re-injection" flow
                    # to ensure safety. We can treat it as a single chunk.
                    # chunker.chunk_srt returns a list of Chunks, if we call it with huge limit it returns 1 chunk.
                    # Or we can manually parse here.
                    from features.llm.chunker import SRTParser
                    segments = SRTParser.parse(original_content)
                    text_block = "\n".join(s.text for s in segments)
                    
                    corrected_text = provider.correct_text(
                        text_block,
                        language=language,
                        system_prompt=system_prompt,
                        temperature=llm_temp,
                        enable_web_search=enable_web_search,
                        max_output_tokens=chunk_config.reserved_for_output,
                        audio_path=audio_input_path if use_audio_grounding else None
                    )
                    
                    # Re-inject
                    lines = [line.strip() for line in corrected_text.strip().split('\n') if line.strip()]
                    limit = min(len(lines), len(segments))
                    for i in range(limit):
                        segments[i].text = lines[i]
                        
                    corrected_content = chunker._segments_to_srt(segments)
                    
                else:
                    # Plain text single pass
                    corrected_content = provider.correct_text(
                        original_content,
                        language=language,
                        system_prompt=system_prompt,
                        temperature=llm_temp,
                        enable_web_search=enable_web_search,
                        max_output_tokens=chunk_config.reserved_for_output,
                        audio_path=audio_input_path if use_audio_grounding else None,
                        status_update_callback=lambda msg: self.progress_cb(task_index, msg)
                    )
            
            # 5. Save Primary Output
            # Logic: If input is .srt -> output is _corrected.srt
            # If input is .txt -> output is _corrected.txt
            
            # We enforce UNIFIED strategy:
            # - If we corrected SRT, we assume user wants clean SRT.
            # - AND we assume user ALSO wants clean TXT derived from that SRT.
            
            # Construct output filename
            stem = path_obj.stem
            parent = path_obj.parent
            # e.g. "video.srt" -> "video_corrected.srt"
            
            # Primary Path
            primary_ext = path_obj.suffix
            primary_out_name = f"{stem}_corrected{primary_ext}"
            primary_out_path = parent / primary_out_name
            
            with open(primary_out_path, 'w', encoding='utf-8') as f:
                f.write(corrected_content)
                
            self.log_cb(f"AI correction saved to: {primary_out_name}")
            
            # 6. Auto-Derivation (Unified Output)
            # If we just saved an SRT, verify/derive the TXT version
            if is_srt:
                derived_txt_name = f"{stem}_corrected.txt"
                derived_txt_path = parent / derived_txt_name
                
                # Derive text using the helper that strips tags
                derived_content = srt_str_to_txt(corrected_content)
                
                with open(derived_txt_path, 'w', encoding='utf-8') as f:
                    f.write(derived_content)
                    
                self.log_cb(f"AI correction sidecar (TXT) saved to: {derived_txt_name}")
            
            # Note: We do NOT auto-derive SRT from TXT because alignment is impossible to guarantee.
            # This is why our unified strategy prefers SRT as the input source.
            
        except Exception as e:
            # Logging and re-raising to be handled by worker
            self.log_cb(f"AI correction pipeline error: {e}")
            raise e
