"""
TaskController - Handles task management and processing business logic.
Separates task operations from UI code using EventBus pattern.
"""

import flet as ft
from pathlib import Path
from typing import List, Optional, Callable, Dict, Any

from core.events import EventBus, Events
from core.notifications import NotificationManager
from core.settings import UserSettings
from core.i18n.localization import DesktopLocale
from core import secure_storage
from core.constants.defaults import DEFAULT_LLM_MODEL
from features.transcription.worker import TranscriptionWorker
from features.transcription.models import TranscriptionTask
from core.utils.text_utils import sanitize_filename


class TaskController:
    """Controller for task management and processing operations.
    
    Uses EventBus to notify UI of state changes:
    - PROCESSING_STARTED: Processing began
    - PROCESSING_STOPPED: Processing was stopped
    - PROCESSING_FINISHED: All tasks complete
    - TASK_STATUS_CHANGED: Individual task status changed
    
    UI should subscribe to these events and update accordingly.
    """
    
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.mp4', '.mp3', '.wav', '.m4a', '.mkv', '.mov', '.flac', '.webm', '.ogg'}
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.tasks: List[TranscriptionTask] = []
        self.current_worker: Optional[TranscriptionWorker] = None
        self.processing_index = 0
        self.is_processing = False
        
        # Log callback
        self._log: Optional[Callable[[str], None]] = None
    
    def set_config_getter(self, getter: Callable[[], Dict[str, Any]]) -> None:
        """Set callback to get current config from UI controls."""
        self._get_config = getter
    
    def set_log_callback(self, log_fn: Callable[[str], None]) -> None:
        """Set log callback."""
        self._log = log_fn
    
    def _do_log(self, msg: str | tuple) -> None:
        """Log a message if callback is set.
        
        Supports both plain strings and tuples for localization:
        - Plain string: logged as-is
        - Tuple: (locale_key, *args) - translated using DesktopLocale
        """
        if not self._log:
            return
            
        if isinstance(msg, tuple):
            locale_key = msg[0]
            args = msg[1:] if len(msg) > 1 else ()
            translated = DesktopLocale.get(locale_key)
            # Format with positional args if present
            if args:
                try:
                    # Try Python format (for {0}, {1} style)
                    translated = translated.format(*args)
                except (IndexError, KeyError):
                    # Fallback to simple concatenation
                    translated = f"{translated}: {', '.join(str(a) for a in args)}"
            self._log(translated)
        else:
            self._log(str(msg))
    
    # ==========================================
    # Task Management
    # ==========================================
    
    def add_files(self, file_paths: List[str]) -> int:
        """Add files to task list. Returns number of files added."""
        # Unified Pipeline: Always default to .srt (canonical format)
        # Sidecar .txt will be generated automatically
        output_format = "srt"
        added = 0
        
        for file_path in file_paths:
            path = Path(file_path)
            if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                # Force replace suffix (video.mp4 -> video.srt)
                # This prevents "double suffix" or "format name" artifacts from stale settings
                output_path = path.with_suffix(f".{output_format}")
                task = TranscriptionTask(
                    input_path=str(path),
                    output_path=str(output_path),
                    status="status_waiting"
                )
                self.tasks.append(task)
                added += 1
        
        if added > 0:
            EventBus.emit(Events.TASKS_CHANGED, self.tasks)
            NotificationManager.log(f"{added} {DesktopLocale.get('files_added')}")
        
        return added
    
    def add_folder(self, folder_path: str) -> int:
        """Add all supported files from a folder."""
        folder = Path(folder_path)
        
        files_to_add = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files_to_add.extend(folder.glob(f"*{ext}"))
            files_to_add.extend(folder.glob(f"*{ext.upper()}"))
        
        return self.add_files([str(f) for f in files_to_add])
    
    def remove_task(self, index: int) -> bool:
        """Remove a task by index."""
        if 0 <= index < len(self.tasks):
            removed = self.tasks.pop(index)
            EventBus.emit(Events.TASK_REMOVED, {"index": index, "task": removed})
            EventBus.emit(Events.TASKS_CHANGED, self.tasks)
            return True
        return False
    
    def clear_tasks(self) -> None:
        """Clear all tasks"""
        self.tasks.clear()
        EventBus.emit(Events.TASKS_CHANGED, self.tasks)
    
    def get_tasks(self) -> List[TranscriptionTask]:
        """Get current task list"""
        return self.tasks
    
    def get_task_count(self) -> int:
        """Get number of tasks"""
        return len(self.tasks)
    
    def update_task_status(self, index: int, status: str, progress: int | None = None, error_msg: str | None = None) -> None:
        """Update task status"""
        if 0 <= index < len(self.tasks):
            task = self.tasks[index]
            task.status = status
            if progress is not None:
                task.progress = progress
            if error_msg is not None:
                task.error_msg = error_msg
            EventBus.emit(Events.TASK_STATUS_CHANGED, {"index": index, "task": task})

    def update_output_filename(self, index: int, new_filename: str) -> bool:
        """Update task output filename with validation"""
        if not (0 <= index < len(self.tasks)):
            return False
            
        # Standardized sanitization (Round 8 Refactor)
        safe_name = sanitize_filename(new_filename)
        
        if not safe_name:
            return False
            
        # Ensure extension logic matches user preference
        # Ensure extension matches Unified Pipeline standard (.srt)
        expected_ext = ".srt"
        if not safe_name.lower().endswith(expected_ext):
            safe_name += expected_ext
            
        old_path = Path(self.tasks[index].output_path)
        new_path = old_path.parent / safe_name
        
        self.tasks[index].output_path = str(new_path)
        return True
    
    # ==========================================
    # Processing Control
    # ==========================================
    
    def can_start_processing(self) -> bool:
        """Check if processing can be started"""
        return len(self.tasks) > 0 and not self.is_processing
    
    # ==========================================
    # Configuration (Decoupled from App)
    # ==========================================
    
    def _get_config_from_settings(self) -> Dict[str, Any]:
        """Construct config dictionary directly from UserSettings."""
        # This replaces the old _get_processing_config callback from app.py
        
        # Get model (handle custom check logic if needed, but UserSettings stores final string)
        model = UserSettings.get("asr_model", "SoybeanMilk/faster-whisper-Breeze-ASR-25")
        
        config = {
            'backend': "faster-whisper", # Fixed for now or add setting
            'model': model,
            'language': UserSettings.get("asr_language", "zh"),
            'device': UserSettings.get("asr_device", "cuda"),
            'compute_type': UserSettings.get("compute_type", "float16"),
            'download_root': UserSettings.get("model_cache_directory", ""),
            'output_directory': UserSettings.get("output_directory", ""),
            
            # Model loading
            'cpu_threads': UserSettings.get("cpu_threads", 4),
            'num_workers': UserSettings.get("num_workers", 1),
            'local_files_only': UserSettings.get("local_files_only", False),
            
            # Basic transcription
            'task': UserSettings.get("task", "transcribe"),
            'initial_prompt': UserSettings.get("initial_prompt", ""),
            'word_timestamps': UserSettings.get("word_timestamps", False),
            
            # Beam search (Defaults for now until Advanced is decoupled)
            'beam_size': UserSettings.get("beam_size", 5),
            'best_of': UserSettings.get("best_of", 5),
            'patience': UserSettings.get("patience", 1.0),
            'length_penalty': UserSettings.get("length_penalty", 1.0),
            'temperature': UserSettings.get("temperature", "0"),
            
            # Hallucination control
            'repetition_penalty': UserSettings.get("repetition_penalty", 1.0),
            'no_repeat_ngram_size': UserSettings.get("no_repeat_ngram_size", 0),
            'log_prob_threshold': UserSettings.get("log_prob_threshold", -1.0),
            'no_speech_threshold': UserSettings.get("no_speech_threshold", 0.6),
            'compression_ratio_threshold': UserSettings.get("compression_ratio_threshold", 2.4),
            'condition_on_previous_text': UserSettings.get("condition_on_previous_text", True),
            'prompt_reset_on_temperature': UserSettings.get("prompt_reset_on_temperature", 0.5),
            'suppress_blank': UserSettings.get("suppress_blank", True),
            'hallucination_silence_threshold': UserSettings.get("hallucination_silence_threshold", 0.0),
            
            # VAD settings
            'vad_enabled': UserSettings.get("vad_enabled", True),
            'vad_threshold': UserSettings.get("vad_threshold", 0.5),
            'vad_min_speech_duration_ms': UserSettings.get("vad_min_speech_duration_ms", 250),
            'vad_max_speech_duration_s': UserSettings.get("vad_max_speech_duration_s", 15.0),
            'vad_min_silence_duration_ms': UserSettings.get("vad_min_silence_duration_ms", 300),
            'vad_speech_pad_ms': UserSettings.get("vad_speech_pad_ms", 100),
            
            # LLM Correction settings
            'llm_enabled': UserSettings.get("llm_enabled", False),
            'llm_provider': UserSettings.get("llm_provider", "gemini"),
            'llm_api_key': secure_storage.get_api_key(UserSettings.get("llm_provider", "gemini")),
            'llm_model': UserSettings.get("llm_model", DEFAULT_LLM_MODEL),
            'llm_base_url': UserSettings.get("llm_base_url", "http://localhost:11434"),
            'llm_system_prompt': UserSettings.get("llm_system_prompt", ""),
            'llm_temperature': float(UserSettings.get("llm_temperature", 0.3)),
            'llm_web_search': UserSettings.get("llm_web_search", False),
        }
        return config

    def start_processing(self) -> bool:
        """Start processing tasks. Returns True if processing started."""
        if not self.can_start_processing():
            return False
        
        self.is_processing = True
        self.processing_index = 0
        
        # Emit event for UI to update
        EventBus.emit(Events.PROCESSING_STARTED)
        
        self._do_log(DesktopLocale.get("processing_started"))
        
        # Start processing first task
        self._process_next()
        return True
    
    def stop_processing(self) -> None:
        """Stop processing"""
        self.is_processing = False
        
        if self.current_worker:
            self.current_worker.stop()
            self.current_worker = None
        
        # Update current task status if processing
        if self.processing_index < len(self.tasks):
            task = self.tasks[self.processing_index]
            if task.status == "status_processing":
                task.status = "status_stopped"
        
        # Emit event for UI to update
        EventBus.emit(Events.PROCESSING_STOPPED)
    
    def _process_next(self) -> None:
        """Process next task in queue"""
        if self.processing_index >= len(self.tasks) or not self.is_processing:
            self._on_all_finished()
            return
        
        task = self.tasks[self.processing_index]
        
        # Reset progress and status for this task
        task.progress = 0
        task.status = "status_processing"
        
        # Get config DIRECTLY from Settings (No callback)
        config = self._get_config_from_settings()
        
        # Debug log
        self._do_log(DesktopLocale.get("log_config_values").format(config.get('model', 'N/A'), config.get('language', 'N/A')))
        if config.get('initial_prompt'):
            prompt = config['initial_prompt']
            self._do_log(DesktopLocale.get("log_initial_prompt").format(prompt[:50]))
        
        callbacks = {
            'progress': self._on_worker_progress,
            'progress_percent': self._on_worker_progress_percent,
            'finished': self._on_worker_finished,
            'log': self._do_log,
        }
        
        self.current_worker = TranscriptionWorker(self.processing_index, task, config, callbacks)
        self.current_worker.start()
    
    def _on_worker_progress(self, idx: int, status: str) -> None:
        """Handle worker progress update (from background thread)"""
        if idx < len(self.tasks):
            self.tasks[idx].status = status
            EventBus.emit(Events.TASK_STATUS_CHANGED, {"index": idx, "task": self.tasks[idx]})
    
    def _on_worker_progress_percent(self, idx: int, percent: int) -> None:
        """Handle worker progress percent update"""
        if idx < len(self.tasks):
            self.tasks[idx].progress = percent
            EventBus.emit(Events.TASK_STATUS_CHANGED, {"index": idx, "task": self.tasks[idx]})
    
    def _on_worker_finished(self, idx: int, success: bool, status: str) -> None:
        """Handle worker task finished"""
        if idx < len(self.tasks):
            self.tasks[idx].status = status
            self.tasks[idx].progress = 1.0 if success else self.tasks[idx].progress
            EventBus.emit(Events.TASK_STATUS_CHANGED, {"index": idx, "task": self.tasks[idx]})
        
        self.current_worker = None
        
        # Continue to next task
        if self.is_processing:
            self.processing_index += 1
            self._process_next()
    
    def _on_all_finished(self) -> None:
        """Handle all tasks finished"""
        self.is_processing = False
        self.current_worker = None
        
        # Count results
        completed = sum(1 for t in self.tasks if t.status == "status_completed")
        failed = sum(1 for t in self.tasks if t.status == "status_failed")
        
        if completed > 0:
            summary = DesktopLocale.get("log_result_summary").format(
                DesktopLocale.get('processing_finished'),
                completed,
                DesktopLocale.get('processing_completed'),
                failed,
                DesktopLocale.get('processing_failed')
            )
            self._do_log(summary)
        
        # Emit event for UI to update
        EventBus.emit(Events.PROCESSING_FINISHED, {"completed": completed, "failed": failed})
