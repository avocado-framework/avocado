import os
import tempfile
import unittest

from avocado.utils import genio

from .. import setup_avocado_loggers, temp_dir_prefix


setup_avocado_loggers()


class TestGenio(unittest.TestCase):
    def test_check_pattern_in_directory(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        tempdirname = tempfile.mkdtemp(prefix=prefix)
        with self.assertRaises(genio.GenIOError):
            genio.is_pattern_in_file(tempdirname, 'something')
        os.rmdir(tempdirname)

    def test_check_simple_pattern_in_file_successfully(self):
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write('Hello World')
            temp_file.seek(0)
            self.assertTrue(genio.is_pattern_in_file(temp_file.name, 'Hello'))

    def test_check_pattern_in_file_successfully(self):
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write('123')
            temp_file.seek(0)
            self.assertTrue(genio.is_pattern_in_file(temp_file.name, r'\d{3}'))

    def test_check_pattern_in_file_unsuccessfully(self):
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write('123')
            temp_file.seek(0)
            self.assertFalse(genio.is_pattern_in_file(temp_file.name, r'\D{3}'))
