import platform
import os
import subprocess
import sys
import logging
import time
from typing import List, Optional

logger = logging.getLogger(__name__)


def is_windows() -> bool:
    """Check if the current platform is Windows."""
    return platform.system() == "Windows"


def is_admin() -> bool:
    """
    Check if the current process is running with administrator privileges.
    Only meaningful on Windows; returns True on other platforms.
    """
    if not is_windows():
        return True  # Non-Windows platforms don't need elevation for symlinks
    
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin(close_callback=None) -> bool:
    """
    Restart the application with administrator privileges on Windows.
    
    Args:
        close_callback: Optional function to call to close the current window
        
    Returns:
        True if restart was initiated, False if failed
    """
    if not is_windows():
        return False
    
    try:
        import ctypes
        
        # Get the current Python executable and script
        python_exe = sys.executable
        
        # Check if running as frozen application (e.g. PyInstaller)
        is_frozen = getattr(sys, 'frozen', False)
        
        if is_frozen:
            # In frozen mode, the executable IS the script.
            # We execute it directly, passing validation arguments if needed.
            # Use sys.argv[1:] to pass original arguments, skipping the executable name itself.
            cmd_file = python_exe
            cmd_params = ' '.join(f'"{arg}"' for arg in sys.argv[1:])
        else:
            # In script mode, we execute python.exe with the script as first argument
            script = os.path.abspath(sys.argv[0])
            cmd_file = python_exe
            cmd_params = f'"{script}"'
        
        # ShellExecuteW with "runas" verb to request elevation
        # Returns value > 32 on success
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operation - run as admin
            cmd_file,     # file
            cmd_params,  # parameters
            None,           # directory
            1               # show command (SW_SHOWNORMAL)
        )
        
        if result > 32:
            # Successfully initiated, close current instance
            if close_callback:
                close_callback()
            return True
        else:
            logger.error(f"ShellExecuteW failed with code: {result}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to restart as admin: {e}")
        return False


def open_file_or_folder(path: str) -> bool:
    """
    Open a file or folder using the default system application.
    Cross-platform implementation for Windows, macOS, and Linux.
    
    Args:
        path: Path to file or folder
        
    Returns:
        True if successful, False otherwise
    """
    try:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            logger.error(f"Cannot open path: {path} does not exist")
            return False

        system = platform.system()
        
        if system == "Windows":
            # SW_SHOWNORMAL = 1
            os.startfile(path, operation="open", show_cmd=1)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            # Linux/Unix
            subprocess.Popen(["xdg-open", path])
            
        return True
    except Exception as e:
        logger.error(f"Failed to open path {path}: {e}")
        return False


# ---------------- Win32 API Helpers (Internal) ----------------

def _win32_get_foreground_window() -> int:
    try:
        import ctypes
        return int(ctypes.windll.user32.GetForegroundWindow())
    except Exception:
        return 0


def _win32_list_explorer_hwnds() -> List[int]:
    """
    Helper to list all visible File Explorer windows.
    Returns a list of window handles (HWNDs).
    """
    if not is_windows():
        return []
        
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

        def _get_class_name(hwnd: int) -> str:
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            return buf.value

        def _enum_top_windows() -> List[int]:
            hwnds: List[int] = []
            def _cb(hwnd, lparam):
                if user32.IsWindowVisible(hwnd):
                    hwnds.append(int(hwnd))
                return True
            
            proc = EnumWindowsProc(_cb)
            user32.EnumWindows(proc, 0)
            return hwnds

        def _list_explorer_hwnds() -> List[int]:
            """List all visible File Explorer windows (CabinetWClass/ExploreWClass)"""
            result = []
            for hwnd in _enum_top_windows():
                cls = _get_class_name(hwnd)
                if cls in ("CabinetWClass", "ExploreWClass"):
                    result.append(hwnd)
            return result
            
        return _list_explorer_hwnds()
        
    except Exception:
        return []

def _win32_bring_explorer_front_and_app_second(hwnd_app: int, before_hwnds: set, timeout_sec: float = 1.0) -> bool:
    """
    Apply Z-Order strategy (Sandwich Strategy):
    1. Bring new Explorer window to front (Non-Topmost).
    2. Bring App to front.
    3. Insert App behind Explorer.
    
    Result: Explorer -> App -> Others (Steam, etc.)
    """
    if not is_windows():
        return False
        
    try:
        import ctypes
        
        user32 = ctypes.windll.user32
        
        # Win32 Constants
        HWND_TOP = 0
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2

        SWP_NOMOVE = 0x0002
        SWP_NOSIZE = 0x0001
        SWP_NOACTIVATE = 0x0010

        def _set_window_pos(hwnd: int, insert_after: int, flags: int) -> None:
            user32.SetWindowPos(hwnd, insert_after, 0, 0, 0, 0, flags | SWP_NOMOVE | SWP_NOSIZE)

        def _bump_to_front_non_topmost(hwnd: int) -> None:
            # Trick to bump window to front of Z-order without keeping it Topmost
            _set_window_pos(hwnd, HWND_TOPMOST, SWP_NOACTIVATE)
            _set_window_pos(hwnd, HWND_NOTOPMOST, SWP_NOACTIVATE)

        # 'before' state is passed in to allow accurate diffing against current state
        before = before_hwnds
        
        # Poll for new window appearance
        end = time.time() + timeout_sec
        explorer_hwnd = None
        
        while time.time() < end:
            current_explorers = set(_win32_list_explorer_hwnds())
            new_ones = list(current_explorers - before)
            if new_ones:
                explorer_hwnd = new_ones[-1]
                break
            time.sleep(0.01) # Fast poll to minimize perceived delay

        if explorer_hwnd is None:
            # Fallback: Pick last active explorer if detection failed or window reused
            ex_list = _win32_list_explorer_hwnds()
            if not ex_list:
                return False
            explorer_hwnd = ex_list[-1]

        # (A) Bump Explorer to absolute front
        _bump_to_front_non_topmost(explorer_hwnd)

        # (B) Bump App to front (ensures it's above other apps like Steam)
        if hwnd_app:
            _set_window_pos(hwnd_app, HWND_TOP, SWP_NOACTIVATE)

            # (C) Sandwich: Insert App directly behind Explorer
            _set_window_pos(hwnd_app, explorer_hwnd, SWP_NOACTIVATE)

        return True

    except Exception as e:
        logger.warning(f"Z-Order fix failed: {e}")
        return False


def show_files_in_file_manager(paths: List[str]) -> None:
    """
    Open the file manager and select the specified files.
    Cross-platform implementation using show-in-file-manager.
    
    Args:
        paths: List of file paths to select
    """
    if not paths:
        return
        
    # Capture App HWND before potential context switch (Windows only)
    hwnd_app = 0
    before_explorers = set()
    
    if is_windows():
        hwnd_app = _win32_get_foreground_window()
        # Capture explorer state BEFORE launching to detect new windows
        try:
            before_explorers = set(_win32_list_explorer_hwnds())
        except Exception:
            pass
    
    try:
        from showinfm import show_in_file_manager
        
        # Filter existing paths
        valid_paths = [p for p in paths if os.path.exists(p)]
        
        if not valid_paths:
            logger.warning(f"No valid paths found to show in file manager from: {paths}")
            if paths:
                 parent = os.path.dirname(paths[0])
                 if os.path.exists(parent):
                     open_file_or_folder(parent)
            return
            
        # Call library function
        show_in_file_manager(valid_paths)
        
        # 2. Fix Z-Order (Windows)
        if is_windows() and hwnd_app:
             _win32_bring_explorer_front_and_app_second(hwnd_app, before_explorers)
        
    except ImportError:
        logger.error("show-in-file-manager package not installed")
        if paths:
            open_file_or_folder(os.path.dirname(paths[0]))
    except Exception as e:
        logger.error(f"Failed to show files in file manager: {e}")
        if paths:
            open_file_or_folder(os.path.dirname(paths[0]))
