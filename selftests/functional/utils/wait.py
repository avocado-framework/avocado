import os
import threading
import time
import unittest

from avocado.utils import wait
from selftests.utils import TestCaseTmpDir


class WaitForFunctionalTest(TestCaseTmpDir):
    """Functional tests for wait.wait_for with real-world scenarios."""

    def test_condition_becomes_true(self):
        """Test wait_for with condition that eventually becomes true (real I/O)."""
        filepath = os.path.join(self.tmpdir.name, "test_file.txt")

        # Create file after a delay
        def create_file_delayed():
            time.sleep(0.3)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("test content")

        # Start file creation in background
        thread = threading.Thread(target=create_file_delayed)
        thread.start()

        # Wait for file to exist
        result = wait.wait_for(
            lambda: os.path.exists(filepath),
            timeout=2.0,
            step=0.1,
            text="Waiting for file to appear",
        )

        thread.join()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(filepath))

    def test_timeout_when_condition_never_true(self):
        """Test that wait_for respects timeout when condition never becomes true."""
        filepath = os.path.join(self.tmpdir.name, "nonexistent.txt")

        # Wait for a file that will never be created
        start = time.time()
        result = wait.wait_for(lambda: os.path.exists(filepath), timeout=0.5, step=0.1)
        elapsed = time.time() - start

        self.assertIsNone(result)
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 0.7)


if __name__ == "__main__":
    unittest.main()
