"""
MLX-Whisper Backend for macOS Apple Silicon
Placeholder for v2 implementation.

TODO v2:
- pip install mlx-whisper
- Implement load_model, transcribe, unload_model
- Add word_timestamps support
- Test on M1/M2/M3 Mac
"""

from typing import List, Optional
from features.transcription.engines.base import ASRBackend, TranscriptionSegment


class MLXWhisperBackend(ASRBackend):
    """
    Backend using MLX-Whisper for Apple Silicon acceleration.
    
    This is a placeholder for v2. On macOS with Apple Silicon,
    MLX provides 10x faster transcription than CPU-based Whisper.
    
    Usage (v2):
        backend = MLXWhisperBackend("mlx-community/whisper-large-v3-mlx")
        backend.load_model()
        segments = backend.transcribe("audio.mp3", language="zh")
    """
    
    def __init__(
        self, 
        model_name: str = "mlx-community/whisper-large-v3-mlx",
        **kwargs
    ):
        # MLX runs on Apple GPU (MPS) automatically
        super().__init__(model_name, device="mps", **kwargs)
        self._mlx_whisper = None
    
    def load_model(self) -> None:
        """
        Load MLX-Whisper model.
        
        TODO v2:
            import mlx_whisper
            self._mlx_whisper = mlx_whisper
            # MLX models are lazy-loaded on first transcribe
        """
        raise NotImplementedError("MLX backend will be available in v2")
    
    def transcribe(
        self, 
        audio_path: str, 
        language: Optional[str] = "zh",
        word_timestamps: bool = False,
        **kwargs
    ) -> List[TranscriptionSegment]:
        """
        Transcribe audio using MLX-Whisper.
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "zh", "en")
            word_timestamps: Enable word-level timestamps
            
        TODO v2:
            result = self._mlx_whisper.transcribe(
                audio_path,
                path_or_hf_repo=self.model_name,
                language=language,
                word_timestamps=word_timestamps
            )
            return [
                TranscriptionSegment(s["start"], s["end"], s["text"])
                for s in result.get("segments", [])
            ]
        """
        raise NotImplementedError("MLX backend will be available in v2")
    
    def unload_model(self) -> None:
        """
        Free MLX model from memory.
        
        TODO v2:
            import gc
            self._mlx_whisper = None
            gc.collect()
        """
        self._mlx_whisper = None

    @staticmethod
    def is_available() -> bool:
        """Check if MLX is available (macOS Apple Silicon only)"""
        import platform
        return platform.system() == "Darwin" and platform.machine() == "arm64"
