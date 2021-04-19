import stat
import unittest

from avocado.utils import process, script
from selftests.utils import AVOCADO

# Use the same definitions from loader to make sure the behavior
# is also the same
from .test_loader import AVOCADO_TEST_OK as AVOCADO_INSTRUMENTED_TEST
from .test_loader import SIMPLE_TEST as EXEC_TEST


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
            cmd_line = ('%s --verbose list --resolver %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertIn('exec-test: 1', result.stdout_text)

    def test_not_exec_test(self):
        name = 'executable-test'
        with script.TemporaryScript(name, EXEC_TEST,
                                    name, self.MODE_0664) as test_file:
            cmd_line = ('%s list --resolver %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertNotIn('exec-test ', result.stdout_text)

    def test_avocado_instrumented(self):
        name = 'passtest.py'
        with script.TemporaryScript(name, AVOCADO_INSTRUMENTED_TEST,
                                    name, self.MODE_0664) as test_file:
            cmd_line = ('%s --verbose list --resolver %s' % (AVOCADO, test_file.path))
            result = process.run(cmd_line)
        self.assertIn('passtest.py:PassTest.test', result.stdout_text)
        self.assertIn('avocado-instrumented: 1', result.stdout_text)


if __name__ == '__main__':
    unittest.main()
