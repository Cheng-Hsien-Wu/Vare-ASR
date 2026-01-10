"""
Faster-Whisper Backend for Vare
Built-in Silero VAD support for better segmentation
"""

import logging
from typing import List, Optional, Dict
from features.transcription.engines.base import ASRBackend, TranscriptionSegment

logger = logging.getLogger(__name__)


# VAD Default Parameters
DEFAULT_VAD_THRESHOLD = 0.5
DEFAULT_MIN_SPEECH_DURATION_MS = 250
DEFAULT_MAX_SPEECH_DURATION_S = 15.0
DEFAULT_MIN_SILENCE_DURATION_MS = 400
DEFAULT_SPEECH_PAD_MS = 100

class FasterWhisperBackend(ASRBackend):
    """Backend using faster-whisper (CTranslate2) with built-in VAD"""
    
    def __init__(
        self, 
        model_name: str = "SoybeanMilk/faster-whisper-Breeze-ASR-25",
        device: str = "cuda",
        compute_type: str = "float16",
        cpu_threads: int = 4,
        num_workers: int = 1,
        download_root: Optional[str] = None,
        local_files_only: bool = False,
        flash_attention: bool = False,
        **kwargs
    ):
        super().__init__(model_name, device, **kwargs)
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self.download_root = download_root
        self.local_files_only = local_files_only
        self.flash_attention = flash_attention
        
    def load_model(self) -> None:
        """Load faster-whisper CT2 model"""
        from faster_whisper import WhisperModel
        logger.info(f"Loading model: {self.model_name}")
        logger.info(f"Device: {self.device}, Compute type: {self.compute_type}")
        if self.download_root:
            logger.info(f"Download root: {self.download_root}")
        
        def _try_load():
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                num_workers=self.num_workers,
                download_root=self.download_root if self.download_root else None,
                local_files_only=self.local_files_only,
            )
        
        max_retries = 3
        last_error = None
        
        for attempt in range(max_retries):
            try:
                _try_load()
                logger.info(f"✓ Faster-Whisper model loaded successfully")
                return
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # Handle Windows file lock issue (WinError 32)
                if "WinError 32" in error_str or "being used by another process" in error_str:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠ File lock detected (attempt {attempt + 1}/{max_retries}), waiting and retrying...")
                        self._cleanup_incomplete_files()
                        self._force_gc_and_wait()
                    else:
                        logger.error("⚠ File lock persists. Please close any other programs using the model files and try again.")
                        raise RuntimeError(f"Failed to load model after {max_retries} attempts: {e}")
                else:
                    raise RuntimeError(f"Failed to load model: {e}")
        
        raise RuntimeError(f"Failed to load model: {last_error}")
    
    def _force_gc_and_wait(self) -> None:
        """Force garbage collection and wait to release file handles"""
        import gc
        import time
        
        gc.collect()
        time.sleep(2)  # Wait for OS to release file handles
    
    def _cleanup_incomplete_files(self) -> None:
        """Clean up .incomplete files from failed downloads"""
        from pathlib import Path
        
        if not self.download_root:
            return
        
        download_path = Path(self.download_root)
        if not download_path.exists():
            return
        
        # Look for .incomplete files in the cache directory
        for incomplete_file in download_path.rglob("*.incomplete"):
            try:
                logger.info(f"  Removing: {incomplete_file.name}")
                incomplete_file.unlink()
            except PermissionError:
                logger.warning(f"  File still locked: {incomplete_file.name} (will retry)")
            except Exception as e:
                logger.error(f"  Could not remove {incomplete_file.name}: {e}")
    
    def transcribe(
        self, 
        audio_path: str, 
        language: Optional[str] = "zh",
        task: str = "transcribe",
        beam_size: int = 5,
        best_of: int = 5,
        patience: float = 1.0,
        length_penalty: float = 1.0,
        repetition_penalty: float = 1.0,
        no_repeat_ngram_size: int = 0,
        temperature: float = 0.0,
        log_prob_threshold: float = -1.0,
        no_speech_threshold: float = 0.6,
        compression_ratio_threshold: float = 2.4,
        condition_on_previous_text: bool = True,
        prompt_reset_on_temperature: float = 0.5,
        hallucination_silence_threshold: Optional[float] = None,
        suppress_blank: bool = True,
        word_timestamps: bool = False,
        vad_filter: bool = True,
        vad_parameters: Optional[Dict] = None,
        progress_callback=None,
        initial_prompt: Optional[str] = None,
        **kwargs
    ) -> List[TranscriptionSegment]:
        """
        Transcribe audio with full parameter support
        
        Args:
            audio_path: Path to audio/video file
            language: Language code ("zh", "en", etc.)
            task: "transcribe" or "translate"
            beam_size: Beam search size
            best_of: Number of candidates when sampling
            patience: Beam search patience
            length_penalty: Exponential length penalty
            repetition_penalty: Penalty for repetition
            no_repeat_ngram_size: Prevent N-gram repetition
            temperature: Sampling temperature (0 = greedy)
            log_prob_threshold: Log probability threshold for fallback
            no_speech_threshold: No speech probability threshold
            compression_ratio_threshold: Compression ratio threshold
            condition_on_previous_text: Use previous text as context
            prompt_reset_on_temperature: Reset prompt above this temperature
            hallucination_silence_threshold: Silence duration to skip (hallucination prevention)
            suppress_blank: Suppress blank output at start
            word_timestamps: Generate word-level timestamps
            vad_filter: Enable Silero VAD
            vad_parameters: VAD config dict
            **kwargs: Additional parameters
        """
        if not self.is_loaded():
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        logger.info(f"Transcribing: {audio_path}")
        
        default_vad = {
            "threshold": DEFAULT_VAD_THRESHOLD,
            "min_speech_duration_ms": DEFAULT_MIN_SPEECH_DURATION_MS,
            "max_speech_duration_s": DEFAULT_MAX_SPEECH_DURATION_S,
            "min_silence_duration_ms": DEFAULT_MIN_SILENCE_DURATION_MS,
            "speech_pad_ms": DEFAULT_SPEECH_PAD_MS
        }
        
        if vad_parameters:
            default_vad.update(vad_parameters)
        
        try:
            if vad_filter:
                logger.info(f"Running with Silero VAD (max_speech: {default_vad['max_speech_duration_s']}s)")
            
            # Build transcribe parameters
            transcribe_params = {
                "language": language,
                "task": task,
                "beam_size": beam_size,
                "best_of": best_of,
                "patience": patience,
                "length_penalty": length_penalty,
                "repetition_penalty": repetition_penalty,
                "no_repeat_ngram_size": no_repeat_ngram_size,
                "temperature": temperature,
                "log_prob_threshold": log_prob_threshold,
                "no_speech_threshold": no_speech_threshold,
                "compression_ratio_threshold": compression_ratio_threshold,
                "condition_on_previous_text": condition_on_previous_text,
                "prompt_reset_on_temperature": prompt_reset_on_temperature,
                "suppress_blank": suppress_blank,
                "word_timestamps": word_timestamps,
                "vad_filter": vad_filter,
                "vad_parameters": default_vad if vad_filter else None,
                "initial_prompt": initial_prompt if initial_prompt else None,
            }
            
            # Add hallucination_silence_threshold only if set
            if hallucination_silence_threshold and hallucination_silence_threshold > 0:
                transcribe_params["hallucination_silence_threshold"] = hallucination_silence_threshold
            
            # Execute transcription
            segments_iter, info = self.model.transcribe(audio_path, **transcribe_params)

            total_duration = info.duration
            logger.info(f"Audio duration: {total_duration:.2f}s")
            
            results = []
            for seg in segments_iter:
                if progress_callback and total_duration > 0:
                    percent = seg.end / total_duration
                    progress_callback(min(percent, 1.0))
                
                if seg.text.strip():
                    results.append(TranscriptionSegment(
                        start=seg.start,
                        end=seg.end,
                        text=seg.text.strip()
                    ))
            
            logger.info(f"Transcription complete: {len(results)} segments")
            logger.info(f"Detected language: {info.language} (probability: {info.language_probability:.2%})")
            
            return results
            
        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")
    
    def unload_model(self) -> None:
        """Free model from memory"""
        if self.model is not None:
            del self.model
            self.model = None
            # Note: ctranslate2 handles CUDA memory cleanup internally
            logger.info("Model unloaded from memory")
