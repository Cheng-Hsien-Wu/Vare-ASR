"""
Unit Tests for LLM Chunking Modules
Tests TokenEstimator, SRTParser, TextChunker, and ChunkMerger.
"""

import unittest

# Test data
SAMPLE_SRT = """1
00:00:00,000 --> 00:00:05,000
這是第一段字幕

2
00:00:05,000 --> 00:00:10,000
This is the second subtitle

3
00:00:10,000 --> 00:00:15,000
這是第三段字幕

4
00:00:15,000 --> 00:00:20,000
Fourth segment here

5
00:00:20,000 --> 00:00:25,000
第五段字幕內容
"""


class TestTokenEstimator(unittest.TestCase):
    """Test TokenEstimator class."""
    
    def test_count_tokens_english(self):
        """Test token counting for English text."""
        from features.llm.token_estimator import TokenEstimator
        estimator = TokenEstimator()
        
        tokens = estimator.count_tokens("Hello, world!")
        self.assertGreater(tokens, 0)
        self.assertIsInstance(tokens, int)
    
    def test_count_tokens_chinese(self):
        """Test token counting for Chinese text."""
        from features.llm.token_estimator import TokenEstimator
        estimator = TokenEstimator()
        
        tokens = estimator.count_tokens("這是一段中文測試")
        self.assertGreater(tokens, 0)
    
    def test_count_tokens_empty(self):
        """Test token counting for empty string."""
        from features.llm.token_estimator import TokenEstimator
        estimator = TokenEstimator()
        
        tokens = estimator.count_tokens("")
        self.assertEqual(tokens, 0)
    
    def test_estimate_with_overhead(self):
        """Test token estimation with overhead margin."""
        from features.llm.token_estimator import TokenEstimator
        estimator = TokenEstimator()
        
        # Use longer text to avoid rounding issues
        text = "This is a longer test text for overhead estimation"
        base = estimator.count_tokens(text)
        with_overhead = estimator.estimate_with_overhead(text, 0.1)
        self.assertGreaterEqual(with_overhead, base)


class TestSRTParser(unittest.TestCase):
    """Test SRTParser class."""
    
    def test_parse_valid_srt(self):
        """Test parsing valid SRT content."""
        from features.llm.chunker import SRTParser
        
        segments = SRTParser.parse(SAMPLE_SRT)
        
        self.assertEqual(len(segments), 5)
        self.assertAlmostEqual(segments[0].start_time, 0.0)
        self.assertAlmostEqual(segments[0].end_time, 5.0)
    
    def test_parse_empty(self):
        """Test parsing empty content."""
        from features.llm.chunker import SRTParser
        
        segments = SRTParser.parse("")
        self.assertEqual(len(segments), 0)
    
    def test_parse_time_extraction(self):
        """Test correct time extraction."""
        from features.llm.chunker import SRTParser
        
        srt = "1\n00:01:30,500 --> 00:02:00,000\nTest"
        segments = SRTParser.parse(srt)
        
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0].start_time, 90.5)
        self.assertAlmostEqual(segments[0].end_time, 120.0)


class TestTextChunker(unittest.TestCase):
    """Test TextChunker class."""
    
    def test_no_chunking_needed(self):
        """Test that small content returns single chunk."""
        from features.llm.chunker import TextChunker, ChunkConfig
        
        config = ChunkConfig(max_tokens=100000)
        chunker = TextChunker(config=config)
        
        chunks = chunker.chunk_srt(SAMPLE_SRT)
        
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].total_chunks, 1)
    
    def test_needs_chunking_detection(self):
        """Test needs_chunking correctly detects large content."""
        from features.llm.chunker import TextChunker, ChunkConfig
        
        config = ChunkConfig(max_tokens=50)
        chunker = TextChunker(config=config)
        
        self.assertTrue(chunker.needs_chunking(SAMPLE_SRT))
    
    def test_chunk_config_available_tokens(self):
        """Test ChunkConfig calculates available tokens correctly."""
        from features.llm.chunker import ChunkConfig
        
        config = ChunkConfig(
            max_tokens=65536,
            reserved_for_output=8192,
            reserved_for_prompt=2048
        )
        
        self.assertEqual(config.available_tokens, 65536 - 8192 - 2048)


class TestChunkMerger(unittest.TestCase):
    """Test ChunkMerger class."""
    
    def test_merge_single_chunk(self):
        """Test merging single chunk."""
        from features.llm.merger import ChunkMerger
        
        merger = ChunkMerger()
        result = merger.merge_results([SAMPLE_SRT])
        
        self.assertIn("第一段", result)
    
    def test_merge_empty(self):
        """Test merging empty list."""
        from features.llm.merger import ChunkMerger
        
        merger = ChunkMerger()
        result = merger.merge_results([])
        self.assertEqual(result, "")
    
    def test_merge_removes_duplicates(self):
        """Test that merging removes duplicate segments."""
        from features.llm.merger import ChunkMerger
        
        chunk1 = "1\n00:00:00,000 --> 00:00:05,000\nFirst\n\n2\n00:00:05,000 --> 00:00:10,000\nOverlap\n"
        chunk2 = "1\n00:00:05,000 --> 00:00:10,000\nOverlap\n\n2\n00:00:10,000 --> 00:00:15,000\nLast\n"
        
        merger = ChunkMerger()
        result = merger.merge_results([chunk1, chunk2], [0, 1])
        
        # Should have 3 unique segments
        self.assertEqual(result.count("-->"), 3)


class TestIntegration(unittest.TestCase):
    """Integration tests."""
    
    def test_full_pipeline(self):
        """Test full chunking pipeline."""
        from features.llm.chunker import TextChunker, ChunkConfig
        from features.llm.merger import ChunkMerger
        
        chunker = TextChunker(config=ChunkConfig(max_tokens=100000))
        merger = ChunkMerger()
        
        chunks = chunker.chunk_srt(SAMPLE_SRT)
        corrected = [c.content for c in chunks]
        result = merger.merge_results(corrected, [c.overlap_count for c in chunks])
        
        self.assertIn("第一段", result)
        self.assertIn("第五段", result)


if __name__ == '__main__':
    unittest.main()
