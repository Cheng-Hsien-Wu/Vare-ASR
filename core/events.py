"""
EventBus - Decoupled event system for UI updates.
Allows Controllers to emit events and Pages to subscribe.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class EventBus:
    """Simple publish-subscribe event bus for decoupling components"""
    
    _listeners: Dict[str, List[Callable]] = {}
    
    @classmethod
    def subscribe(cls, event: str, callback: Callable[[Any], None]) -> None:
        """Subscribe to an event.
        
        Args:
            event: Event name (e.g., 'tasks_changed', 'theme_changed')
            callback: Function to call when event is emitted
        """
        if event not in cls._listeners:
            cls._listeners[event] = []
        if callback not in cls._listeners[event]:
            cls._listeners[event].append(callback)
    
    @classmethod
    def unsubscribe(cls, event: str, callback: Callable) -> None:
        """Unsubscribe from an event."""
        if event in cls._listeners and callback in cls._listeners[event]:
            cls._listeners[event].remove(callback)
    
    @classmethod
    def emit(cls, event: str, data: Any = None) -> None:
        """Emit an event to all subscribers.
        
        Args:
            event: Event name
            data: Optional data to pass to callbacks
        """
        if event in cls._listeners:
            for callback in list(cls._listeners[event]):  # Copy list to allow modification
                try:
                    if inspect.iscoroutinefunction(callback):
                        # Schedule async callback on the event loop
                        asyncio.create_task(callback(data))
                    else:
                        # Call sync callback directly
                        callback(data)
                except Exception as e:
                    logger.error(f"EventBus: Error in callback for '{event}': {e}")
    
    @classmethod
    def clear(cls, event: str = None) -> None:
        """Clear listeners for a specific event or all events."""
        if event:
            cls._listeners.pop(event, None)
        else:
            cls._listeners.clear()


# Common event names as constants
class Events:
    """Standard event names used throughout the application"""
    TASKS_CHANGED = "tasks_changed"
    TASK_ADDED = "task_added"
    TASK_REMOVED = "task_removed"
    TASK_STATUS_CHANGED = "task_status_changed"
    PROCESSING_STARTED = "processing_started"
    PROCESSING_STOPPED = "processing_stopped"
    PROCESSING_FINISHED = "processing_finished"
    THEME_CHANGED = "theme_changed"
    SETTINGS_CHANGED = "settings_changed"
    LOG_MESSAGE = "log_message"
    APP_LANGUAGE_CHANGED = "app_language_changed"
    TEXT_SCALE_CHANGED = "text_scale_changed"
    
    # File/Folder Picker Events
    BROWSE_MODEL_DIR_REQUESTED = "browse_model_dir_requested"
    BROWSE_OUTPUT_DIR_REQUESTED = "browse_output_dir_requested"
    MODEL_DIR_CHANGED = "model_dir_changed"
    OUTPUT_DIR_CHANGED = "output_dir_changed"
    
    # Device/Hardware Events
    DEVICE_CHANGED = "device_changed"  # Emitted when user switches CPU/GPU
    
    # LLM Events
    LLM_TEST_CONNECTION_REQUESTED = "llm_test_connection_requested"
    LLM_CONNECTION_RESULT = "llm_connection_result"
