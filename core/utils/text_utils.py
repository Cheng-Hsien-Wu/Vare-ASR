"""
Text utility functions.
"""
import re

def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape sequences from text.
    Useful for cleaning up terminal output captured from subprocesses.
    """
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def clean_error_message(text: str) -> str:
    """
    Clean error message by stripping ANSI codes and redundant prefixes.
    Removes 'ERROR: ' or 'ERROR: [yt_dlp] ' prefixes.
    """
    text = strip_ansi(text)
    # Remove redundant "ERROR: " or "ERROR: [xxx] " prefix
    # case insensitive
    return re.sub(r'ERROR:\s*(\[[^\]]+\]\s*)?', '', text, flags=re.IGNORECASE)

def sanitize_filename(name: str) -> str:
    """
    Sanitize filename by removing illegal characters for Windows/Linux/macOS.
    Removes: < > : " / \\ | ? *
    Returns empty string if result is all invalid chars.
    """

    return "".join(c for c in name if c not in '<>:"/\\|?*').strip()
