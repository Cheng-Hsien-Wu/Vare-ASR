
import unittest
from features.llm.chunker import Chunk, SRTSegment

class TestChunkerSafety(unittest.TestCase):
    def setUp(self):
        # Create a sample chunk with 5 segments
        self.segments = [
            SRTSegment(1, 0.0, 1.0, "Line 1"),
            SRTSegment(2, 1.0, 2.0, "Line 2"),
            SRTSegment(3, 2.0, 3.0, "Line 3"),
            SRTSegment(4, 3.0, 4.0, "Line 4"),
            SRTSegment(5, 4.0, 5.0, "Line 5"),
        ]
        self.chunk = Chunk(
            content="Original Content",
            segments=self.segments,
            token_count=100
        )

    def test_update_from_text_match(self):
        """Test successful update when line counts match."""
        corrected_text = "Corrected 1\nCorrected 2\nCorrected 3\nCorrected 4\nCorrected 5"
        self.chunk.update_from_text(corrected_text)
        
        # Verify updates
        self.assertEqual(self.chunk.segments[0].text, "Corrected 1")
        self.assertEqual(self.chunk.segments[4].text, "Corrected 5")

    def test_update_from_text_mismatch_abort(self):
        """Test that update ABORTS if line counts mismatch (Structural Mismatch)."""
        # 4 lines instead of 5
        corrected_text = "Corrected 1\nCorrected 2\nCorrected 3\nCorrected 4"
        
        # Current logic (Buggy) does naive mapping:
        # Segment 1 -> Corrected 1
        # Segment 4 -> Corrected 4
        # Segment 5 -> Remains "Line 5" (Unchanged but incorrectly aligned if the missing line was earlier)
        
        self.chunk.update_from_text(corrected_text)
        
        # Expectation: Chunker should ABORT and keep ALL original text
        # But since we haven't fixed it yet, this might fail or pass depending on current impl.
        # The current impl does "limit = min(len)" so it updates partials.
        # We assert what we WANT: No change.
        self.assertEqual(self.chunk.segments[0].text, "Line 1", "Segment 1 should be unchanged on mismatch")

    def test_update_from_text_trailing_newline_fix(self):
        """Test that update succeeds if mismatch is just a trailing newline."""
        # 5 lines + 1 blank line
        corrected_text = "Corrected 1\nCorrected 2\nCorrected 3\nCorrected 4\nCorrected 5\n"
        self.chunk.update_from_text(corrected_text)
        
        self.assertEqual(self.chunk.segments[0].text, "Corrected 1")
        self.assertEqual(self.chunk.segments[4].text, "Corrected 5")

if __name__ == "__main__":
    unittest.main()
