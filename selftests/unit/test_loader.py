import os
import stat
import tempfile
import unittest.mock

from avocado.core import loader
from avocado.utils import script
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

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


class LoaderTest(unittest.TestCase):

    def _check_discovery(self, exps, tests):
        self.assertEqual(len(exps), len(tests),
                         (f'Total count of tests not '
                          f'as expected ({len(exps)} != {len(tests)}) '
                          f'\nexps: {exps}\ntests: {tests}'))
        try:
            for exp, tst in zip(exps, tests):
                # Test class
                self.assertEqual(tst[0], exp[0])
                # Test name (path)
                # py2 reports relpath, py3 abspath
                self.assertEqual(os.path.abspath(tst[1]['name']),
                                 os.path.abspath(exp[1]))
        except AssertionError as details:
            raise AssertionError(f"{details}\nexps: {exps}\ntests:{tests}")

    def setUp(self):
        self.loader = loader.FileLoader(None, {})
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

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
        # Load using regex
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

    def test_mod_import_and_classes(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'safeloader', 'data', 'dont_crash.py')
        tests = self.loader.discover(path)
        exps = [('DiscoverMe', 'selftests/.data/safeloader/data/dont_crash.py:DiscoverMe.test'),
                ('DiscoverMe2', 'selftests/.data/safeloader/data/dont_crash.py:DiscoverMe2.test'),
                ('DiscoverMe3', 'selftests/.data/safeloader/data/dont_crash.py:DiscoverMe3.test'),
                ('DiscoverMe4', 'selftests/.data/safeloader/data/dont_crash.py:DiscoverMe4.test')]
        self._check_discovery(exps, tests)

    def test_imports(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'safeloader', 'data', 'imports.py')
        tests = self.loader.discover(path)
        exps = [('Test1', 'selftests/.data/safeloader/data/imports.py:Test1.test'),
                ('Test3', 'selftests/.data/safeloader/data/imports.py:Test3.test'),
                ('Test4', 'selftests/.data/safeloader/data/imports.py:Test4.test'),
                ('Test5', 'selftests/.data/safeloader/data/imports.py:Test5.test'),
                ('Test6', 'selftests/.data/safeloader/data/imports.py:Test6.test'),
                ('Test8', 'selftests/.data/safeloader/data/imports.py:Test8.test'),
                ('Test10', 'selftests/.data/safeloader/data/imports.py:Test10.test')]
        self._check_discovery(exps, tests)

    def test_infinite_recurse(self):
        """Checks we don't crash on infinite recursion"""
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'safeloader', 'data',
                            'infinite_recurse.py')
        tests = self.loader.discover(path)
        self.assertEqual(tests, [])

    def test_double_import(self):
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            '.data', 'safeloader', 'data', 'double_import.py')
        tests = self.loader.discover(path)
        exps = [('Test1', 'selftests/.data/safeloader/data/double_import.py:Test1.test1'),
                ('Test2', 'selftests/.data/safeloader/data/double_import.py:Test2.test2'),
                ('Test3', 'selftests/.data/safeloader/data/double_import.py:Test3.test3'),
                ('Test4', 'selftests/.data/safeloader/data/double_import.py:Test4.test4')]
        self._check_discovery(exps, tests)

    def test_list_raising_exception(self):
        with script.TemporaryScript('test.py', AVOCADO_TEST_OK) as avocado_test:
            with unittest.mock.patch('avocado.core.loader.safeloader.find_avocado_tests') as _mock:
                _mock.side_effect = BaseException()
                tests = self.loader.discover(avocado_test.path,
                                             loader.DiscoverMode.ALL)
                self.assertEqual(tests[0][1]["name"],
                                 f"{avocado_test.path}: Not an INSTRUMENTED "
                                 f"(avocado.Test based) test")

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
