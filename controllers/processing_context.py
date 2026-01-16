"""
Processing Context
Unified processing state management (SSOT for processing status).
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from features.transcription.worker import TranscriptionWorker


class ProcessingMode(Enum):
    """Processing mode enumeration"""
    IDLE = "idle"              # No processing
    ASR = "asr"                # ASR transcription processing
    LLM_RETRY = "llm_retry"    # Manual LLM retry


@dataclass
class ProcessingContext:
    """Unified processing context (SSOT).
    
    Replaces the dual-tracking system:
    - TaskController.processing_index, current_worker, is_processing
    - VareApp._llm_retry_task_index, _llm_retry_cancelled
    
    All processing state is now centralized here.
    """
    mode: ProcessingMode = ProcessingMode.IDLE
    task_index: int = -1
    cancelled: bool = False
    worker: Optional["TranscriptionWorker"] = None
    
    @property
    def is_active(self) -> bool:
        """Whether processing is currently active."""
        return self.mode != ProcessingMode.IDLE
    
    @property
    def is_cancellable(self) -> bool:
        """Whether processing can be cancelled."""
        return self.is_active and not self.cancelled
    
    def start(self, mode: ProcessingMode, task_index: int, worker: Optional["TranscriptionWorker"] = None) -> None:
        """Start processing.
        
        Args:
            mode: The processing mode (ASR or LLM_RETRY)
            task_index: Index of the task being processed
            worker: Optional TranscriptionWorker instance (for ASR mode)
        """
        self.mode = mode
        self.task_index = task_index
        self.cancelled = False
        self.worker = worker
    
    def cancel(self) -> int:
        """Cancel processing.
        
        Returns:
            The task_index of the cancelled task (for status update).
        """
        self.cancelled = True
        if self.worker:
            self.worker.stop()
            self.worker = None
        return self.task_index
    
    def finish(self) -> None:
        """Finish processing and reset to idle state."""
        self.mode = ProcessingMode.IDLE
        self.task_index = -1
        self.cancelled = False
        self.worker = None
