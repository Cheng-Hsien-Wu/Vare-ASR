"""
Vare - Application Entry Point
"""

import multiprocessing
import flet as ft
import logging
import warnings
import sys
import os
from app import VareApp

# Suppress Flet's internal asyncio shutdown warnings (known Flet issue)
# These occur because Flet's socket server doesn't gracefully handle window close
warnings.filterwarnings("ignore", message="coroutine .* was never awaited", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="Enable tracemalloc", category=RuntimeWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Suppress asyncio "Task was destroyed" errors (Flet internal cleanup issue)
class AsyncioFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        # Filter out Flet's internal task destruction warnings on shutdown
        if record.levelno == logging.ERROR:
            if "Task was destroyed but it is pending" in msg:
                return False
            if "Exception ignored" in msg:
                return False
        return True

logging.getLogger("asyncio").addFilter(AsyncioFilter())

# Suppress unhandled exceptions during Flet shutdown (AttributeError from socket cleanup)
_original_excepthook = sys.excepthook
def _shutdown_excepthook(exc_type, exc_value, exc_tb) -> None:
    # Suppress AttributeError during Flet cleanup (NoneType has no attribute 'create_future')
    if exc_type is AttributeError and "create_future" in str(exc_value):
        return
    # Suppress RuntimeError for coroutine GeneratorExit
    if exc_type is RuntimeError and "GeneratorExit" in str(exc_value):
        return
    _original_excepthook(exc_type, exc_value, exc_tb)

sys.excepthook = _shutdown_excepthook

# Filter stderr to suppress Flet internal shutdown messages
# These are printed directly by Python, not through logging
class StderrFilter:
    """
    Wrapper for stderr that filters out Flet/Asyncio shutdown noise.
    
    Flet's architecture involves python-to-go communication via sockets.
    On Windows, aggressive window closing can tear down loops before 
    coroutines finish, causing "Task was destroyed but it is pending" 
    and "Event loop is closed" errors.
    
    These are cosmetic and inevitable in the current Flet architecture.
    This filter prevents them from scaring the user.
    """

    SUPPRESS_PATTERNS = [
        # Flet/Asyncio Shutdown Noise
        "Exception ignored",
        "Task was destroyed but it is pending",
        "coroutine ignored GeneratorExit",
        "create_future",
        "RuntimeWarning:",
        "FletSocketServer",
        "IocpProactor",
        "async with self.__connection_lock",
        "handle_connection",
        "_OverlappedFuture",
        "Traceback (most recent call last)",
        f"asyncio{os.sep}locks.py",
        f"asyncio{os.sep}tasks.py",
        f"asyncio{os.sep}windows_events.py",
        f"asyncio{os.sep}base_events.py",
        f"asyncio{os.sep}streams.py",
        f"flet{os.sep}messaging",
        f"flet{os.sep}app.py",
        "flet_socket_server",
        "was never awaited",
        
        # Specific path filters
        f"site-packages{os.sep}flet",  # Any flet package path
        f"site-packages{os.sep}asyncio",  # Any asyncio package path
        
        # Traceback formatting lines
        "    ^",  # Error pointer lines
        "  ^",   # Shorter pointer lines
        "^^^^^", # Multiple caret chars
        "gather.<locals>",
        "cb=[",
        "run_async",
        "serve_forever",
        "__receive_loop",
        "__send_loop",
        "accept_coro",
        "task:",  # Task info lines
        "coro=<",  # Coroutine info
        "wait_for=<",  # Wait info
        "^^",  # Simplified - any 2+ consecutive carets
        
        # NOTE: Removed generic "AttributeError" and "RuntimeError" (Round 9)
        # to prevent masking legitimate app crashes.
    ]

    
    def __init__(self, original) -> None:
        self._original = original
        self._suppress_next_lines = 0  # Counter to suppress traceback continuation
    
    def write(self, text: str) -> int:
        # Check if we should suppress this line
        should_suppress = any(pattern in text for pattern in self.SUPPRESS_PATTERNS)
        
        # Extra check: suppress lines that are mostly whitespace and carets (error pointers)
        if not should_suppress:
            stripped = text.strip()
            if stripped and all(c == '^' for c in stripped):
                should_suppress = True
        
        # Also suppress continuation lines of tracebacks
        if should_suppress:
            # Count newlines to know how many following lines might be part of traceback
            self._suppress_next_lines = text.count('\n') + 5
        elif self._suppress_next_lines > 0:
            self._suppress_next_lines -= text.count('\n') if '\n' in text else 1
            should_suppress = True
        
        if not should_suppress:
            try:
                if self._original:
                    self._original.write(text)
            except UnicodeEncodeError:
                # Handle encoding errors (e.g. CP932 on Windows) by replacing chars
                try:
                    encoding = getattr(self._original, "encoding", "utf-8") or "utf-8"
                    safe_text = text.encode(encoding, errors="replace").decode(encoding)
                    self._original.write(safe_text)
                except Exception:
                    pass  # If even safe write fails, suppress
            except Exception:
                pass  # Suppress other write errors to prevent crash
        return len(text)
    
    def flush(self) -> None:
        self._original.flush()
    
    def fileno(self) -> int:
        return self._original.fileno()
    
    def isatty(self) -> bool:
        return self._original.isatty()
    
    @property
    def encoding(self) -> str:
        return self._original.encoding
    
    @property
    def errors(self) -> str | None:
        return getattr(self._original, 'errors', None)
    
    def __getattr__(self, name: str):
        return getattr(self._original, name)

# Apply stderr filter
sys.stderr = StderrFilter(sys.__stderr__)


async def main(page: ft.Page) -> None:
    app = VareApp(page)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # Required for Windows
    ft.run(main)