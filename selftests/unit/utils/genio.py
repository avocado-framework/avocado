import os
import tempfile
import unittest
from unittest import mock

from avocado.utils import genio
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class TestGenIOError(unittest.TestCase):
    """Tests for the GenIOError exception class."""

    def test_genio_error_behavior(self):
        """Test GenIOError is a proper exception with message support."""
        self.assertTrue(issubclass(genio.GenIOError, Exception))
        error = genio.GenIOError("test error message")
        self.assertEqual(str(error), "test error message")


class TestAsk(unittest.TestCase):
    """Tests for the ask function."""

    def test_ask_auto_returns_y(self):
        """Test that auto=True returns 'y' without prompting."""
        result = genio.ask("Do you want to continue?", auto=True)
        self.assertEqual(result, "y")

    @mock.patch("builtins.input", return_value="n")
    def test_ask_prompts_user(self, mock_input):
        """Test that ask prompts user and returns their input."""
        result = genio.ask("Continue?", auto=False)
        self.assertEqual(result, "n")
        mock_input.assert_called_once_with("Continue? (y/n) ")


class TestReadFile(unittest.TestCase):
    """Tests for the read_file function."""

    def test_read_file_returns_content(self):
        """Test reading file content including multiline and unicode."""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Line 1\nLine 2\n日本語 🎉")
            f.flush()
            content = genio.read_file(f.name)
        os.unlink(f.name)
        self.assertEqual(content, "Line 1\nLine 2\n日本語 🎉")

    def test_read_file_empty(self):
        """Test reading an empty file returns empty string."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.flush()
            content = genio.read_file(f.name)
        os.unlink(f.name)
        self.assertEqual(content, "")

    def test_read_file_nonexistent_raises(self):
        """Test that reading a nonexistent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            genio.read_file("/nonexistent/path/to/file.txt")


class TestReadOneLine(unittest.TestCase):
    """Tests for the read_one_line function."""

    def test_read_one_line_returns_first_line_stripped(self):
        """Test reading first line with newline stripped."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("First line\nSecond line\n")
            f.flush()
            line = genio.read_one_line(f.name)
        os.unlink(f.name)
        self.assertEqual(line, "First line")

    def test_read_one_line_empty_file(self):
        """Test reading from an empty file returns empty string."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.flush()
            line = genio.read_one_line(f.name)
        os.unlink(f.name)
        self.assertEqual(line, "")


class TestReadAllLines(unittest.TestCase):
    """Tests for the read_all_lines function."""

    def test_read_all_lines_returns_list_stripped(self):
        """Test reading all lines with newlines stripped."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("Line 1\nLine 2\nLine 3\n")
            f.flush()
            lines = genio.read_all_lines(f.name)
        os.unlink(f.name)
        self.assertEqual(lines, ["Line 1", "Line 2", "Line 3"])

    def test_read_all_lines_graceful_on_error(self):
        """Test that errors return empty list instead of raising."""
        # Nonexistent file
        self.assertEqual(genio.read_all_lines("/nonexistent/path/file.txt"), [])
        # Directory path causes error
        self.assertEqual(genio.read_all_lines("/"), [])


class TestReadLineWithMatchingPattern(unittest.TestCase):
    """Tests for the read_line_with_matching_pattern function."""

    def test_matching_pattern_finds_lines(self):
        """Test finding matching lines with newlines stripped."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("ERROR: First\nINFO: Middle\nERROR: Second\n")
            f.flush()
            matches = genio.read_line_with_matching_pattern(f.name, "ERROR")
        os.unlink(f.name)
        self.assertEqual(len(matches), 2)
        self.assertNotIn("\n", matches[0])

    def test_matching_pattern_no_match(self):
        """Test that no matches returns empty list."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("INFO: Something\nDEBUG: Another\n")
            f.flush()
            matches = genio.read_line_with_matching_pattern(f.name, "ERROR")
        os.unlink(f.name)
        self.assertEqual(matches, [])


class TestWriteFile(unittest.TestCase):
    """Tests for the write_file function."""

    def test_write_file_creates_and_overwrites(self):
        """Test writing creates file and overwrites existing content."""
        prefix = temp_dir_prefix(self)
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        filename = os.path.join(tmpdir, "test.txt")
        # Create new file
        genio.write_file(filename, "Original")
        self.assertEqual(genio.read_file(filename), "Original")
        # Overwrite
        genio.write_file(filename, "New 日本語 🎉")
        self.assertEqual(genio.read_file(filename), "New 日本語 🎉")
        os.unlink(filename)
        os.rmdir(tmpdir)


class TestWriteOneLine(unittest.TestCase):
    """Tests for the write_one_line function."""

    def test_write_one_line_adds_single_newline(self):
        """Test that write_one_line adds exactly one newline."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            filename = f.name
        # Without trailing newline
        genio.write_one_line(filename, "Line")
        self.assertEqual(genio.read_file(filename), "Line\n")
        # With trailing newline - should not double
        genio.write_one_line(filename, "Line\n")
        self.assertEqual(genio.read_file(filename), "Line\n")
        os.unlink(filename)


class TestWriteFileOrFail(unittest.TestCase):
    """Tests for the write_file_or_fail function."""

    def test_write_file_or_fail_success(self):
        """Test successful write."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            filename = f.name
        genio.write_file_or_fail(filename, "Success content")
        self.assertEqual(genio.read_file(filename), "Success content")
        os.unlink(filename)

    def test_write_file_or_fail_raises_genioerror(self):
        """Test that GenIOError is raised with details on failure."""
        bad_path = "/nonexistent/directory/file.txt"
        with self.assertRaises(genio.GenIOError) as context:
            genio.write_file_or_fail(bad_path, "content")
        self.assertIn(bad_path, str(context.exception))


class TestAppendFile(unittest.TestCase):
    """Tests for the append_file function."""

    def test_append_file_appends_content(self):
        """Test appending to existing file and creating new file."""
        prefix = temp_dir_prefix(self)
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        filename = os.path.join(tmpdir, "append.txt")
        # Creates new file
        genio.append_file(filename, "First")
        genio.append_file(filename, " Second")
        self.assertEqual(genio.read_file(filename), "First Second")
        os.unlink(filename)
        os.rmdir(tmpdir)


class TestAppendOneLine(unittest.TestCase):
    """Tests for the append_one_line function."""

    def test_append_one_line_adds_newlines(self):
        """Test that append_one_line adds exactly one newline per call."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            filename = f.name
        genio.append_one_line(filename, "Line 1")
        genio.append_one_line(filename, "Line 2\n")  # Should not double newline
        self.assertEqual(genio.read_file(filename), "Line 1\nLine 2\n")
        os.unlink(filename)


class TestIsPatternInFile(unittest.TestCase):
    """Tests for the is_pattern_in_file function."""

    def test_pattern_matching_with_regex(self):
        """Test regex pattern matching returns True/False correctly."""
        with tempfile.NamedTemporaryFile(mode="w") as temp_file:
            temp_file.write("Line 1\n123\nLine 3\n")
            temp_file.seek(0)
            # Matches
            self.assertTrue(genio.is_pattern_in_file(temp_file.name, r"\d{3}"))
            self.assertTrue(genio.is_pattern_in_file(temp_file.name, "Line"))
            # No match
            self.assertFalse(genio.is_pattern_in_file(temp_file.name, r"\D{10}"))

    def test_pattern_in_file_raises_for_invalid_file(self):
        """Test that GenIOError is raised for directory or nonexistent file."""
        prefix = temp_dir_prefix(self)
        tempdirname = tempfile.mkdtemp(prefix=prefix)
        with self.assertRaises(genio.GenIOError):
            genio.is_pattern_in_file(tempdirname, "something")
        os.rmdir(tempdirname)
        with self.assertRaises(genio.GenIOError):
            genio.is_pattern_in_file("/nonexistent/file.txt", "pattern")


class TestAreFilesEqual(unittest.TestCase):
    """Tests for the are_files_equal function."""

    def test_are_files_equal_compares_by_hash(self):
        """Test file comparison using hash - identical, different, and same file."""
        file_1 = tempfile.NamedTemporaryFile(mode="w", delete=False)
        file_2 = tempfile.NamedTemporaryFile(mode="w", delete=False)
        # Identical content
        for f in [file_1, file_2]:
            f.write("Same content")
            f.close()
        self.assertTrue(genio.are_files_equal(file_1.name, file_2.name))
        # Same file compared to itself
        self.assertTrue(genio.are_files_equal(file_1.name, file_1.name))
        # Different content
        with open(file_2.name, "w", encoding="utf-8") as f:
            f.write("Different")
        self.assertFalse(genio.are_files_equal(file_1.name, file_2.name))
        os.unlink(file_1.name)
        os.unlink(file_2.name)


if __name__ == "__main__":
    unittest.main()
