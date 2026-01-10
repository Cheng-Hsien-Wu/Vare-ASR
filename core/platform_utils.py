import platform
import os
import subprocess
import sys
import logging

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
        script = os.path.abspath(sys.argv[0])
        
        # ShellExecuteW with "runas" verb to request elevation
        # Returns value > 32 on success
        result = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operation - run as admin
            python_exe,     # file
            f'"{script}"',  # parameters
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

