import json
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import genio, process, script

from .. import AVOCADO, TestCaseTmpDir

AVOCADO_TEST_SKIP_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

class AvocadoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    @avocado.skip('Test skipped')
    def test1(self):
        self.log.info('test executed')

    @avocado.skipIf(check_condition(True),
                    'Skipped due to the True condition')
    def test2(self):
        self.log.info('test executed')

    @avocado.skipUnless(check_condition(False),
                        'Skipped due to the False condition')
    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')
"""

AVOCADO_TEST_SKIP_CLASS_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition
@avocado.skip('Test skipped')
class AvocadoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    def test1(self):
        self.log.info('test executed')

    def test2(self):
        self.log.info('test executed')

    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')

"""


AVOCADO_TEST_SKIP_IF_CLASS_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition
@avocado.skipIf(check_condition(True),
                    'Skipped due to the True condition')
class AvocadoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    def test1(self):
        self.log.info('test executed')

    def test2(self):
        self.log.info('test executed')

    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')

@avocado.skipIf(check_condition(False),
                    'Skipped due to the True condition')
class AvocadoNoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    def test1(self):
        self.log.info('test executed')

    def test2(self):
        self.log.info('test executed')

    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')
"""


AVOCADO_TEST_SKIP_UNLESS_CLASS_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

@avocado.skipUnless(check_condition(False),
                    'Skipped due to the True condition')
class AvocadoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    def test1(self):
        self.log.info('test executed')

    def test2(self):
        self.log.info('test executed')

    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')

@avocado.skipUnless(check_condition(True),
                    'Skipped due to the True condition')
class AvocadoNoSkipTests(avocado.Test):

    def setUp(self):
        self.log.info('setup executed')

    def test1(self):
        self.log.info('test executed')

    def test2(self):
        self.log.info('test executed')

    def test3(self):
        self.log.info('test executed')

    def tearDown(self):
        self.log.info('teardown executed')
"""


AVOCADO_TEST_SKIP_LIB = """
def check_condition(condition):
    if condition:
        return True
    return False
"""


AVOCADO_SKIP_DECORATOR_SETUP = """
import avocado

class AvocadoSkipTests(avocado.Test):

    @avocado.skip('Test skipped')
    def setUp(self):
        pass

    def test1(self):
        pass
"""


AVOCADO_SKIP_DECORATOR_TEARDOWN = """
import avocado

class AvocadoSkipTests(avocado.Test):

    def test1(self):
        pass

    @avocado.skip('Test skipped')
    def tearDown(self):
        pass
"""


class TestSkipDecorators(TestCaseTmpDir):

    def setUp(self):
        super(TestSkipDecorators, self).setUp()
        test_path = os.path.join(self.tmpdir.name, 'test_skip_decorators.py')
        self.test_module = script.Script(test_path,
                                         AVOCADO_TEST_SKIP_DECORATORS)
        self.test_module.save()

        class_path = os.path.join(self.tmpdir.name,
                                  'test_skip_class_decorators.py')
        self.class_module = script.Script(class_path,
                                          AVOCADO_TEST_SKIP_CLASS_DECORATORS)
        self.class_module.save()

        class_if_path = os.path.join(self.tmpdir.name,
                                     'test_skip_if_class_decorators.py')
        self.class_if_module = script.Script(class_if_path,
                                             AVOCADO_TEST_SKIP_IF_CLASS_DECORATORS)
        self.class_if_module.save()

        class_unless_path = os.path.join(self.tmpdir.name,
                                         'test_skip_unless_class_decorators.py')
        self.class_unless_module = script.Script(class_unless_path,
                                                 AVOCADO_TEST_SKIP_UNLESS_CLASS_DECORATORS)
        self.class_unless_module.save()

        lib_path = os.path.join(self.tmpdir.name, 'lib_skip_decorators.py')
        self.test_lib = script.Script(lib_path, AVOCADO_TEST_SKIP_LIB)
        self.test_lib.save()

        skip_setup_path = os.path.join(self.tmpdir.name,
                                       'test_skip_decorator_setup.py')
        self.skip_setup = script.Script(skip_setup_path,
                                        AVOCADO_SKIP_DECORATOR_SETUP)
        self.skip_setup.save()

        bad_teardown_path = os.path.join(self.tmpdir.name,
                                         'test_skip_decorator_teardown.py')
        self.bad_teardown = script.Script(bad_teardown_path,
                                          AVOCADO_SKIP_DECORATOR_TEARDOWN)
        self.bad_teardown.save()

    def test_skip_decorators(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.test_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)
        debuglog = json_results['debuglog']

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['skip'], 3)
        debuglog_contents = genio.read_file(debuglog)
        self.assertFalse('setup executed' in debuglog_contents)
        self.assertFalse('test executed' in debuglog_contents)
        self.assertFalse('teardown executed' in debuglog_contents)

    def test_skip_class_decorators(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.class_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)
        debuglog = json_results['debuglog']

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['skip'], 3)
        debuglog_contents = genio.read_file(debuglog)
        self.assertFalse('setup executed' in debuglog_contents)
        self.assertFalse('test executed' in debuglog_contents)
        self.assertFalse('teardown executed' in debuglog_contents)

    def test_skipIf_class_decorators(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.class_if_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['skip'], 3)
        self.assertEqual(json_results['pass'], 3)

    def test_skipUnless_class_decorators(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.class_unless_module,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)

        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['skip'], 3)
        self.assertEqual(json_results['pass'], 3)

    def test_skip_setup(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.skip_setup,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        self.assertEqual(json_results['skip'], 1)

    def test_skip_teardown(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % self.bad_teardown,
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        json_results = json.loads(result.stdout_text)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
        self.assertEqual(json_results['errors'], 1)


if __name__ == '__main__':
    unittest.main()
