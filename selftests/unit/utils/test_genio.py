import os
import random
import string
import tempfile
import unittest

from avocado.utils import genio
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class TestGenio(unittest.TestCase):
    def test_check_pattern_in_directory(self):
        prefix = temp_dir_prefix(self)
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

    def test_are_files_equal(self):
        file_1 = tempfile.NamedTemporaryFile(mode='w')
        file_2 = tempfile.NamedTemporaryFile(mode='w')
        for _ in range(100000):
            line = ''.join(random.choice(string.ascii_letters + string.digits
                                         + '\n'))
            file_1.write(line)
            file_2.write(line)
        self.assertTrue(genio.are_files_equal(file_1.name, file_2.name))
