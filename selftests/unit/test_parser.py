import argparse
import unittest

from avocado.core import parser


class SilentParser(argparse.ArgumentParser):
    def __init__(self):
        super(SilentParser, self).__init__(prog='avocado')

    def error(self, message):
        """
        Don't sys.exit, but only raise RuntimeError
        """
        raise RuntimeError(message)


class FileOrStdoutActionTest(unittest.TestCase):

    def setUp(self):
        self.parser = SilentParser()
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
        self.assertRaises(RuntimeError,
                          self.parser.parse_args,
                          ['--xunit=-', '--json=-'])


if __name__ == '__main__':
    unittest.main()
