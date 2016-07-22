import argparse
import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import parser
from avocado.core import exceptions


class FileOrStdoutActionTest(unittest.TestCase):

    def setUp(self):
        self.parser = argparse.ArgumentParser(prog='avocado')
        self.parser.add_argument('--xunit',
                                 action=parser.FileOrStdoutAction)
        self.parser.add_argument('--json',
                                 action=parser.FileOrStdoutAction)

    def test_multiple_files(self):
        self.parser.parse_args(['--xunit=results.xml',
                                '--json=results.json'])

    def test_one_file_and_stdout(self):
        self.parser.parse_args(['--xunit=-',
                                '--json=results.json'])

    def test_multiple_stdout_raises(self):
        self.assertRaises(exceptions.OptionValidationError,
                          self.parser.parse_args,
                          ['--xunit=-', '--json=-'])


if __name__ == '__main__':
    unittest.main()
