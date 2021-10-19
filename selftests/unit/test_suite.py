import tempfile
import unittest.mock

from avocado.core.suite import TestSuite
from avocado.utils import path as utils_path
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class TestSuiteTest(unittest.TestCase):

    def setUp(self):
        self.suite = None
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @staticmethod
    def _find_simple_test_candidates(candidates=None):
        if candidates is None:
            candidates = ['true']
        found = []
        for candidate in candidates:
            try:
                found.append(utils_path.find_command(candidate))
            except utils_path.CmdNotFoundError:
                pass
        return found

    def test_custom_suite(self):
        """Custom suites should assume custom tests.

        When using custom suites (from constructor) we are assuming no
        magic, no tests should be created from resolver.references.
        """
        tests = self._find_simple_test_candidates()
        config = {'run.results_dir': self.tmpdir.name,
                  'core.show': ['none'],
                  'resolver.references': tests}

        self.suite = TestSuite(name='foo', config=config)
        self.assertEqual(0, self.suite.size)

    def test_automatic_suite(self):
        """Automatic suites should create tests.

        When using automatic suites we are assuming magic,
        and, tests should be created from resolver.references.
        """
        tests = self._find_simple_test_candidates()
        config = {'run.results_dir': self.tmpdir.name,
                  'core.show': ['none'],
                  'resolver.references': tests}

        self.suite = TestSuite.from_config(config=config)
        self.assertEqual(1, self.suite.size)

    def test_config_extend_manual(self):
        """Test extends config from job when using manual method."""
        tests = self._find_simple_test_candidates()
        job_config = {'run.results_dir': self.tmpdir.name,
                      'core.show': ['none']}
        suite_config = {'resolver.references': tests}
        self.suite = TestSuite(name='foo',
                               config=suite_config,
                               job_config=job_config)
        self.assertEqual(self.suite.config.get('core.show'), ['none'])

    def test_config_extend_automatic(self):
        """Test extends config from job when using automatic method."""
        tests = self._find_simple_test_candidates()
        job_config = {'run.results_dir': self.tmpdir.name,
                      'core.show': ['none']}
        suite_config = {'resolver.references': tests}
        self.suite = TestSuite.from_config(config=suite_config,
                                           job_config=job_config)
        self.assertEqual(self.suite.config.get('core.show'), ['none'])

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
