"""
Transcription Models
Data classes for transcription tasks.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptionTask:
    """Data class for a transcription task"""
    input_path: str
    output_path: str
    status: str = "status_waiting"
    progress: float = 0.0
    error_msg: str = ""

    @property
    def output_dir(self) -> str:
        """Get the directory containing the output file"""
        import os
        return os.path.dirname(self.output_path)
    
    @property
    def output_exists(self) -> bool:
        """Check if output file exists (SSOT for file existence check).
        
        Checks both the task's output path and the configured output directory.
        """
        from core.settings import UserSettings
        
        task_output = Path(self.output_path)
        
        # Check original path
        if task_output.exists():
            return True
        
        # Check in configured output directory
        output_dir = UserSettings.get("output_directory", "")
        if output_dir:
            alt_path = Path(output_dir) / task_output.name
            if alt_path.exists():
                return True
        
        return False
    
    @property
    def can_show_actions(self) -> bool:
        """Whether to show action buttons (Open Folder, LLM Retry).
        
        True when: output file exists AND task is not actively processing.
        """
        # These statuses indicate active processing - don't show buttons
        active_statuses = ("status_waiting", "status_processing", "llm_correcting")
        return self.output_exists and self.status not in active_statuses

