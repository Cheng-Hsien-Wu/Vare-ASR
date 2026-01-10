"""
ASR Backend Abstract Interface
Defines the common interface for all ASR model backends
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from dataclasses import dataclass


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment with timing"""
    start: float  # seconds
    end: float    # seconds
    text: str
    
    def duration(self) -> float:
        return self.end - self.start


class ASRBackend(ABC):
    """Abstract base class for ASR backends"""
    
    def __init__(self, model_name: str, device: str = "cuda", **kwargs):
        """
        Initialize the ASR backend
        
        Args:
            model_name: Model identifier (HuggingFace repo or local path)
            device: "cuda" or "cpu"
            **kwargs: Backend-specific parameters
        """
        self.model_name = model_name
        self.device = device
        self.kwargs = kwargs
        self.model = None
        
    @abstractmethod
    def load_model(self) -> None:
        """Load the model into memory"""
        pass
    
    @abstractmethod
    def transcribe(
        self, 
        audio_path: str, 
        language: Optional[str] = None,
        **kwargs
    ) -> List[TranscriptionSegment]:
        """
        Transcribe audio file to text with timestamps
        
        Args:
            audio_path: Path to audio/video file
            language: Language code (e.g., "zh", "en", None for auto-detect)
            **kwargs: Backend-specific transcription parameters
            
        Returns:
            List of TranscriptionSegment objects
        """
        pass
    
    @abstractmethod
    def unload_model(self) -> None:
        """Free model from memory"""
        pass
    
    def is_loaded(self) -> bool:
        """Check if model is loaded"""
        return self.model is not None
    
    def get_info(self) -> Dict[str, Any]:
        """Get backend information"""
        return {
            "backend_type": self.__class__.__name__,
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.is_loaded()
        }