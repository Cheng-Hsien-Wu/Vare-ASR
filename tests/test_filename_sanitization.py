
import sys
import os
import unittest

# Ensure project root is in path
sys.path.insert(0, os.getcwd())

from core.utils.text_utils import sanitize_filename

class TestFilenameSanitization(unittest.TestCase):
    def test_clean_filename(self):
        """Test already clean filenames remain unchanged"""
        self.assertEqual(sanitize_filename("clean.txt"), "clean.txt")
        self.assertEqual(sanitize_filename("My Document 2024.docx"), "My Document 2024.docx")
        
    def test_illegal_chars(self):
        """Test removal of illegal characters"""
        # < > : " / \ | ? *
        self.assertEqual(sanitize_filename("bad<name>.txt"), "badname.txt")
        self.assertEqual(sanitize_filename("test:file.txt"), "testfile.txt")
        self.assertEqual(sanitize_filename('quote"mark.txt'), 'quotemark.txt')
        self.assertEqual(sanitize_filename("path/to/file.txt"), "pathtofile.txt")
        self.assertEqual(sanitize_filename("back\\slash.txt"), "backslash.txt")
        self.assertEqual(sanitize_filename("pipe|line.txt"), "pipeline.txt")
        self.assertEqual(sanitize_filename("what?why*.txt"), "whatwhy.txt")
        
    def test_whitespace(self):
        """Test trimming of whitespace"""
        self.assertEqual(sanitize_filename("  clean.txt  "), "clean.txt")
        
    def test_mixed(self):
        """Test mixed scenarios"""
        input_str = '  <Duplicate>: "File/Name?.txt"  '
        # < " / ? removed -> Duplicate : FileName.txt -> : removed
        expected = "Duplicate FileName.txt"
        self.assertEqual(sanitize_filename(input_str), expected)
        
    def test_all_invalid(self):
        """Test string with only invalid chars"""
        self.assertEqual(sanitize_filename("<>/?"), "")

if __name__ == "__main__":
    unittest.main()
