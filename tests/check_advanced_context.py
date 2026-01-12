import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.llm.gemini import GeminiProvider

class TestAdvancedContext(unittest.TestCase):
    
    def setUp(self):
        self.provider = GeminiProvider(api_key="test_key")
        self.mock_client = MagicMock()
        self.provider._client = self.mock_client
        self.provider._file_cache = {}

    @patch('time.sleep', return_value=None)
    def test_upload_and_wait_success(self, mock_sleep):
        # Mock file object with state transitions
        mock_file_processing = MagicMock()
        mock_file_processing.name = "files/123"
        mock_file_processing.state.name = "PROCESSING"
        
        mock_file_active = MagicMock()
        mock_file_active.name = "files/123"
        mock_file_active.state.name = "ACTIVE"
        
        # Setup client behavior
        self.mock_client.files.upload.return_value = mock_file_processing
        self.mock_client.files.get.side_effect = [mock_file_processing, mock_file_active]
        
        # Call method
        result = self.provider._upload_and_wait("test_audio.mp3")
        
        # Verify
        self.mock_client.files.upload.assert_called_with(path="test_audio.mp3", config=None)
        self.assertEqual(result.state.name, "ACTIVE")
        self.assertIn("test_audio.mp3", self.provider._file_cache)
        
    def test_caching_behavior(self):
        # Pre-populate cache
        mock_cached_file = MagicMock()
        self.provider._file_cache["cached_file.txt"] = mock_cached_file
        
        # Call method
        result = self.provider._upload_and_wait("cached_file.txt")
        
        # Verify no upload called
        self.mock_client.files.upload.assert_not_called()
        self.assertEqual(result, mock_cached_file)

    def test_correct_text_with_file_caching(self):
        # Mock _upload_and_wait to return a mock file immediately
        mock_text_file = MagicMock()
        mock_text_file.name = "files/text_ref"
        
        self.provider._upload_and_wait = MagicMock(return_value=mock_text_file)
        
        # Mock generate_content response
        mock_response = MagicMock()
        mock_response.text = "Corrected Text"
        self.mock_client.models.generate_content.return_value = mock_response
        
        # Input text long enough to trigger file caching (>100 chars)
        long_text = "A" * 150
        
        # Run correct_text
        self.provider.correct_text(long_text, use_file_caching=True)
        
        # Verify contents passed to generate_content
        call_args = self.mock_client.models.generate_content.call_args
        contents = call_args.kwargs['contents']
        
        # Should contain [mock_text_file]
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0], mock_text_file)
        
    def test_correct_text_with_audio_grounding_and_file_caching(self):
        # Mock _upload_and_wait to handle both calls
        mock_audio_file = MagicMock()
        mock_audio_file.name = "files/audio_ref"
        
        mock_text_file = MagicMock()
        mock_text_file.name = "files/text_ref"
        
        def side_effect(path, mime_type=None):
            if path == "audio.mp3": return mock_audio_file
            if ".srt" in path: return mock_text_file
            return None
            
        self.provider._upload_and_wait = MagicMock(side_effect=side_effect)
        
        # Mock response
        mock_response = MagicMock()
        mock_response.text = "Corrected"
        self.mock_client.models.generate_content.return_value = mock_response
        
        with patch('os.path.exists', return_value=True): 
             self.provider.correct_text("A" * 150, audio_path="audio.mp3", use_file_caching=True)
        
        # Verify contents structure
        # Structure: [audio_file, "prompt...", text_file]
        call_args = self.mock_client.models.generate_content.call_args
        contents = call_args.kwargs['contents']
        
        self.assertEqual(len(contents), 3)
        self.assertEqual(contents[0], mock_audio_file)
        self.assertIsInstance(contents[1], str) 
        self.assertEqual(contents[2], mock_text_file)

if __name__ == '__main__':
    unittest.main()
