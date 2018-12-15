import os
import shutil
import stat
import tempfile
import unittest

from avocado.core import test
from avocado.core import loader
from avocado.utils import script

from .. import setup_avocado_loggers


setup_avocado_loggers()


#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)


AVOCADO_TEST_OK = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_OK_DISABLED = """#!/usr/bin/env python
from avocado import Test
from avocado import main

class PassTest(Test):
    '''
    Instrumented test, but disabled using an Avocado docstring tag
    :avocado: disable
    '''
    def test(self):
        pass

if __name__ == "__main__":
    main()
"""

AVOCADO_TEST_TAGS = """#!/usr/bin/env python
from avocado import Test
from avocado import main

import time

class DisabledTest(Test):
    '''
    :avocado: disable
    :avocado: tags=fast,net
    '''
    def test_disabled(self):
        pass

class FastTest(Test):
    '''
    :avocado: tags=fast
    '''
    def test_fast(self):
        '''
        :avocado: tags=net
        '''
        pass

    def test_fast_other(self):
        '''
        :avocado: tags=net
        '''
        pass

class SlowTest(Test):
    '''
    :avocado: tags=slow,disk
    '''
    def test_slow(self):
        time.sleep(1)

class SlowUnsafeTest(Test):
    '''
    :avocado: tags=slow,disk,unsafe
    '''
    def test_slow_unsafe(self):
        time.sleep(1)

class SafeTest(Test):
    '''
    :avocado: tags=safe
    '''
    def test_safe(self):
        pass

class SafeX86Test(Test):
    '''
    :avocado: tags=safe,arch:x86_64
    '''
    def test_safe_x86(self):
        pass

class NoTagsTest(Test):
    def test_no_tags(self):
        pass

if __name__ == "__main__":
    main()
"""

NOT_A_TEST = """
def hello():
    print('Hello World!')
"""

PY_SIMPLE_TEST = """#!/usr/bin/env python
def hello():
    print('Hello World!')

if __name__ == "__main__":
    hello()
"""

SIMPLE_TEST = """#!/bin/sh
true
"""

AVOCADO_MULTIPLE_TESTS = """from avocado import Test

class MultipleMethods(Test):
    def test_one(self):
        pass
    def testTwo(self):
        pass
    def foo(self):
        pass
"""

AVOCADO_MULTIPLE_TESTS_SAME_NAME = """from avocado import Test

class MultipleMethods(Test):
    def test(self):
        raise
    def test(self):
        raise
    def test(self):
        pass
"""

AVOCADO_FOREIGN_TAGGED_ENABLE = """from foreignlib import Base

class First(Base):
    '''
    First actual test based on library base class

    This Base class happens to, fictionally, inherit from avocado.Test. Because
    Avocado can't tell that, a tag is necessary to signal that.

    :avocado: enable
    '''
    def test(self):
        pass
"""

AVOCADO_TEST_NESTED_TAGGED = """from avocado import Test
import avocado
import fmaslkfdsaf

class First(Test):
    '''
    :avocado: disable
    '''
    def test(self):
        class Third(Test):
            '''
            :avocado: enable
            '''
            def test_2(self):
                pass
        class Fourth(Second):
            '''
            :avocado: enable
            '''
            def test_3(self):
                pass
        pass
"""

AVOCADO_TEST_MULTIPLE_IMPORTS = """from avocado import Test
import avocado

class Second(avocado.Test):
    def test_1(self):
        pass
"""

PYTHON_UNITTEST = """#!/usr/bin/env python
from unittest import TestCase

class SampleTest(TestCase):
    def test(self):
        pass
"""


class LoaderTest(unittest.TestCase):

    def _check_discovery(self, exps, tests):
        self.assertEqual(len(exps), len(tests), "Total count of tests not "
                         "as expected (%s != %s)\nexps: %s\ntests: %s"
                         % (len(exps), len(tests), exps, tests))
        try:
            for exp, tst in zip(exps, tests):
                # Test class
                self.assertEqual(tst[0], exp[0])
                # Test name (path)
                # py2 reports relpath, py3 abspath
                self.assertEqual(os.path.abspath(tst[1]['name']),
                                 os.path.abspath(exp[1]))
        except AssertionError as details:
            raise AssertionError("%s\nexps: %s\ntests:%s"
                                 % (details, exps, tests))

    def setUp(self):
        self.loader = loader.FileLoader(None, {})
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)

    def test_load_simple(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest')
        simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(simple_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        test_parameters['name'] = test.TestID(0, test_parameters['name'])
        test_parameters['base_logdir'] = self.tmpdir
        tc = test_class(**test_parameters)
        tc.run_avocado()
        suite = self.loader.discover(simple_test.path, loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["name"], simple_test.path)
        simple_test.remove()

    def test_load_simple_not_exec(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest',
                                             mode=DEFAULT_NON_EXEC_MODE)
        simple_test.save()
        test_class, _ = self.loader.discover(simple_test.path, loader.DiscoverMode.ALL)[0]
        self.assertTrue(test_class == loader.NotATest, test_class)
        simple_test.remove()

    def test_load_pass(self):
        avocado_pass_test = script.TemporaryScript('passtest.py',
                                                   AVOCADO_TEST_OK,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, _ = self.loader.discover(avocado_pass_test.path,
                                             loader.DiscoverMode.ALL)[0]
        self.assertTrue(test_class == 'PassTest', test_class)
        avocado_pass_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py',
                                                    NOT_A_TEST,
                                                    'avocado_loader_unittest',
                                                    mode=DEFAULT_NON_EXEC_MODE)
        avocado_not_a_test.save()
        test_class, _ = self.loader.discover(avocado_not_a_test.path,
                                             loader.DiscoverMode.ALL)[0]
        self.assertTrue(test_class == loader.NotATest, test_class)
        avocado_not_a_test.remove()

    def test_load_not_a_test_exec(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST,
                                                    'avocado_loader_unittest')
        avocado_not_a_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_not_a_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == test.SimpleTest, test_class)
        test_parameters['name'] = test.TestID(0, test_parameters['name'])
        test_parameters['base_logdir'] = self.tmpdir
        tc = test_class(**test_parameters)
        # The test can't be executed (no shebang), raising an OSError
        # (OSError: [Errno 8] Exec format error)
        self.assertRaises(OSError, tc.test)
        avocado_not_a_test.remove()

    def test_py_simple_test(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest')
        avocado_simple_test.save()
        test_class, test_parameters = (
            self.loader.discover(avocado_simple_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == test.SimpleTest)
        test_parameters['name'] = test.TestID(0, test_parameters['name'])
        test_parameters['base_logdir'] = self.tmpdir
        tc = test_class(**test_parameters)
        tc.run_avocado()
        avocado_simple_test.remove()

    def test_py_simple_test_notexec(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py',
                                                     PY_SIMPLE_TEST,
                                                     'avocado_loader_unittest',
                                                     mode=DEFAULT_NON_EXEC_MODE)
        avocado_simple_test.save()
        test_class, _ = self.loader.discover(avocado_simple_test.path,
                                             loader.DiscoverMode.ALL)[0]
        self.assertTrue(test_class == loader.NotATest)
        avocado_simple_test.remove()

    def test_multiple_methods(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=DEFAULT_NON_EXEC_MODE)
        avocado_multiple_tests.save()
        suite = self.loader.discover(avocado_multiple_tests.path, loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 2)
        # Try to load only some of the tests
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':MultipleMethods.testTwo', loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'testTwo')
        # Load using regexp
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':.*_one', loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'test_one')
        # Load booth
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':test.*', loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 2)
        # Load none should return no tests
        self.assertTrue(not self.loader.discover(avocado_multiple_tests.path +
                                                 ":no_match", loader.DiscoverMode.ALL))
        avocado_multiple_tests.remove()

    def test_multiple_methods_same_name(self):
        avocado_multiple_tests = script.TemporaryScript('multipletests.py',
                                                        AVOCADO_MULTIPLE_TESTS_SAME_NAME,
                                                        'avocado_multiple_tests_unittest',
                                                        mode=DEFAULT_NON_EXEC_MODE)
        avocado_multiple_tests.save()
        suite = self.loader.discover(avocado_multiple_tests.path, loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 1)
        # Try to load only some of the tests
        suite = self.loader.discover(avocado_multiple_tests.path +
                                     ':MultipleMethods.test', loader.DiscoverMode.ALL)
        self.assertEqual(len(suite), 1)
        self.assertEqual(suite[0][1]["methodName"], 'test')
        avocado_multiple_tests.remove()

    def test_load_foreign(self):
        avocado_pass_test = script.TemporaryScript('foreign.py',
                                                   AVOCADO_FOREIGN_TAGGED_ENABLE,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, _ = (
            self.loader.discover(avocado_pass_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == 'First', test_class)
        avocado_pass_test.remove()

    def test_load_pass_disable(self):
        avocado_pass_test = script.TemporaryScript('disable.py',
                                                   AVOCADO_TEST_OK_DISABLED,
                                                   'avocado_loader_unittest',
                                                   DEFAULT_NON_EXEC_MODE)
        avocado_pass_test.save()
        test_class, _ = (
            self.loader.discover(avocado_pass_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == loader.NotATest)
        avocado_pass_test.remove()

    def test_load_tagged_nested(self):
        avocado_nested_test = script.TemporaryScript('nested.py',
                                                     AVOCADO_TEST_NESTED_TAGGED,
                                                     'avocado_loader_unittest',
                                                     DEFAULT_NON_EXEC_MODE)
        avocado_nested_test.save()
        test_class, _ = self.loader.discover(avocado_nested_test.path,
                                             loader.DiscoverMode.ALL)[0]
        self.assertTrue(test_class == loader.NotATest)
        avocado_nested_test.remove()

    def test_load_multiple_imports(self):
        avocado_multiple_imp_test = script.TemporaryScript(
            'multipleimports.py',
            AVOCADO_TEST_MULTIPLE_IMPORTS,
            'avocado_loader_unittest')
        avocado_multiple_imp_test.save()
        test_class, _ = (
            self.loader.discover(avocado_multiple_imp_test.path, loader.DiscoverMode.ALL)[0])
        self.assertTrue(test_class == 'Second', test_class)
        avocado_multiple_imp_test.remove()

    def test_python_unittest(self):
        disabled_test = script.TemporaryScript("disabled.py",
                                               AVOCADO_TEST_OK_DISABLED,
                                               mode=DEFAULT_NON_EXEC_MODE)
        python_unittest = script.TemporaryScript("python_unittest.py",
                                                 PYTHON_UNITTEST)
        disabled_test.save()
        python_unittest.save()
        tests = self.loader.discover(disabled_test.path)
        self.assertEqual(tests, [])
        tests = self.loader.discover(python_unittest.path)
        exp = [(test.PythonUnittest,
                {"name": "python_unittest.SampleTest.test",
                 "test_dir": os.path.dirname(python_unittest.path)})]
        self.assertEqual(tests, exp)

    def test_mod_import_and_classes(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'loader_instrumented', 'dont_crash.py')
        tests = self.loader.discover(path)
        exps = [('DiscoverMe', 'selftests/.data/loader_instrumented/dont_crash.py:DiscoverMe.test'),
                ('DiscoverMe2', 'selftests/.data/loader_instrumented/dont_crash.py:DiscoverMe2.test'),
                ('DiscoverMe3', 'selftests/.data/loader_instrumented/dont_crash.py:DiscoverMe3.test'),
                ('DiscoverMe4', 'selftests/.data/loader_instrumented/dont_crash.py:DiscoverMe4.test')]
        self._check_discovery(exps, tests)

    def test_double_import(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'loader_instrumented', 'double_import.py')
        tests = self.loader.discover(path)
        exps = [('Test1', 'selftests/.data/loader_instrumented/double_import.py:Test1.test1'),
                ('Test2', 'selftests/.data/loader_instrumented/double_import.py:Test2.test2'),
                ('Test3', 'selftests/.data/loader_instrumented/double_import.py:Test3.test3'),
                ('Test4', 'selftests/.data/loader_instrumented/double_import.py:Test4.test4')]
        self._check_discovery(exps, tests)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TagFilter(unittest.TestCase):

    def setUp(self):
        with script.TemporaryScript('tags.py',
                                    AVOCADO_TEST_TAGS,
                                    'avocado_loader_unittest',
                                    DEFAULT_NON_EXEC_MODE) as test_script:
            this_loader = loader.FileLoader(None, {})
            self.test_suite = this_loader.discover(test_script.path,
                                                   loader.DiscoverMode.ALL)

    def test_no_tag_filter(self):
        self.assertEqual(len(self.test_suite), 7)
        self.assertEqual(self.test_suite[0][0], 'FastTest')
        self.assertEqual(self.test_suite[0][1]['methodName'], 'test_fast')
        self.assertEqual(self.test_suite[1][0], 'FastTest')
        self.assertEqual(self.test_suite[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(self.test_suite[2][0], 'SlowTest')
        self.assertEqual(self.test_suite[2][1]['methodName'], 'test_slow')
        self.assertEqual(self.test_suite[3][0], 'SlowUnsafeTest')
        self.assertEqual(self.test_suite[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(self.test_suite[4][0], 'SafeTest')
        self.assertEqual(self.test_suite[4][1]['methodName'], 'test_safe')
        self.assertEqual(self.test_suite[5][0], 'SafeX86Test')
        self.assertEqual(self.test_suite[5][1]['methodName'], 'test_safe_x86')
        self.assertEqual(self.test_suite[6][0], 'NoTagsTest')
        self.assertEqual(self.test_suite[6][1]['methodName'], 'test_no_tags')

    def test_filter_fast_net(self):
        filtered = loader.filter_test_tags(self.test_suite, ['fast,net'], False, False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')

    def test_filter_fast_net_include_empty(self):
        filtered = loader.filter_test_tags(self.test_suite, ['fast,net'], True, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'NoTagsTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_no_tags')

    def test_filter_arch(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch'], False, False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')

    def test_filter_arch_include_empty(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch'], True, False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[1][0], 'NoTagsTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_no_tags')

    def test_filter_arch_x86_64(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch:x86_64'], False, False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0][0], 'SafeX86Test')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe_x86')

    def test_filter_arch_other(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch:ppc64'], False, False)
        self.assertEqual(len(filtered), 0)

    def test_filter_arch_other_include_empty_key(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch:ppc64'], False, True)
        self.assertEqual(len(filtered), 5)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(filtered[4][0], 'SafeTest')
        self.assertEqual(filtered[4][1]['methodName'], 'test_safe')

    def test_filter_arch_other_include_empty_flat_and_key(self):
        filtered = loader.filter_test_tags(self.test_suite, ['arch:ppc64'], True, True)
        self.assertEqual(len(filtered), 6)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')
        self.assertEqual(filtered[4][0], 'SafeTest')
        self.assertEqual(filtered[4][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[5][0], 'NoTagsTest')
        self.assertEqual(filtered[5][1]['methodName'], 'test_no_tags')

    def test_filter_fast_net__slow_disk_unsafe(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['fast,net',
                                            'slow,disk,unsafe'],
                                           False, False)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow_unsafe')

    def test_filter_fast_net__slow_disk(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['fast,net',
                                            'slow,disk'],
                                           False, False)
        self.assertEqual(len(filtered), 4)
        self.assertEqual(filtered[0][0], 'FastTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_fast')
        self.assertEqual(filtered[1][0], 'FastTest')
        self.assertEqual(filtered[1][1]['methodName'], 'test_fast_other')
        self.assertEqual(filtered[2][0], 'SlowTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_slow')
        self.assertEqual(filtered[3][0], 'SlowUnsafeTest')
        self.assertEqual(filtered[3][1]['methodName'], 'test_slow_unsafe')

    def test_filter_not_fast_not_slow(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['-fast,-slow'],
                                           False)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0][0], 'SafeTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[1][0], 'SafeX86Test')
        self.assertEqual(filtered[1][1]['methodName'], 'test_safe_x86')

    def test_filter_not_fast_not_slow_include_empty(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['-fast,-slow'],
                                           True)
        self.assertEqual(len(filtered), 3)
        self.assertEqual(filtered[0][0], 'SafeTest')
        self.assertEqual(filtered[0][1]['methodName'], 'test_safe')
        self.assertEqual(filtered[1][0], 'SafeX86Test')
        self.assertEqual(filtered[1][1]['methodName'], 'test_safe_x86')
        self.assertEqual(filtered[2][0], 'NoTagsTest')
        self.assertEqual(filtered[2][1]['methodName'], 'test_no_tags')

    def test_filter_not_fast_not_slow_not_safe(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['-fast,-slow,-safe'],
                                           False)
        self.assertEqual(len(filtered), 0)

    def test_filter_not_fast_not_slow_not_safe_others_dont_exist(self):
        filtered = loader.filter_test_tags(self.test_suite,
                                           ['-fast,-slow,-safe',
                                            'does,not,exist'],
                                           False)
        self.assertEqual(len(filtered), 0)

    def test_load_tags(self):
        tags_map = {
            'FastTest.test_fast': {'fast': None, 'net': None},
            'FastTest.test_fast_other': {'fast': None, 'net': None},
            'SlowTest.test_slow': {'slow': None, 'disk': None},
            'SlowUnsafeTest.test_slow_unsafe': {'slow': None,
                                                'disk': None,
                                                'unsafe': None},
            'SafeTest.test_safe': {'safe': None},
            'SafeX86Test.test_safe_x86': {'safe': None,
                                          'arch': set(['x86_64'])},
            'NoTagsTest.test_no_tags': {}
        }

        for _, info in self.test_suite:
            name = info['name'].split(':', 1)[1]
            self.assertEqual(info['tags'], tags_map[name])
            del(tags_map[name])
        self.assertEqual(len(tags_map), 0)


class TagFilter2(unittest.TestCase):

    def test_filter_tags_include_empty(self):
        with script.TemporaryScript('passtest.py',
                                    AVOCADO_TEST_OK,
                                    'avocado_loader_unittest',
                                    DEFAULT_NON_EXEC_MODE) as test_script:
            this_loader = loader.FileLoader(None, {})
            test_suite = this_loader.discover(test_script.path,
                                              loader.DiscoverMode.ALL)
        self.assertEqual([], loader.filter_test_tags(test_suite, [], False, False))
        self.assertEqual(test_suite,
                         loader.filter_test_tags(test_suite, [], True, False))


class ParseFilterByTags(unittest.TestCase):

    def test_must(self):
        self.assertEqual(loader.parse_filter_by_tags(['foo,bar,baz']),
                         [(set(['foo', 'bar', 'baz']), set([]))])

    def test_must_must_not(self):
        self.assertEqual(loader.parse_filter_by_tags(['foo,-bar,baz']),
                         [(set(['foo', 'baz']), set(['bar']))])

    def test_musts_must_nots(self):
        self.assertEqual(loader.parse_filter_by_tags(['foo,bar,baz',
                                                      '-FOO,-BAR,-BAZ']),
                         [(set(['foo', 'bar', 'baz']), set([])),
                          (set([]), set(['FOO', 'BAR', 'BAZ']))])


if __name__ == '__main__':
    unittest.main()
