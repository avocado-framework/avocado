import hashlib
import os
import unittest

from avocado.utils import crypto
from selftests.utils import TestCaseTmpDir


class HashFileTest(TestCaseTmpDir):
    """Test cases for crypto.hash_file function."""

    def _create_test_file(self, content, filename="testfile"):
        """Helper to create a test file with given content."""
        filepath = os.path.join(self.tmpdir.name, filename)
        with open(filepath, "wb") as f:
            f.write(content)
        return filepath

    # Core algorithm tests - testing the algorithm parameter code path
    def test_hash_file_md5_default(self):
        """Test MD5 hash calculation with default algorithm."""
        content = b"Hello, World!"
        filepath = self._create_test_file(content)
        expected = hashlib.md5(content).hexdigest()
        result = crypto.hash_file(filepath)
        self.assertEqual(result, expected)

    def test_hash_file_sha256(self):
        """Test SHA256 hash calculation."""
        content = b"Test content for SHA256"
        filepath = self._create_test_file(content)
        expected = hashlib.sha256(content).hexdigest()
        result = crypto.hash_file(filepath, algorithm="sha256")
        self.assertEqual(result, expected)

    # Size parameter tests - each tests a distinct code path
    def test_hash_file_with_size_limit(self):
        """Test hashing only the first N bytes of a file."""
        content = b"ABCDEFGHIJ"  # 10 bytes
        filepath = self._create_test_file(content)
        # Hash only first 5 bytes - tests size < file_size path
        expected = hashlib.md5(b"ABCDE").hexdigest()
        result = crypto.hash_file(filepath, size=5)
        self.assertEqual(result, expected)

    def test_hash_file_size_larger_than_file(self):
        """Test that size larger than file hashes the whole file."""
        content = b"Small file"
        filepath = self._create_test_file(content)
        expected = hashlib.md5(content).hexdigest()
        # Request more bytes than file contains - tests size > file_size branch
        result = crypto.hash_file(filepath, size=1000000)
        self.assertEqual(result, expected)

    def test_hash_file_size_falsy_hashes_whole_file(self):
        """Test that falsy size values (None, 0) hash the entire file."""
        content = b"Complete file content"
        filepath = self._create_test_file(content)
        expected = hashlib.md5(content).hexdigest()
        # Both None and 0 are falsy - tests 'not size' branch
        self.assertEqual(crypto.hash_file(filepath, size=None), expected)
        self.assertEqual(crypto.hash_file(filepath, size=0), expected)

    # Edge case tests - each tests unique behavior
    def test_hash_file_empty_file(self):
        """Test hashing an empty file."""
        filepath = self._create_test_file(b"")
        expected = hashlib.md5(b"").hexdigest()
        result = crypto.hash_file(filepath)
        self.assertEqual(result, expected)

    def test_hash_file_binary_content(self):
        """Test hashing a file with all possible byte values."""
        content = bytes(range(256))  # All byte values 0-255
        filepath = self._create_test_file(content)
        expected = hashlib.md5(content).hexdigest()
        result = crypto.hash_file(filepath)
        self.assertEqual(result, expected)

    def test_hash_file_larger_than_chunk_size(self):
        """Test hashing a file that requires multiple read iterations."""
        # Create content larger than io.DEFAULT_BUFFER_SIZE (typically 8192)
        content = b"x" * 100000
        filepath = self._create_test_file(content)
        expected = hashlib.md5(content).hexdigest()
        result = crypto.hash_file(filepath)
        self.assertEqual(result, expected)

    # Error handling tests
    def test_hash_file_invalid_algorithm_returns_none(self):
        """Test that invalid algorithm returns None without raising."""
        content = b"Test content"
        filepath = self._create_test_file(content)
        result = crypto.hash_file(filepath, algorithm="invalid_algo")
        self.assertIsNone(result)

    def test_hash_file_nonexistent_file_raises(self):
        """Test that non-existent file raises FileNotFoundError."""
        nonexistent = os.path.join(self.tmpdir.name, "nonexistent_file.txt")
        with self.assertRaises(FileNotFoundError):
            crypto.hash_file(nonexistent)

    # Hash uniqueness test - verifies hash function works correctly
    def test_hash_file_different_content_produces_different_hash(self):
        """Test that different content produces different hash values."""
        filepath1 = self._create_test_file(b"Content A", filename="file1.txt")
        filepath2 = self._create_test_file(b"Content B", filename="file2.txt")
        hash1 = crypto.hash_file(filepath1)
        hash2 = crypto.hash_file(filepath2)
        self.assertNotEqual(hash1, hash2)


if __name__ == "__main__":
    unittest.main()
