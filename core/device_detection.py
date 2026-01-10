"""
Device Detection Utility (Optimized - No Torch Version)

Strategy:
1. Fast Check (Phase 1): Use nvidia-smi at startup for UI display (< 50ms).
2. Deep Check (Phase 2): Use ctranslate2 only when actual transcription starts.

This avoids blocking the main thread with CUDA initialization (~1-2s).
"""

import logging
import subprocess
import os
import platform
from typing import Optional, List, Tuple, Callable

logger = logging.getLogger(__name__)


# ==========================================
# Phase 1: Fast Detection (for UI startup display)
# ==========================================

def get_gpu_name_fast() -> Optional[str]:
    """
    Get GPU name quickly using nvidia-smi.
    Pros: No CUDA init, no blocking, no extra Python dependencies.
    """
    try:
        # Hide cmd window on Windows
        startupinfo = None
        if platform.system() == "Windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
            startupinfo=startupinfo
        )
        
        if result.returncode == 0 and result.stdout.strip():
            # Return the first GPU's name
            return result.stdout.strip().split('\n')[0]
            
    except FileNotFoundError:
        logger.debug("nvidia-smi not found (Driver not installed?)")
    except subprocess.TimeoutExpired:
        logger.debug("nvidia-smi timeout")
    except Exception as e:
        logger.debug(f"Fast GPU check failed: {e}")
        
    return None


# Global cache for device list detection
_cached_devices: Optional[List[Tuple[str, str]]] = None

def detect_available_devices_fast(force_refresh: bool = False) -> List[Tuple[str, str]]:
    """
    Return list of available devices [(device_id, display_name)].
    Used to populate UI dropdown menus.
    This function is very fast (< 50ms), won't block UI.
    Results are cached to avoid repeated nvidia-smi execution.
    """
    global _cached_devices
    
    if _cached_devices is not None and not force_refresh:
        return _cached_devices

    devices = []
    
    # 1. Try fast GPU detection
    gpu_name = get_gpu_name_fast()
    if gpu_name:
        devices.append(("cuda", f"GPU ({gpu_name})"))
        logger.info(f"CUDA available: {gpu_name}")
    
    # 2. CPU is always available
    devices.append(("cpu", "CPU"))
    
    _cached_devices = devices
    return devices


# ==========================================
# Phase 2: Precise Detection (before actual transcription)
# ==========================================

def get_optimal_compute_type(device: str) -> str:
    """
    Determine the optimal compute_type (int8, float16, etc.).
    Note: This triggers CUDA initialization (~1-2s), call only when starting transcription.
    """
    if device == "cpu":
        return "int8"  # CPU typically uses int8

    # If CUDA, query ctranslate2 for actually supported precision
    try:
        import ctranslate2
        
        # Fixed logic: check if returned set is non-empty
        supported_types = ctranslate2.get_supported_compute_types("cuda")
        
        # Log supported types for debugging
        logger.info(f"Supported CUDA compute types: {supported_types}")

        # Priority: float16 > int8_float16 > int8 > default
        if "float16" in supported_types:
            return "float16"
        elif "int8_float16" in supported_types:
            return "int8_float16"
        elif "int8" in supported_types:
            return "int8"
        else:
            return "default"  # Let ctranslate2 decide
            
    except ImportError:
        logger.error("ctranslate2 not installed.")
        return "int8"
    except Exception as e:
        logger.warning(f"Failed to detect compute type, falling back to float32: {e}")
        return "float32"


# ==========================================
# Backward Compatibility Wrappers
# ==========================================

def detect_available_devices() -> List[Tuple[str, str]]:
    """
    Backward compatible alias for detect_available_devices_fast().
    """
    return detect_available_devices_fast()


def get_default_device() -> str:
    """
    Get the recommended default device.
    Returns: Device string: "cuda" or "cpu"
    """
    devices = detect_available_devices_fast()
    if devices:
        return devices[0][0]  # First device is the best available
    return "cpu"


def is_cuda_available() -> bool:
    """Check if CUDA is available (fast check using nvidia-smi)."""
    # Force check only if not cached, otherwise use cache
    if _cached_devices:
        return any(d[0] == "cuda" for d in _cached_devices)
    return get_gpu_name_fast() is not None


def get_device_info() -> dict:
    """
    Get detailed device information (fast check).
    """
    info = {
        "cuda_available": False,
        "cuda_device_name": None,
        "recommended_device": "cpu"
    }
    
    # Use cached detection if available
    cuda_found = False
    cuda_name = None
    
    if _cached_devices:
        for dev_id, dev_name in _cached_devices:
            if dev_id == "cuda":
                cuda_found = True
                cuda_name = dev_name.replace("GPU (", "").replace(")", "")
                break
    else:
        # Fallback to direct check if cache empty
        cuda_name = get_gpu_name_fast()
        cuda_found = cuda_name is not None
    
    if cuda_found:
        info["cuda_available"] = True
        info["cuda_device_name"] = cuda_name
        info["recommended_device"] = "cuda"
    
    return info


# ==========================================
# Phase 3: Background Detection for UI
# ==========================================

import threading

def get_supported_compute_types(device: str = "cuda") -> List[str]:
    """
    Get supported compute types for a specific device.
    This safely handles the import and CUDA initialization.
    """
    if device == "cpu":
        # CPU typically supports int8, int8_float16, int16, float16, float32
        # But for stability, we usually stick to int8 or float32
        try:
            import ctranslate2
            return list(ctranslate2.get_supported_compute_types("cpu"))
        except Exception:
            return ["int8", "float32"]

    try:
        import ctranslate2
        # This might block for 1-2 seconds if CUDA not init
        types = ctranslate2.get_supported_compute_types("cuda")
        return list(types)
    except Exception as e:
        logger.warning(f"Failed to get supported types for {device}: {e}")
        return ["float16", "int8_float16", "float32"] # Default fallback

class ComputeTypeCache:
    """
    Singleton cache for compute type detection results.
    Detects both CPU and GPU types ONCE in background, then provides instant access.
    """
    _cache: dict = {
        "cpu": None,  # Will be filled with list like ["int8", "float32"]
        "cuda": None, # Will be filled with list like ["float16", "int8_float16"]
    }
    _detection_complete = threading.Event()
    _listeners = []  # Callbacks to notify when detection is complete
    _is_running = False # Guard to prevent multiple threads

    @classmethod
    def get_cached_types(cls, device: str) -> List[str]:
        """
        Get cached compute types for a device.
        Returns default fallback if not yet detected.
        """
        if cls._cache.get(device):
            return cls._cache[device]
        
        # Fallback if not cached yet
        if device == "cpu":
            return ["int8", "float32"]
        else:
            return ["float16", "int8_float16", "float32"]

    @classmethod
    def is_ready(cls) -> bool:
        """Check if background detection has completed."""
        return cls._detection_complete.is_set()

    @classmethod
    def add_listener(cls, callback: Callable[[], None]) -> None:
        """Add a callback to be notified when detection completes."""
        if cls.is_ready():
            # Already done, call immediately
            callback()
        else:
            cls._listeners.append(callback)

    @classmethod
    def start_detection(cls) -> None:
        """
        Start background detection for BOTH CPU and GPU.
        Should be called once at app startup.
        """
        if cls.is_ready() or cls._is_running:
            return
            
        cls._is_running = True

        def _detect_all():
            try:
                # Detect CPU types
                cls._cache["cpu"] = get_supported_compute_types("cpu")
                logger.debug(f"CPU compute types cached: {cls._cache['cpu']}")
                
                # Detect GPU types (this is the slow one - ~1-2s)
                # Use detect_available_devices_fast to check CUDA first
                detect_available_devices_fast() # Ensure device list is cached
                
                if is_cuda_available():
                    cls._cache["cuda"] = get_supported_compute_types("cuda")
                    logger.debug(f"CUDA compute types cached: {cls._cache['cuda']}")
                else:
                    cls._cache["cuda"] = []  # No GPU available
                    logger.debug("No GPU detected, CUDA types set to empty.")
                
                # Sort for better UI: float16 first if present
                for device in ["cpu", "cuda"]:
                    if cls._cache[device] and "float16" in cls._cache[device]:
                        cls._cache[device].remove("float16")
                        cls._cache[device].insert(0, "float16")
                
                # Mark as complete and notify listeners
                cls._detection_complete.set()
                for listener in cls._listeners:
                    try:
                        listener()
                    except Exception as e:
                        logger.error(f"Listener callback failed: {e}")
                cls._listeners.clear()
                
            except Exception as e:
                logger.error(f"Background compute type detection failed: {e}")
                cls._detection_complete.set()  # Still mark as complete
            finally:
                cls._is_running = False

        threading.Thread(target=_detect_all, daemon=True).start()


# Legacy alias for backward compatibility
class ComputeTypeDetector:
    """Legacy helper - now wraps ComputeTypeCache"""
    
    @staticmethod
    def detect_async(callback: Callable[[List[str]], None], device: str = "cuda") -> None:
        """Legacy method: Returns cached result or triggers detection."""
        if ComputeTypeCache.is_ready():
            callback(ComputeTypeCache.get_cached_types(device))
        else:
            # Add listener to call back when detection completes
            def on_ready():
                callback(ComputeTypeCache.get_cached_types(device))
            ComputeTypeCache.add_listener(on_ready)


# ==========================================
# Main Test
# ==========================================

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    
    print("--- 1. App Startup Phase (UI Display) - Should complete instantly ---")
    start = time.perf_counter()
    devices = detect_available_devices_fast()
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Available devices: {devices}")
    print(f"Elapsed: {elapsed:.1f}ms")
    
    selected_device = devices[0][0]  # Assume user selected first one
    print(f"User selected: {selected_device}")

    print("\n--- 2. User Starts Transcription (Task Start) - Delay expected here ---")
    print("Initializing model configuration...") 
    start = time.perf_counter()
    compute_type = get_optimal_compute_type(selected_device)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Final compute type: {compute_type}")
    print(f"Elapsed: {elapsed:.1f}ms")

