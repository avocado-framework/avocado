import os
import shutil
import stat
import tempfile
import unittest

from avocado.utils import script


class TestScript(unittest.TestCase):
    """Test cases for the Script class."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_test_script_")
        self.script_path = os.path.join(self.tmpdir, "test_script.sh")
        self.script_content = "#!/bin/bash\necho 'Hello World'\n"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_save_and_read(self):
        """Test Script save method and content persistence with default mode."""
        scpt = script.Script(self.script_path, self.script_content)
        result = scpt.save()
        self.assertTrue(result)
        self.assertTrue(scpt.stored)
        self.assertTrue(os.path.exists(self.script_path))
        with open(self.script_path, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.script_content)
        # Verify default mode is applied (0o775)
        file_stat = os.stat(self.script_path)
        self.assertEqual(stat.S_IMODE(file_stat.st_mode), script.DEFAULT_MODE)

    def test_custom_mode(self):
        """Test Script with custom file mode (READ_ONLY_MODE)."""
        scpt = script.Script(
            self.script_path, self.script_content, mode=script.READ_ONLY_MODE
        )
        scpt.save()
        file_stat = os.stat(self.script_path)
        self.assertEqual(stat.S_IMODE(file_stat.st_mode), script.READ_ONLY_MODE)

    def test_save_creates_directory(self):
        """Test Script save creates nested parent directories if needed."""
        nested_path = os.path.join(self.tmpdir, "subdir", "nested", "test_script.sh")
        scpt = script.Script(nested_path, self.script_content)
        scpt.save()
        self.assertTrue(os.path.exists(nested_path))

    def test_remove(self):
        """Test Script remove method for existing and non-existent files."""
        scpt = script.Script(self.script_path, self.script_content)
        # Remove non-existent file returns False
        result = scpt.remove()
        self.assertFalse(result)
        # Save then remove returns True
        scpt.save()
        self.assertTrue(os.path.exists(self.script_path))
        result = scpt.remove()
        self.assertTrue(result)
        self.assertFalse(scpt.stored)
        self.assertFalse(os.path.exists(self.script_path))

    def test_context_manager(self):
        """Test Script as context manager with automatic cleanup."""
        with script.Script(self.script_path, self.script_content) as scpt:
            self.assertTrue(os.path.exists(scpt.path))
            self.assertTrue(scpt.stored)
        # File should be cleaned up after context exit
        self.assertFalse(os.path.exists(self.script_path))

    def test_binary_content(self):
        """Test Script with binary content using binary write mode."""
        binary_content = b"\x00\x01\x02\x03\xff\xfe"
        binary_path = os.path.join(self.tmpdir, "binary_script")
        scpt = script.Script(binary_path, binary_content, open_mode="wb")
        scpt.save()
        with open(binary_path, "rb") as f:
            self.assertEqual(f.read(), binary_content)

    def test_string_representation(self):
        """Test Script __str__ and __repr__ methods."""
        scpt = script.Script(self.script_path, self.script_content)
        # __str__ returns path
        self.assertEqual(str(scpt), self.script_path)
        # __repr__ contains class name, path, and stored status
        repr_str = repr(scpt)
        self.assertIn("Script", repr_str)
        self.assertIn(self.script_path, repr_str)
        self.assertIn("stored=False", repr_str)


class TestTemporaryScript(unittest.TestCase):
    """Test cases for the TemporaryScript class."""

    def test_context_manager_cleanup(self):
        """Test TemporaryScript context manager with automatic directory cleanup."""
        name = "test_script.sh"
        content = "#!/bin/bash\necho 'test'\n"
        with script.TemporaryScript(name, content) as scpt:
            self.assertTrue(os.path.exists(scpt.path))
            self.assertTrue(scpt.path.endswith(name))
            tmpdir = os.path.dirname(scpt.path)
            # Verify content
            with open(scpt.path, encoding="utf-8") as f:
                self.assertEqual(f.read(), content)
        # Entire directory should be cleaned up
        self.assertFalse(os.path.exists(tmpdir))

    def test_custom_prefix(self):
        """Test TemporaryScript with custom directory prefix."""
        name = "test_script.sh"
        content = "test content"
        custom_prefix = "my_custom_prefix_"
        with script.TemporaryScript(name, content, prefix=custom_prefix) as scpt:
            tmpdir = os.path.dirname(scpt.path)
            self.assertTrue(os.path.basename(tmpdir).startswith(custom_prefix))

    def test_garbage_collection_cleanup(self):
        """Test TemporaryScript cleanup on garbage collection via __del__."""
        name = "test_script.sh"
        content = "test content"
        scpt = script.TemporaryScript(name, content)
        scpt.save()
        tmpdir = os.path.dirname(scpt.path)
        self.assertTrue(os.path.exists(tmpdir))
        # Trigger garbage collection by deleting reference
        del scpt
        # Directory should be automatically cleaned up
        self.assertFalse(os.path.exists(tmpdir))

    def test_unicode_name(self):
        """Test TemporaryScript with unicode filename."""
        name = "\u00e1 \u00e9 \u00ed \u00f3 \u00fa"
        content = "a e i o u"
        with script.TemporaryScript(name, content) as temp_script:
            self.assertTrue(os.path.exists(temp_script.path))
            with open(temp_script.path, encoding="utf-8") as f:
                self.assertEqual(content, f.read())

    def test_unicode_content(self):
        """Test TemporaryScript with unicode content (CJK characters)."""
        name = "unicode_test.txt"
        content = "\u4e2d\u6587 \u65e5\u672c\u8a9e \ud55c\uad6d\uc5b4"
        with script.TemporaryScript(name, content) as scpt:
            with open(scpt.path, encoding="utf-8") as f:
                self.assertEqual(f.read(), content)


class TestHelperFunctions(unittest.TestCase):
    """Test cases for helper functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_test_helpers_")

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)

    def test_make_script(self):
        """Test make_script function creates and returns script path."""
        path = os.path.join(self.tmpdir, "test_script.sh")
        content = "#!/bin/bash\necho 'test'\n"
        result_path = script.make_script(path, content)
        self.assertEqual(result_path, path)
        self.assertTrue(os.path.exists(path))
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), content)

    def test_make_temp_script(self):
        """Test make_temp_script function returns path and creates temporary script."""
        name = "temp_test.sh"
        content = "#!/bin/bash\necho 'temp'\n"
        result_path = script.make_temp_script(name, content)
        # Function returns a path that ends with the script name
        self.assertTrue(result_path.endswith(name))
        # Note: The TemporaryScript object is garbage collected after the function
        # returns, so the file may not exist anymore. This tests the function
        # signature and return value, not file persistence.


if __name__ == "__main__":
    unittest.main()
