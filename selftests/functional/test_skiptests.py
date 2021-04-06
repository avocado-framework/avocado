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

    def _create_tmp_file(self, name, content):
        scr_obj = script.Script(os.path.join(self.tmpdir.name, name), content)
        scr_obj.save()
        return scr_obj


class Skip(Base):

    def setUp(self):
        super(Skip, self).setUp()
        self.test_lib = self._create_tmp_file('lib_skip_decorators.py',
                                              AVOCADO_TEST_SKIP_LIB)
        self.test_module = self._create_tmp_file('test_skip_decorators.py',
                                                 AVOCADO_TEST_SKIP_DECORATORS)

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
        self.assertEqual(json_results['skip'], 5)
        debuglog_contents = genio.read_file(debuglog)
        self.assertFalse('setup executed' in debuglog_contents)
        self.assertFalse('test executed' in debuglog_contents)
        self.assertFalse('teardown executed' in debuglog_contents)


class SkipClass(Base):

    def setUp(self):
        super(SkipClass, self).setUp()
        self.test_lib = self._create_tmp_file('lib_skip_decorators.py',
                                              AVOCADO_TEST_SKIP_LIB)
        self.class_module = self._create_tmp_file(
            'test_skip_class_decorators.py',
            AVOCADO_TEST_SKIP_CLASS_DECORATORS)

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


class SkipIfClass(Base):

    def setUp(self):
        super(SkipIfClass, self).setUp()
        self.test_lib = self._create_tmp_file('lib_skip_decorators.py',
                                              AVOCADO_TEST_SKIP_LIB)
        self.class_if_module = self._create_tmp_file(
            'test_skip_if_class_decorators.py',
            AVOCADO_TEST_SKIP_IF_CLASS_DECORATORS)

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


class SkipUnlessClass(Base):

    def setUp(self):
        super(SkipUnlessClass, self).setUp()
        self.test_lib = self._create_tmp_file('lib_skip_decorators.py',
                                              AVOCADO_TEST_SKIP_LIB)
        self.class_unless_module = self._create_tmp_file(
            'test_skip_unless_class_decorators.py',
            AVOCADO_TEST_SKIP_UNLESS_CLASS_DECORATORS)

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


class SkipSetup(Base):

    def setUp(self):
        super(SkipSetup, self).setUp()
        self.skip_setup = self._create_tmp_file('test_skip_decorator_setup.py',
                                                AVOCADO_SKIP_DECORATOR_SETUP)

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


class SkipTearDown(Base):

    def setUp(self):
        super(SkipTearDown, self).setUp()
        self.bad_teardown = self._create_tmp_file(
            'test_skip_decorator_teardown.py',
            AVOCADO_SKIP_DECORATOR_TEARDOWN)

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
