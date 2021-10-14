import os
import stat
import unittest

from avocado.utils import process, script
# Use the same definitions from loader to make sure the behavior
# is also the same
from selftests.functional.test_loader import \
    AVOCADO_TEST_OK as AVOCADO_INSTRUMENTED_TEST
from selftests.functional.test_loader import SIMPLE_TEST as EXEC_TEST
from selftests.utils import AVOCADO, BASEDIR


class ResolverFunctional(unittest.TestCase):

    MODE_0664 = (stat.S_IRUSR | stat.S_IWUSR |
                 stat.S_IRGRP | stat.S_IWGRP |
                 stat.S_IROTH)

    MODE_0775 = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def test_exec_test(self):
        name = 'executable-test'
        with script.TemporaryScript(name, EXEC_TEST,
                                    name, self.MODE_0775) as test_file:
            cmd_line = ('%s --verbose list %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertIn('exec-test: 1', result.stdout_text)

    def test_not_exec_test(self):
        name = 'executable-test'
        with script.TemporaryScript(name, EXEC_TEST,
                                    name, self.MODE_0664) as test_file:
            cmd_line = ('%s list %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertNotIn('exec-test ', result.stdout_text)

    def test_avocado_instrumented(self):
        name = 'passtest.py'
        with script.TemporaryScript(name, AVOCADO_INSTRUMENTED_TEST,
                                    name, self.MODE_0664) as test_file:
            cmd_line = ('%s --verbose list %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertIn('passtest.py:PassTest.test', result.stdout_text)
        self.assertIn('avocado-instrumented: 1', result.stdout_text)

    def test_property(self):
        test_path = os.path.join(BASEDIR, 'examples', 'tests', 'property.py')
        cmd_line = ('%s --verbose list %s' % (AVOCADO, test_path))
        result = process.run(cmd_line)
        self.assertIn('examples/tests/property.py:Property.test',
                      result.stdout_text)
        self.assertIn('avocado-instrumented: 1', result.stdout_text)

    def test_python_unittest_first(self):
        """Tests that avocado.Test based tests are found as python-unittest.

        This is valid because of avocado.Test's unittest.TestCase
        inheritance and compatibility.
        """
        config = "[plugins.resolver]\norder = ['python-unittest',]\n"
        with script.TemporaryScript('config', config) as config_path:
            test_path = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
            cmd_line = ('%s --config %s --verbose list %s' % (AVOCADO,
                                                              config_path.path,
                                                              test_path))
            result = process.run(cmd_line)
        self.assertIn('python-unittest: 1', result.stdout_text)

    def test_avocado_and_python_unittest_disabled(self):
        """Tests that avocado.Test based tests are not found.

        If both python-unittest and avocado-instrumented resolver are disabled,
        avocado.Test based tests should not be resolved at all.
        """
        config = ("[plugins]\ndisable = ['resolver.python-unittest', "
                  "'resolver.avocado-instrumented']\n")
        with script.TemporaryScript('config', config) as config_path:
            test_path = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
            cmd_line = ('%s --config %s --verbose list %s' % (AVOCADO,
                                                              config_path.path,
                                                              test_path))
            result = process.run(cmd_line)
        lines = result.stdout_text.splitlines()
        self.assertEqual(lines[-2], "TEST TYPES SUMMARY")
        self.assertEqual(lines[-1], "==================")

    def test_recursive_by_default(self):
        test_path = os.path.join(BASEDIR, 'examples', 'tests', 'skip_conditional.py')
        cmd_line = ('%s --verbose list %s' % (AVOCADO, test_path))
        result = process.run(cmd_line)
        lines = result.stdout_text.splitlines()
        # two random tests that should be among the 10 tests found
        self.assertIn('examples/tests/skip_conditional.py:BareMetal.test_specific',
                      lines[1])
        self.assertIn('examples/tests/skip_conditional.py:NonBareMetal.test_bare_metal',
                      lines[7])
        self.assertEqual('avocado-instrumented: 10', lines[-1])


if __name__ == '__main__':
    unittest.main()
