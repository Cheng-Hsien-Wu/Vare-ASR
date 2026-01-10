"""
Transcription Worker
Multiprocessing worker for transcription with immediate stop support.
"""

import multiprocessing
import threading
from pathlib import Path
from typing import Dict, Callable, Any, List
from multiprocessing import Queue


def _transcribe_process(task_index: int, task_input_path: str, task_output_path: str, config: Dict[str, Any], msg_queue: Queue) -> None:
    """Worker process function for transcription"""
    try:
        msg_queue.put(('progress', task_index, "status_processing"))
        msg_queue.put(('log', ('log_start', Path(task_input_path).name)))
        
        # Determine actual output path
        output_dir = config.get('output_directory', '')
        if output_dir:
            output_name = Path(task_output_path).name
            actual_output_path = str(Path(output_dir) / output_name)
        else:
            actual_output_path = task_output_path
        
        # Backend loading logic - only faster-whisper is supported
        if config['backend'] == "faster-whisper":
            from features.transcription.engines.faster_whisper import FasterWhisperBackend
            backend = FasterWhisperBackend(
                model_name=config['model'],
                device=config['device'],
                compute_type=config['compute_type'],
                download_root=config.get('download_root') or None,
                cpu_threads=config.get('cpu_threads', 4),
                num_workers=config.get('num_workers', 1),
                local_files_only=config.get('local_files_only', False),
            )
        else:
            raise ValueError(f"Unsupported backend: {config['backend']}. Only 'faster-whisper' is supported.")
        
        # === STAGE: Model Loading ===
        msg_queue.put(('log', ('log_loading_model', config['model'], config['device'], config['compute_type'])))
        backend.load_model()
        msg_queue.put(('log', ('log_loading_model_complete',)))
        
        # Log detailed parameters using locale
        params_tuple = ('log_params', 
            config.get('beam_size', 5), 
            config.get('vad_enabled', True),
            config.get('language', 'auto'),
            config.get('task', 'transcribe'))
        msg_queue.put(('log', params_tuple))
        
        if config.get('initial_prompt'):
            prompt_preview = config['initial_prompt'][:30]
            msg_queue.put(('log', ('log_params_with_prompt', prompt_preview)))
        
        # Build VAD parameters
        vad_params = None
        if config.get('vad_enabled', True):
            vad_params = {
                "threshold": config.get('vad_threshold', 0.5),
                "min_speech_duration_ms": config.get('vad_min_speech_duration_ms', 250),
                "max_speech_duration_s": config.get('vad_max_speech_duration_s', 15.0),
                "min_silence_duration_ms": config.get('vad_min_silence_duration_ms', 300),
                "speech_pad_ms": config.get('vad_speech_pad_ms', 400),
            }
        
        # Parse temperature
        temperature = config.get('temperature', '0')
        try:
            if ',' in str(temperature):
                temperature = [float(t.strip()) for t in str(temperature).split(',')]
            else:
                temperature = float(temperature)
        except (ValueError, TypeError):
            temperature = 0.0
        
        if config['backend'] == "faster-whisper":
            # === STAGE: Transcription ===
            msg_queue.put(('log', ('log_transcribing_start', Path(task_input_path).name)))
            
            def on_progress(percent):
                msg_queue.put(('progress_percent', task_index, percent))
            
            segments = backend.transcribe(
                task_input_path,
                language=config.get('language', 'zh'),
                task=config.get('task', 'transcribe'),
                beam_size=config.get('beam_size', 5),
                best_of=config.get('best_of', 5),
                patience=config.get('patience', 1.0),
                length_penalty=config.get('length_penalty', 1.0),
                repetition_penalty=config.get('repetition_penalty', 1.0),
                no_repeat_ngram_size=config.get('no_repeat_ngram_size', 0),
                temperature=temperature,
                log_prob_threshold=config.get('log_prob_threshold', -1.0),
                no_speech_threshold=config.get('no_speech_threshold', 0.6),
                compression_ratio_threshold=config.get('compression_ratio_threshold', 2.4),
                condition_on_previous_text=config.get('condition_on_previous_text', True),
                prompt_reset_on_temperature=config.get('prompt_reset_on_temperature', 0.5),
                hallucination_silence_threshold=config.get('hallucination_silence_threshold', 0.0) or None,
                suppress_blank=config.get('suppress_blank', True),
                word_timestamps=config.get('word_timestamps', False),
                vad_filter=config.get('vad_enabled', True),
                vad_parameters=vad_params,
                initial_prompt=config.get('initial_prompt') or None,
                progress_callback=on_progress,
            )
        
        # Send 100% progress
        msg_queue.put(('progress_percent', task_index, 1.0))
        msg_queue.put(('log', ('log_transcribing_complete', len(segments))))
        
        # === STAGE: Save Output ===
        msg_queue.put(('log', ('log_saving_output', Path(actual_output_path).name)))
        from core.utils.srt_utils import save_srt, save_txt
        if actual_output_path.lower().endswith('.txt'):
            save_txt(segments, actual_output_path)
        else:
            save_srt(segments, actual_output_path)
        msg_queue.put(('log', ('log_saving_output_complete',)))
        
        # === LLM Correction (if enabled) ===
        if config.get('llm_enabled', False):
            try:
                msg_queue.put(('progress', task_index, "llm_correcting"))
                msg_queue.put(('log', ('log_starting_ai_correction',)))
                
                # Read the saved file
                with open(actual_output_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                
                # Get provider settings
                provider_name = config.get('llm_provider', 'gemini')
                language = config.get('language', 'zh')  # Use ASR language for prompt
                
                # Use factory to create provider (DIP compliant)
                from features.llm.factory import create_provider
                provider = create_provider(config)
                
                # Get advanced settings
                system_prompt = config.get('llm_system_prompt', None)
                llm_temp = config.get('llm_temperature', 0.3)
                enable_web_search = config.get('llm_web_search', False)
                
                # Get chunking settings (configurable token limit)
                max_tokens = config.get('llm_max_tokens', 65536)
                
                # Use chunked correction for large transcripts
                from features.llm.token_estimator import TokenEstimator
                from features.llm.chunker import TextChunker, ChunkConfig
                from features.llm.merger import ChunkMerger
                
                estimator = TokenEstimator()
                chunk_config = ChunkConfig(max_tokens=max_tokens)
                chunker = TextChunker(config=chunk_config, estimator=estimator)
                merger = ChunkMerger()
                
                # Check if chunking is needed
                if chunker.needs_chunking(original_content, system_prompt or ""):
                    chunks = chunker.chunk_srt(original_content, system_prompt or "")
                    msg_queue.put(('log', f"Large transcript: {len(chunks)} chunks"))
                    
                    corrected_contents = []
                    overlap_counts = []
                    
                    for i, chunk in enumerate(chunks):
                        msg_queue.put(('log', f"Chunk {i+1}/{len(chunks)} ({chunk.token_count} tokens)"))
                        corrected = provider.correct_text(
                            chunk.content,
                            language=language,
                            system_prompt=system_prompt,
                            temperature=llm_temp,
                            enable_web_search=enable_web_search
                        )
                        corrected_contents.append(corrected)
                        overlap_counts.append(chunk.overlap_count)
                    
                    msg_queue.put(('log', "Merging chunks..."))
                    corrected_content = merger.merge_results(corrected_contents, overlap_counts)
                else:
                    # Single chunk - direct call
                    corrected_content = provider.correct_text(
                        original_content, 
                        language=language,
                        system_prompt=system_prompt,
                        temperature=llm_temp,
                        enable_web_search=enable_web_search
                    )
                
                # Save corrected version
                corrected_path = actual_output_path.replace('.srt', '_corrected.srt').replace('.txt', '_corrected.txt')
                with open(corrected_path, 'w', encoding='utf-8') as f:
                    f.write(corrected_content)
                
                msg_queue.put(('log', f"AI correction saved to: {Path(corrected_path).name}"))
                
            except Exception as e:
                # LLM failure should not fail the whole task
                msg_queue.put(('log', f"AI correction failed: {str(e)} (original file preserved)"))
        
        backend.unload_model()
        
        msg_queue.put(('log', ('log_completed', len(segments))))
        msg_queue.put(('finished', task_index, True, "status_completed"))
        
    except Exception as e:
        error_msg = f"{str(e)}"
        msg_queue.put(('log', ('log_error', error_msg)))
        msg_queue.put(('finished', task_index, False, error_msg))


class TranscriptionWorker:
    """Multiprocessing worker for transcription with immediate stop support"""
    
    def __init__(self, task_index: int, task: Any, config: Dict[str, Any], callbacks: Dict[str, Callable]) -> None:
        self.task_index = task_index
        self.task = task
        self.config = config
        self.callbacks = callbacks
        self.msg_queue = multiprocessing.Queue()
        self.process = None
        self._monitor_thread = None
    
    def start(self) -> None:
        """Start the transcription process"""
        self.process = multiprocessing.Process(
            target=_transcribe_process,
            args=(self.task_index, self.task.input_path, self.task.output_path, 
                  self.config, self.msg_queue)
        )
        self.process.start()
        
        self._monitor_thread = threading.Thread(target=self._monitor_messages, daemon=True)
        self._monitor_thread.start()
    
    def _monitor_messages(self) -> None:
        """Monitor message queue and dispatch to callbacks"""
        import queue  # For Empty exception
        finished_received = False
        while True:
            try:
                msg = self.msg_queue.get(timeout=0.1)
                if msg[0] == 'progress':
                    self.callbacks['progress'](msg[1], msg[2])
                elif msg[0] == 'progress_percent':
                    self.callbacks['progress_percent'](msg[1], msg[2])
                elif msg[0] == 'log':
                    self.callbacks['log'](msg[1])
                elif msg[0] == 'finished':
                    self.callbacks['finished'](msg[1], msg[2], msg[3])
                    finished_received = True
                    break
            except queue.Empty:
                # Timeout occurred, check if process is still alive
                if self.process and not self.process.is_alive():
                    if not finished_received:
                        try:
                            while not self.msg_queue.empty():
                                msg = self.msg_queue.get_nowait()
                                if msg[0] == 'finished':
                                    self.callbacks['finished'](msg[1], msg[2], msg[3])
                                    finished_received = True
                                    break
                        except queue.Empty:
                            pass
                        
                        if not finished_received:
                            exit_code = self.process.exitcode
                            # Exit code -15 = SIGTERM (manual stop), exit code -9 = SIGKILL
                            # These are normal termination codes when user stops manually
                            if exit_code in (-15, -9):
                                # Manual stop handled in stop() method, don't duplicate
                                pass
                            elif exit_code != 0:
                                self.callbacks['log'](f"Process terminated unexpectedly (exit code: {exit_code})")
                                self.callbacks['finished'](self.task_index, False, "status_failed")
                            else:
                                self.callbacks['finished'](self.task_index, True, "status_completed")
                    break
            except Exception as e:
                # Log unexpected errors but continue monitoring
                self.callbacks['log'](f"Monitor error: {e}")
                continue
    
    def stop(self) -> None:
        """Immediately terminate the process"""
        if self.process and self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=1)
            if self.process.is_alive():
                self.process.kill()
            self.callbacks['log']("Process stopped manually")
            self.callbacks['finished'](self.task_index, False, "status_stopped")
