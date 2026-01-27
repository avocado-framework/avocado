"""Functional tests for the genio module.

These tests validate the genio module in real-world file system scenarios,
including cross-module interactions and integration patterns.
"""

import os
import unittest

from avocado.utils import genio
from selftests.utils import TestCaseTmpDir


class TestGenioFileOperations(TestCaseTmpDir):
    """Functional tests for genio file read/write operations."""

    def test_write_read_roundtrip(self):
        """Test writing and reading back produces identical content."""
        test_file = os.path.join(self.tmpdir.name, "roundtrip.txt")
        original_content = "Line 1\nLine 2\nLine 3\n"
        genio.write_file(test_file, original_content)
        read_content = genio.read_file(test_file)
        self.assertEqual(read_content, original_content)

    def test_write_one_line_read_one_line_roundtrip(self):
        """Test write_one_line and read_one_line roundtrip."""
        test_file = os.path.join(self.tmpdir.name, "one_line.txt")
        genio.write_one_line(test_file, "Single line content")
        line = genio.read_one_line(test_file)
        self.assertEqual(line, "Single line content")

    def test_append_builds_file_incrementally(self):
        """Test building a file incrementally with append operations."""
        test_file = os.path.join(self.tmpdir.name, "incremental.txt")
        lines_to_add = ["First line", "Second line", "Third line"]
        for line in lines_to_add:
            genio.append_one_line(test_file, line)
        result_lines = genio.read_all_lines(test_file)
        self.assertEqual(result_lines, lines_to_add)

    def test_large_file_operations(self):
        """Test operations on larger files."""
        test_file = os.path.join(self.tmpdir.name, "large.txt")
        lines = [f"Line {i}: {'x' * 80}" for i in range(1000)]
        content = "\n".join(lines)
        genio.write_file(test_file, content)
        read_content = genio.read_file(test_file)
        self.assertEqual(read_content, content)

    def test_unicode_file_operations(self):
        """Test file operations with unicode content."""
        test_file = os.path.join(self.tmpdir.name, "unicode.txt")
        unicode_content = "日本語テスト\nПривет мир\n🎉 Emoji test 🚀\n"
        genio.write_file(test_file, unicode_content)
        read_content = genio.read_file(test_file)
        self.assertEqual(read_content, unicode_content)

    def test_special_characters_in_content(self):
        """Test file operations with special characters."""
        test_file = os.path.join(self.tmpdir.name, "special.txt")
        special_content = "Tab:\tNewline:\\n\nBackslash:\\\nQuotes:\"'`\n"
        genio.write_file(test_file, special_content)
        read_content = genio.read_file(test_file)
        self.assertEqual(read_content, special_content)


class TestGenioPatternMatching(TestCaseTmpDir):
    """Functional tests for genio pattern matching operations."""

    def setUp(self):
        super().setUp()
        self.log_file = os.path.join(self.tmpdir.name, "debug.log")
        log_content = (
            "2024-01-01 10:00:00,123 avocado.test test_module      L0042 INFO | Starting test\n"
            "2024-01-01 10:00:01,456 avocado.test test_module      L0043 DEBUG| Loading configuration\n"
            "2024-01-01 10:00:02,789 avocado.test test_module      L0044 ERROR| Failed to connect to database\n"
            "2024-01-01 10:00:03,012 avocado.test test_module      L0045 INFO | Retrying connection\n"
            "2024-01-01 10:00:04,345 avocado.test test_module      L0046 ERROR| Connection timeout\n"
            "2024-01-01 10:00:05,678 avocado.test test_module      L0047 INFO | Connection established\n"
        )
        genio.write_file(self.log_file, log_content)

    def test_log_analysis_workflow(self):
        """Test analyzing a log file - finding errors and verifying patterns."""
        # Find all error lines
        error_lines = genio.read_line_with_matching_pattern(self.log_file, "ERROR")
        self.assertEqual(len(error_lines), 2)
        self.assertTrue(all("ERROR" in line for line in error_lines))

        # Verify timestamp pattern exists
        self.assertTrue(genio.is_pattern_in_file(self.log_file, r"\d{4}-\d{2}-\d{2}"))

    def test_config_file_pattern_extraction(self):
        """Test extracting values from a config-like file."""
        config_file = os.path.join(self.tmpdir.name, "config.ini")
        config_content = (
            "[database]\n"
            "host=localhost\n"
            "port=5432\n"
            "name=testdb\n"
            "\n"
            "[server]\n"
            "host=0.0.0.0\n"
            "port=8080\n"
        )
        genio.write_file(config_file, config_content)
        # Find all host settings
        host_lines = genio.read_line_with_matching_pattern(config_file, "host=")
        self.assertEqual(len(host_lines), 2)
        # Verify section markers
        self.assertTrue(genio.is_pattern_in_file(config_file, r"\[database\]"))


class TestGenioFileComparison(TestCaseTmpDir):
    """Functional tests for genio file comparison in workflows."""

    def test_copy_verification_workflow(self):
        """Test using are_files_equal to verify file copy integrity."""
        source = os.path.join(self.tmpdir.name, "source.txt")
        dest = os.path.join(self.tmpdir.name, "dest.txt")
        genio.write_file(source, "Original content for copy test\n")

        # Simulate a copy by reading and writing
        content = genio.read_file(source)
        genio.write_file(dest, content)

        # Verify copy integrity
        self.assertTrue(genio.are_files_equal(source, dest))

        # Modify dest and verify they're now different
        genio.append_file(dest, "extra content")
        self.assertFalse(genio.are_files_equal(source, dest))


class TestGenioRealWorldScenarios(TestCaseTmpDir):
    """Functional tests simulating real-world usage scenarios."""

    def test_config_file_modification_workflow(self):
        """Test complete workflow: read config, modify value, verify change."""
        config_file = os.path.join(self.tmpdir.name, "app.conf")
        initial_config = "debug=false\nport=8080\nhost=localhost\n"
        genio.write_file(config_file, initial_config)

        # Read, modify, write pattern
        content = genio.read_file(config_file)
        modified_content = content.replace("debug=false", "debug=true")
        genio.write_file(config_file, modified_content)

        # Verify modification
        self.assertTrue(genio.is_pattern_in_file(config_file, "debug=true"))
        self.assertFalse(genio.is_pattern_in_file(config_file, "debug=false"))

    def test_log_aggregation_workflow(self):
        """Test analyzing a log file and counting different log levels."""
        log_file = os.path.join(self.tmpdir.name, "app.log")
        log_entries = [
            "[2024-01-01 10:00:00] INFO: Application started",
            "[2024-01-01 10:00:01] WARNING: Low memory",
            "[2024-01-01 10:00:02] ERROR: Database connection failed",
            "[2024-01-01 10:00:03] INFO: Retrying...",
            "[2024-01-01 10:00:04] INFO: Connection restored",
        ]
        genio.write_file(log_file, "\n".join(log_entries) + "\n")

        # Count different log levels
        errors = genio.read_line_with_matching_pattern(log_file, "ERROR:")
        warnings = genio.read_line_with_matching_pattern(log_file, "WARNING:")
        infos = genio.read_line_with_matching_pattern(log_file, "INFO:")

        self.assertEqual(len(errors), 1)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(len(infos), 3)

    def test_incremental_logging_workflow(self):
        """Test simulating incremental log file building."""
        log_file = os.path.join(self.tmpdir.name, "events.log")
        events = ["Event 1 occurred", "Event 2 occurred", "Event 3 occurred"]

        for event in events:
            genio.append_one_line(log_file, event)

        all_events = genio.read_all_lines(log_file)
        self.assertEqual(all_events, events)

    def test_csv_data_verification_workflow(self):
        """Test verifying CSV file structure and content."""
        data_file = os.path.join(self.tmpdir.name, "data.csv")
        csv_content = "name,age,city\nAlice,30,NYC\nBob,25,LA\nCharlie,35,Chicago\n"
        genio.write_file(data_file, csv_content)

        # Verify header
        first_line = genio.read_one_line(data_file)
        self.assertEqual(first_line, "name,age,city")

        # Verify data row pattern
        self.assertTrue(genio.is_pattern_in_file(data_file, r"^\w+,\d+,\w+$"))


if __name__ == "__main__":
    unittest.main()
