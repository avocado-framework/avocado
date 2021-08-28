import os
import unittest

from avocado.core import exit_codes
from avocado.utils import process
from selftests.utils import AVOCADO, BASEDIR


class List(unittest.TestCase):

    list_command = 'list --loader'

    def test_list_filter_by_tags(self):
        examples_dir = os.path.join(BASEDIR, 'examples', 'tests')
        cmd_line = "%s --verbose %s -t fast -- %s" % (AVOCADO,
                                                      self.list_command,
                                                      examples_dir)
        result = process.run(cmd_line)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK,
                         "Avocado did not return rc %d:\n%s"
                         % (exit_codes.AVOCADO_ALL_OK, result))
        stdout_lines = result.stdout_text.splitlines()
        self.assertIn("TEST TYPES SUMMARY", stdout_lines)
        self.assertIn("instrumented: 2", stdout_lines)
        self.assertIn("TEST TAGS SUMMARY", stdout_lines)
        self.assertIn("fast: 2", stdout_lines)
