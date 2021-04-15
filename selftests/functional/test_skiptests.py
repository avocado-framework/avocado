import json
import os
import unittest

from avocado.core import exit_codes
from avocado.utils import genio, process, script
from selftests.utils import AVOCADO, TestCaseTmpDir

AVOCADO_TEST_SKIP_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

class AvocadoSkipTests(avocado.Test):

    TRUE_CONDITION = True
    FALSE_CONDITION = False

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

    @avocado.skipIf(lambda x: x.TRUE_CONDITION,
                    'Skipped due to the True condition')
    def test4(self):
        self.log.info('test executed')

    @avocado.skipUnless(lambda x: x.FALSE_CONDITION,
                        'Skipped due to the False condition')
    def test5(self):
        self.log.info('test executed')

    @avocado.skipIf(lambda x: x.FALSE_CONDITION,
                    'skipIf with False condition should never happen')
    def test6(self):
        # test "runs", because skipIf with False condition runs a test
        self.cancel('ran, but was canceled')
        self.log.info('test executed')  # should never get here

    @avocado.skipUnless(lambda x: x.TRUE_CONDITION,
                        'skipUnless with True condition should never happen')
    def test7(self):
        # test "runs", because skipUnless with True condition runs a test
        self.cancel('ran, but was canceled')
        self.log.info('test executed')  # should never get here

    def tearDown(self):
        self.log.info('teardown executed')
"""


AVOCADO_TEST_NOT_SKIP_DECORATORS = """
import avocado
from lib_skip_decorators import check_condition

class AvocadoSkipTests(avocado.Test):

    TRUE_CONDITION = True
    FALSE_CONDITION = False

    def setUp(self):
        self.log.info('setup executed')

    @avocado.skipIf(False,
                    'skipIf with False condition, should not happen')
    def test1(self):
        self.log.info('test executed')

    @avocado.skipUnless(True,
                        'SkipUnless with True condition, should not happen')
    def test2(self):
        self.log.info('test executed')

    @avocado.skipIf(lambda x: x.FALSE_CONDITION,
                    'skipIf with False condition, should not happen')
    def test3(self):
        self.log.info('test executed')

    @avocado.skipUnless(lambda x: x.TRUE_CONDITION,
                        'skipUnless with True condition, should not happen')
    def test4(self):
        self.log.info('test executed')

    @avocado.skipIf(None,
                    'skipIf with None condition, should not happen')
    def test5(self):
        self.log.info('test executed')

    @avocado.skipIf(lambda x: None,
                    'skipIf with None condition, should not happen')
    def test6(self):
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


class Base(TestCaseTmpDir):

    FILE_NAME_CONTENT_MAP = {}
    SCRIPT_TO_EXEC = 'script_to_exec.py'

    def setUp(self):
        super(Base, self).setUp()
        for name, content in self.FILE_NAME_CONTENT_MAP.items():
            self._create_tmp_file(name, content)

    def _create_tmp_file(self, name, content):
        scr_obj = script.Script(os.path.join(self.tmpdir.name, name), content)
        scr_obj.save()
        return scr_obj

    def _get_json_result(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % os.path.join(self.tmpdir.name, self.SCRIPT_TO_EXEC),
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_ALL_OK)
        json_results = json.loads(result.stdout_text)
        return json_results

    def check_skips_and_content(self, number_of_skips):
        json_results = self._get_json_result()
        self.check_status_occurrences(json_results, skip=number_of_skips)
        self.check_content(json_results)

    def check_status(self, **kwargs):
        json_results = self._get_json_result()
        self.check_status_occurrences(json_results, **kwargs)

    def check_status_occurrences(self, json_results, **kwargs):
        for status, number_of_occurrences in kwargs.items():
            self.assertEqual(json_results[status], number_of_occurrences)

    def check_content(self, json_results):
        debuglog = json_results['debuglog']
        debuglog_contents = genio.read_file(debuglog)
        self.assertFalse('setup executed' in debuglog_contents)
        self.assertFalse('test executed' in debuglog_contents)
        self.assertFalse('teardown executed' in debuglog_contents)


class Skip(Base):

    FILE_NAME_CONTENT_MAP = {
        'lib_skip_decorators.py': AVOCADO_TEST_SKIP_LIB,
        'script_to_exec.py': AVOCADO_TEST_SKIP_DECORATORS
    }

    def test_skip_decorators(self):
        self.check_status(skip=5, cancel=2)


class NotSkip(Base):

    FILE_NAME_CONTENT_MAP = {
        'lib_skip_decorators.py': AVOCADO_TEST_SKIP_LIB,
        'script_to_exec.py': AVOCADO_TEST_NOT_SKIP_DECORATORS
    }

    def test(self):
        self.check_status(**{'pass': 6, 'skip': 0})


class SkipClass(Base):

    FILE_NAME_CONTENT_MAP = {
        'lib_skip_decorators.py': AVOCADO_TEST_SKIP_LIB,
        'script_to_exec.py': AVOCADO_TEST_SKIP_CLASS_DECORATORS
    }

    def test_skip_class_decorators(self):
        self.check_skips_and_content(3)


class SkipIfClass(Base):

    FILE_NAME_CONTENT_MAP = {
        'lib_skip_decorators.py': AVOCADO_TEST_SKIP_LIB,
        'script_to_exec.py': AVOCADO_TEST_SKIP_IF_CLASS_DECORATORS
    }

    def test_skipIf_class_decorators(self):
        self.check_status(**{'skip': 3, 'pass': 3})


class SkipUnlessClass(Base):

    FILE_NAME_CONTENT_MAP = {
        'lib_skip_decorators.py': AVOCADO_TEST_SKIP_LIB,
        'script_to_exec.py': AVOCADO_TEST_SKIP_UNLESS_CLASS_DECORATORS
    }

    def test_skipUnless_class_decorators(self):
        self.check_status(**{'skip': 3, 'pass': 3})


class SkipSetup(Base):

    FILE_NAME_CONTENT_MAP = {
        'script_to_exec.py': AVOCADO_SKIP_DECORATOR_SETUP
    }

    def test_skip_setup(self):
        self.check_status(skip=1)


class SkipTearDown(Base):

    FILE_NAME_CONTENT_MAP = {
        'script_to_exec.py': AVOCADO_SKIP_DECORATOR_TEARDOWN
    }

    def _get_json_result(self):
        cmd_line = [AVOCADO,
                    'run',
                    '--disable-sysinfo',
                    '--job-results-dir',
                    '%s' % self.tmpdir.name,
                    '%s' % os.path.join(self.tmpdir.name, self.SCRIPT_TO_EXEC),
                    '--json -']
        result = process.run(' '.join(cmd_line), ignore_status=True)
        self.assertEqual(result.exit_status, exit_codes.AVOCADO_TESTS_FAIL)
        json_results = json.loads(result.stdout_text)
        return json_results

    def test_skip_teardown(self):
        self.check_status(errors=1)


if __name__ == '__main__':
    unittest.main()
