"""Functional tests for the script module."""

import os
import shutil
import subprocess
import tempfile
import unittest

from avocado.utils import script


class TestScriptExecution(unittest.TestCase):
    """Functional tests for script execution scenarios."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_func_test_script_")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_script_creation_and_execution(self):
        """Test that created scripts are executable with correct permissions."""
        script_path = os.path.join(self.tmpdir, "test.sh")
        script_content = "#!/bin/bash\necho 'Avocado test'\nexit 0\n"
        scpt = script.Script(script_path, script_content)
        scpt.save()

        # Verify file was created with executable permissions
        self.assertTrue(os.path.exists(script_path))
        file_stat = os.stat(script_path)
        # Check that owner execute bit is set (part of 0775)
        self.assertTrue(file_stat.st_mode & 0o100)

        # Verify script can actually be executed
        result = subprocess.run(
            [script_path], capture_output=True, text=True, check=True
        )
        self.assertIn("Avocado test", result.stdout)
        self.assertEqual(result.returncode, 0)

        # Clean up
        scpt.remove()

    def test_temporary_script_lifecycle(self):
        """Test TemporaryScript with context manager and execution."""
        script_name = "lifecycle_test.sh"
        script_content = "#!/bin/bash\necho 'Temporary script'\nexit 0\n"

        # Use context manager
        with script.TemporaryScript(script_name, script_content) as scpt:
            # Verify file exists in a temporary directory
            self.assertTrue(os.path.exists(scpt.path))
            tmpdir = os.path.dirname(scpt.path)
            self.assertTrue(tmpdir.startswith("/tmp") or tmpdir.startswith("/var"))

            # Verify script can be executed
            result = subprocess.run(
                [scpt.path], capture_output=True, text=True, check=True
            )
            self.assertIn("Temporary script", result.stdout)

        # Verify entire temporary directory was cleaned up
        self.assertFalse(os.path.exists(tmpdir))

    def test_multiple_concurrent_scripts(self):
        """Test creating and managing multiple TemporaryScript instances."""
        scripts = []
        script_names = ["script1.sh", "script2.sh", "script3.sh"]

        # Create multiple scripts concurrently
        for name in script_names:
            content = f'#!/bin/bash\necho "{name}"\n'
            scpt = script.TemporaryScript(name, content)
            scpt.save()
            scripts.append(scpt)

        # Verify all exist and are in different directories
        paths = [scpt.path for scpt in scripts]
        dirs = [os.path.dirname(p) for p in paths]
        # Each should be in its own temp directory
        self.assertEqual(len(dirs), len(set(dirs)))
        for scpt in scripts:
            self.assertTrue(os.path.exists(scpt.path))

        # Verify each can be executed independently
        for i, scpt in enumerate(scripts):
            result = subprocess.run(
                [scpt.path], capture_output=True, text=True, check=True
            )
            self.assertIn(script_names[i], result.stdout)

        # Clean up
        for scpt in scripts:
            tmpdir = os.path.dirname(scpt.path)
            scpt.remove()
            self.assertFalse(os.path.exists(tmpdir))


if __name__ == "__main__":
    unittest.main()
