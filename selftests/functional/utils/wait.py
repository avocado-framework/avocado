import os
import time
import unittest

from avocado.utils import wait


class WaitForFunctionalTest(unittest.TestCase):
    """Functional tests for wait.wait_for with real-world scenarios."""

    def test_file_appears(self):
        """Test waiting for a file to appear in filesystem."""
        import tempfile

        # Create a temporary directory
        tmpdir = tempfile.mkdtemp()
        filepath = os.path.join(tmpdir, "test_file.txt")

        # Create file after a delay
        def create_file_delayed():
            time.sleep(0.3)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("test content")

        # Start file creation in background
        import threading

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

        # Cleanup
        os.remove(filepath)
        os.rmdir(tmpdir)

    def test_file_size_reaches_threshold(self):
        """Test waiting for a file to reach certain size."""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        filepath = os.path.join(tmpdir, "growing_file.txt")

        # Write to file gradually
        def write_gradually():
            with open(filepath, "w", encoding="utf-8") as f:
                for _ in range(10):
                    f.write("x" * 100)
                    f.flush()
                    time.sleep(0.05)

        import threading

        thread = threading.Thread(target=write_gradually)
        thread.start()

        # Wait for file to reach at least 500 bytes
        result = wait.wait_for(
            lambda: os.path.exists(filepath) and os.path.getsize(filepath) >= 500,
            timeout=2.0,
            step=0.1,
        )

        thread.join()
        self.assertTrue(result)
        self.assertGreaterEqual(os.path.getsize(filepath), 500)

        # Cleanup
        os.remove(filepath)
        os.rmdir(tmpdir)

    def test_network_port_becomes_available(self):
        """Test waiting for a network port to become available."""
        import socket

        def is_port_free(port):
            """Check if a port is free."""
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(("127.0.0.1", port))
                sock.close()
                return True
            except OSError:
                return False

        # Find a port that's likely free
        test_port = 54321

        # Initially the port should be free
        if not is_port_free(test_port):
            self.skipTest(f"Port {test_port} is not available for testing")

        result = wait.wait_for(lambda: is_port_free(test_port), timeout=1.0, step=0.1)
        self.assertTrue(result)

    def test_process_completion_simulation(self):
        """Test waiting for a simulated process to complete."""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        status_file = os.path.join(tmpdir, "process_status.txt")

        # Simulate a process that completes after some time
        def simulated_process():
            time.sleep(0.4)
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("COMPLETED")

        import threading

        thread = threading.Thread(target=simulated_process)
        thread.start()

        # Wait for process completion
        def check_status():
            if not os.path.exists(status_file):
                return False
            with open(status_file, "r", encoding="utf-8") as f:
                return f.read().strip() == "COMPLETED"

        result = wait.wait_for(check_status, timeout=2.0, step=0.1)

        thread.join()
        self.assertTrue(result)

        # Cleanup
        os.remove(status_file)
        os.rmdir(tmpdir)

    def test_environment_variable_appears(self):
        """Test waiting for an environment variable to be set."""

        def set_env_delayed():
            time.sleep(0.3)
            os.environ["TEST_WAIT_VAR"] = "test_value"

        import threading

        thread = threading.Thread(target=set_env_delayed)
        thread.start()

        # Wait for environment variable
        result = wait.wait_for(
            lambda: "TEST_WAIT_VAR" in os.environ, timeout=2.0, step=0.1
        )

        thread.join()
        self.assertTrue(result)
        self.assertEqual(os.environ.get("TEST_WAIT_VAR"), "test_value")

        # Cleanup
        del os.environ["TEST_WAIT_VAR"]

    def test_counter_reaches_value(self):
        """Test waiting for a counter to reach a specific value."""

        class Counter:
            def __init__(self):
                self.value = 0
                self.lock = threading.Lock()

            def increment(self):
                with self.lock:
                    self.value += 1

            def get(self):
                with self.lock:
                    return self.value

        import threading

        counter = Counter()

        # Increment counter in background
        def increment_slowly():
            for _ in range(10):
                time.sleep(0.05)
                counter.increment()

        thread = threading.Thread(target=increment_slowly)
        thread.start()

        # Wait for counter to reach 5
        result = wait.wait_for(lambda: counter.get() >= 5, timeout=2.0, step=0.05)

        thread.join()
        self.assertTrue(result)
        self.assertGreaterEqual(counter.get(), 5)

    def test_multiple_conditions_combined(self):
        """Test waiting for multiple conditions to be satisfied."""
        import tempfile
        import threading

        tmpdir = tempfile.mkdtemp()
        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")

        def create_files():
            time.sleep(0.2)
            with open(file1, "w", encoding="utf-8") as f:
                f.write("content1")
            time.sleep(0.2)
            with open(file2, "w", encoding="utf-8") as f:
                f.write("content2")

        thread = threading.Thread(target=create_files)
        thread.start()

        # Wait for both files to exist
        result = wait.wait_for(
            lambda: os.path.exists(file1) and os.path.exists(file2),
            timeout=2.0,
            step=0.1,
        )

        thread.join()
        self.assertTrue(result)
        self.assertTrue(os.path.exists(file1))
        self.assertTrue(os.path.exists(file2))

        # Cleanup
        os.remove(file1)
        os.remove(file2)
        os.rmdir(tmpdir)

    def test_timeout_in_real_scenario(self):
        """Test that timeout works correctly in real scenario."""
        import tempfile

        tmpdir = tempfile.mkdtemp()
        filepath = os.path.join(tmpdir, "nonexistent.txt")

        # Wait for a file that will never be created
        start = time.time()
        result = wait.wait_for(lambda: os.path.exists(filepath), timeout=0.5, step=0.1)
        elapsed = time.time() - start

        self.assertIsNone(result)
        self.assertGreaterEqual(elapsed, 0.5)
        self.assertLess(elapsed, 0.7)

        # Cleanup
        os.rmdir(tmpdir)

    def test_directory_creation(self):
        """Test waiting for a directory to be created."""
        import tempfile
        import threading

        tmpdir = tempfile.mkdtemp()
        new_dir = os.path.join(tmpdir, "new_directory")

        def create_dir_delayed():
            time.sleep(0.3)
            os.makedirs(new_dir)

        thread = threading.Thread(target=create_dir_delayed)
        thread.start()

        result = wait.wait_for(lambda: os.path.isdir(new_dir), timeout=2.0, step=0.1)

        thread.join()
        self.assertTrue(result)
        self.assertTrue(os.path.isdir(new_dir))

        # Cleanup
        os.rmdir(new_dir)
        os.rmdir(tmpdir)

    def test_file_content_matches(self):
        """Test waiting for file content to match expected value."""
        import tempfile
        import threading

        tmpdir = tempfile.mkdtemp()
        filepath = os.path.join(tmpdir, "content_file.txt")

        def write_content_delayed():
            # Write wrong content first
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("wrong content")
            time.sleep(0.3)
            # Write correct content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("correct content")

        thread = threading.Thread(target=write_content_delayed)
        thread.start()

        def check_content():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read().strip() == "correct content"
            except FileNotFoundError:
                return False

        result = wait.wait_for(check_content, timeout=2.0, step=0.1)

        thread.join()
        self.assertTrue(result)

        # Cleanup
        os.remove(filepath)
        os.rmdir(tmpdir)

    def test_list_accumulation(self):
        """Test waiting for a list to accumulate enough items."""
        import threading

        shared_list = []

        def add_items_slowly():
            for i in range(10):
                time.sleep(0.05)
                shared_list.append(i)

        thread = threading.Thread(target=add_items_slowly)
        thread.start()

        # Wait for list to have at least 5 items
        result = wait.wait_for(lambda: len(shared_list) >= 5, timeout=2.0, step=0.05)

        thread.join()
        self.assertTrue(result)
        self.assertGreaterEqual(len(shared_list), 5)

    def test_dictionary_key_appears(self):
        """Test waiting for a specific key to appear in a dictionary."""
        import threading

        shared_dict = {}

        def add_keys_slowly():
            time.sleep(0.2)
            shared_dict["key1"] = "value1"
            time.sleep(0.2)
            shared_dict["key2"] = "value2"
            time.sleep(0.2)
            shared_dict["target_key"] = "target_value"

        thread = threading.Thread(target=add_keys_slowly)
        thread.start()

        result = wait.wait_for(
            lambda: "target_key" in shared_dict, timeout=2.0, step=0.1
        )

        thread.join()
        self.assertTrue(result)
        self.assertEqual(shared_dict.get("target_key"), "target_value")

    def test_with_complex_condition_function(self):
        """Test wait_for with a complex condition checking function."""
        import tempfile
        import threading

        tmpdir = tempfile.mkdtemp()
        filepath = os.path.join(tmpdir, "numbers.txt")

        def write_numbers():
            with open(filepath, "w", encoding="utf-8") as f:
                for i in range(1, 11):
                    f.write(f"{i}\n")
                    f.flush()
                    time.sleep(0.05)

        thread = threading.Thread(target=write_numbers)
        thread.start()

        def check_sum_exceeds_threshold():
            """Check if sum of numbers in file exceeds 30."""
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    if not lines:
                        return False
                    numbers = [int(line.strip()) for line in lines if line.strip()]
                    return sum(numbers) > 30
            except (FileNotFoundError, ValueError):
                return False

        result = wait.wait_for(check_sum_exceeds_threshold, timeout=2.0, step=0.1)

        thread.join()
        self.assertTrue(result)

        # Cleanup
        os.remove(filepath)
        os.rmdir(tmpdir)

    def test_stress_many_quick_checks(self):
        """Test wait_for can handle many quick successive checks."""
        counter = {"value": 0}

        def increment_counter():
            counter["value"] += 1
            return counter["value"] >= 50

        result = wait.wait_for(increment_counter, timeout=2.0, step=0.001)

        self.assertTrue(result)
        self.assertEqual(counter["value"], 50)


if __name__ == "__main__":
    unittest.main()
