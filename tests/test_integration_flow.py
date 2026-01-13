
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from core.events import EventBus, Events
from controllers.task_controller import TaskController

class TestIntegrationFlow(unittest.TestCase):
    def setUp(self):
        # Mock Flet page since TaskController needs it
        self.mock_page = MagicMock()
        self.controller = TaskController(self.mock_page)
        
        # Reset EventBus listeners to avoid pollution
        EventBus._listeners = {}

    def test_add_files_emits_event(self):
        """Test that adding files triggers TASKS_CHANGED event"""
        # Create a mock subscriber
        subscriber = MagicMock()
        EventBus.subscribe(Events.TASKS_CHANGED, subscriber)
        
        # Add a file (assuming it's supported or mocking glob)
        # We need to mock Path to avoid actual file system checks if possible,
        # but the controller checks path.suffix.
        # Let's provide a dummy file path with supported extension.
        test_files = ["test_video.mp4"]
        
        added = self.controller.add_files(test_files)
        
        # Verify result
        self.assertEqual(added, 1)
        self.assertEqual(len(self.controller.tasks), 1)
        
        # Verify EventBus emission
        subscriber.assert_called_once()
        args, _ = subscriber.call_args
        self.assertEqual(args[0], self.controller.tasks) # The payload should be the task list

    def test_remove_task_emits_event(self):
        """Test that removing a task triggers TASK_REMOVED and TASKS_CHANGED"""
        # Setup initial state
        self.controller.tasks.append(MagicMock())
        
        sub_removed = MagicMock()
        sub_changed = MagicMock()
        
        EventBus.subscribe(Events.TASK_REMOVED, sub_removed)
        EventBus.subscribe(Events.TASKS_CHANGED, sub_changed)
        
        # Action
        result = self.controller.remove_task(0)
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(len(self.controller.tasks), 0)
        
        sub_removed.assert_called_once()
        sub_changed.assert_called_once()

    def test_update_status_emits_event(self):
        """Test that updating status triggers TASK_STATUS_CHANGED"""
        # Setup
        task = MagicMock()
        self.controller.tasks.append(task)
        
        subscriber = MagicMock()
        EventBus.subscribe(Events.TASK_STATUS_CHANGED, subscriber)
        
        # Action
        self.controller.update_task_status(0, "status_processing", progress=50)
        
        # Verify
        subscriber.assert_called_once()
        task.status = "status_processing" # Mock should have been updated? No, controller updates attributes.
        # controller.update_task_status updates the task object attributes.
        # Check args
        args, _ = subscriber.call_args
        payload = args[0]
        self.assertEqual(payload['index'], 0)
        self.assertEqual(payload['task'], task)

if __name__ == "__main__":
    unittest.main()
