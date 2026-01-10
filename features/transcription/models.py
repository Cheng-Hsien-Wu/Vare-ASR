"""
Transcription Models
Data classes for transcription tasks.
"""

from dataclasses import dataclass


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
