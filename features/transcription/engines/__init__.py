"""
ASR Engine Backends

Available backends:
- FasterWhisperBackend: Windows/Linux with CUDA support
- MLXWhisperBackend: macOS Apple Silicon (v2 placeholder)
"""

from .base import ASRBackend, TranscriptionSegment
from .faster_whisper import FasterWhisperBackend

# MLX backend (macOS only, v2 placeholder)
try:
    from .mlx_whisper import MLXWhisperBackend
except ImportError:
    MLXWhisperBackend = None

__all__ = [
    "ASRBackend",
    "TranscriptionSegment", 
    "FasterWhisperBackend",
    "MLXWhisperBackend",
]
