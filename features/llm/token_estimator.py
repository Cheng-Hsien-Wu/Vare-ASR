"""
Token Estimator
Estimates token count using tiktoken for LLM context management.
Single Responsibility: Token counting only.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default encoding for modern models (GPT-4, etc.)
DEFAULT_ENCODING = "cl100k_base"


class TokenEstimator:
    """Estimates token count using tiktoken (GPT tokenizer).
    
    While tiktoken is designed for GPT models, it provides a reasonable
    approximation for other models as well, and is more accurate than
    simple character-based estimation.
    """
    
    _instance: Optional["TokenEstimator"] = None
    _encoding = None
    
    def __new__(cls, encoding_name: str = DEFAULT_ENCODING):
        """Singleton pattern to avoid reloading encoding multiple times."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_encoding(encoding_name)
        return cls._instance
    
    def _init_encoding(self, encoding_name: str) -> None:
        """Initialize tiktoken encoding."""
        try:
            import tiktoken
            self._encoding = tiktoken.get_encoding(encoding_name)
            logger.info(f"TokenEstimator initialized with encoding: {encoding_name}")
        except ImportError:
            logger.warning("tiktoken not installed, falling back to character-based estimation")
            self._encoding = None
        except Exception as e:
            logger.warning(f"Failed to load tiktoken encoding: {e}, using fallback")
            self._encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
            
        if self._encoding is not None:
            try:
                return len(self._encoding.encode(text))
            except Exception as e:
                logger.debug(f"Token counting failed: {e}, using fallback")
        
        # Fallback: rough estimate (1 token ≈ 4 chars for English, 1.5 for Chinese)
        # This is a conservative estimate
        return self._fallback_estimate(text)
    
    def _fallback_estimate(self, text: str) -> int:
        """Fallback token estimation based on character analysis."""
        # Count Chinese characters (CJK range)
        cjk_count = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        non_cjk_count = len(text) - cjk_count
        
        # Chinese: ~1.5 chars per token, English: ~4 chars per token
        estimated = (cjk_count / 1.5) + (non_cjk_count / 4)
        return int(estimated) + 1  # Round up for safety
    
    def estimate_with_overhead(self, text: str, overhead_percentage: float = 0.1) -> int:
        """Count tokens with additional safety overhead.
        
        Args:
            text: Text to count tokens for
            overhead_percentage: Safety margin (default 10%)
            
        Returns:
            Estimated token count with overhead
        """
        base_count = self.count_tokens(text)
        return int(base_count * (1 + overhead_percentage))
