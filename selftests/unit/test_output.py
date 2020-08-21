import sys
import unittest.mock

from avocado.core import output
from avocado.utils import path as utils_path


class TestStdOutput(unittest.TestCase):

    def setUp(self):
        """Preserve sys.std{out,err} so we can restore them in tearDown"""
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def tearDown(self):
        sys.stdout = self.stdout
        sys.stderr = self.stderr

    def test_paginator_not_available(self):
        """Check that without paginator command we proceed without changes"""
        std = output.StdOutput()
        with unittest.mock.patch('avocado.utils.path.find_command',
                                 side_effect=utils_path.CmdNotFoundError('just',
                                                                         ['mocking'])):
            std.enable_paginator()
        self.assertEqual(self.stdout, sys.stdout)
        self.assertEqual(self.stderr, sys.stderr)


if __name__ == '__main__':
    unittest.main()
