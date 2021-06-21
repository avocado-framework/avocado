import os
import sys
import unittest.mock

from avocado.core.safeloader.core import find_avocado_tests
from selftests.utils import BASEDIR


class Caveats(unittest.TestCase):

    def test_no_multilevel_base_class(self):
        caveat_dir = os.path.join(BASEDIR, 'selftests', '.data', 'safeloader',
                                  'caveat_multilevel')
        success = os.path.join(caveat_dir, 'success.py')
        failure = os.path.join(caveat_dir, 'failure.py')
        sys_path = sys.path + [caveat_dir]
        with unittest.mock.patch('sys.path', sys_path):
            self.assertEqual(find_avocado_tests(success)[0],
                             {'Test': [('test', {}, [])]})
            self.assertEqual(find_avocado_tests(failure)[0], {})
