import os
import stat
import unittest

from avocado.core import resolver
from avocado.plugins.resolvers import (AvocadoInstrumentedResolver,
                                       ExecTestResolver,
                                       PythonUnittestResolver)
from avocado.utils import script
from selftests.utils import BASEDIR

#: What is commonly known as "0664" or "u=rw,g=rw,o=r"
DEFAULT_NON_EXEC_MODE = (stat.S_IRUSR | stat.S_IWUSR |
                         stat.S_IRGRP | stat.S_IWGRP |
                         stat.S_IROTH)


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


PYTHON_UNITTEST = """#!/usr/bin/env python
from unittest import TestCase

from . import something

class SampleTest(TestCase):
    '''
    :avocado: tags=flattag
    :avocado: tags=foo:bar
    '''
    def test(self):
        pass
"""


class ReferenceResolution(unittest.TestCase):

    """
    Tests on how to initialize and use
    :class:`avocado.core.resolver.ReferenceResolution`
    """

    def test_no_args(self):
        with self.assertRaises(TypeError):
            resolver.ReferenceResolution()

    def test_no_result(self):
        with self.assertRaises(TypeError):
            resolver.ReferenceResolution('/test/reference')

    def test_no_resolutions(self):
        resolution = resolver.ReferenceResolution(
            '/test/reference',
            resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(len(resolution.resolutions), 0,
                         "Unexpected resolutions found")


class AvocadoInstrumented(unittest.TestCase):

    def test_passtest(self):
        passtest = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        test = 'PassTest.test'
        uri = '%s:%s' % (passtest, test)
        res = AvocadoInstrumentedResolver().resolve(passtest)
        self.assertEqual(res.reference, passtest)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertIsNone(res.info)
        self.assertIsNone(res.origin)
        self.assertEqual(len(res.resolutions), 1)
        resolution = res.resolutions[0]
        self.assertEqual(resolution.kind, 'avocado-instrumented')
        self.assertEqual(resolution.uri, uri)
        self.assertEqual(resolution.args, ())
        self.assertEqual(resolution.kwargs, {})
        self.assertEqual(resolution.tags, {'fast': None})

    def test_passtest_filter_found(self):
        passtest = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        test_filter = 'test'
        reference = '%s:%s' % (passtest, test_filter)
        res = AvocadoInstrumentedResolver().resolve(reference)
        self.assertEqual(res.reference, reference)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(res.resolutions), 1)

    def test_passtest_filter_notfound(self):
        passtest = os.path.join(BASEDIR, 'examples', 'tests', 'passtest.py')
        test_filter = 'test_other'
        reference = '%s:%s' % (passtest, test_filter)
        res = AvocadoInstrumentedResolver().resolve(reference)
        self.assertEqual(res.reference, reference)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.NOTFOUND)


class ExecTest(unittest.TestCase):

    def test_exec_test(self):
        with script.TemporaryScript('exec-test.sh', "#!/bin/sh\ntrue",
                                    'test_resolver_exec_test') as exec_test:
            res = ExecTestResolver().resolve(exec_test.path)
        self.assertEqual(res.reference, exec_test.path)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(res.resolutions), 1)
        resolution = res.resolutions[0]
        self.assertEqual(resolution.kind, 'exec-test')
        self.assertEqual(resolution.uri, exec_test.path)
        self.assertEqual(resolution.args, ())
        self.assertEqual(resolution.kwargs, {})
        self.assertEqual(resolution.tags, None)

    def test_not_exec(self):
        with script.TemporaryScript('exec-test.sh', "#!/bin/sh\ntrue",
                                    'test_resolver_exec_test',
                                    mode=DEFAULT_NON_EXEC_MODE) as exec_test:
            res = ExecTestResolver().resolve(exec_test.path)
        self.assertEqual(res.reference, exec_test.path)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.NOTFOUND)
        self.assertEqual(len(res.resolutions), 0)


class PythonUnittest(unittest.TestCase):

    def test_disabled(self):
        with script.TemporaryScript(
                "disabled.py",
                AVOCADO_TEST_OK_DISABLED,
                mode=DEFAULT_NON_EXEC_MODE) as disabled_test:
            res = PythonUnittestResolver().resolve(disabled_test.path)
        self.assertEqual(res.result,
                         resolver.ReferenceResolutionResult.NOTFOUND)

    def test_unittest(self):
        with script.TemporaryScript(
                "python_unittest.py",
                PYTHON_UNITTEST) as python_unittest:
            res = PythonUnittestResolver().resolve(python_unittest.path)

        self.assertEqual(res.reference, python_unittest.path)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(res.resolutions), 1)
        resolution = res.resolutions[0]
        self.assertEqual(resolution.kind, 'python-unittest')
        self.assertEqual(resolution.uri,
                         "%s:%s" % (python_unittest.path, "SampleTest.test"))
        self.assertEqual(resolution.args, ())
        self.assertEqual(resolution.kwargs, {})
        self.assertEqual(resolution.tags, {"flattag": None, "foo": {"bar"}})

    def test_dont_detect_non_avocado(self):
        def _check_resolution(resolution, name):
            self.assertEqual(resolution.kind, 'python-unittest')
            self.assertEqual(resolution.uri, "%s:%s" % (path, name))
            self.assertEqual(resolution.args, ())
            self.assertEqual(resolution.kwargs, {})
            self.assertEqual(resolution.tags, {})
            self.assertEqual(resolution.requirements, [])

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            '.data', 'safeloader', 'data', 'dont_detect_non_avocado.py')

        res = PythonUnittestResolver().resolve(path)
        self.assertEqual(res.reference, path)
        self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(res.resolutions), 3)

        _check_resolution(res.resolutions[0], "StaticallyNotAvocadoTest.test")
        _check_resolution(res.resolutions[1], "NotTest.test2")
        _check_resolution(res.resolutions[2], "NotTest.test")


if __name__ == '__main__':
    unittest.main()
