import os
import unittest

from avocado.core import resolver
from avocado.plugins.resolvers import (AvocadoInstrumentedResolver,
                                       ExecTestResolver)
from avocado.utils import script
from selftests.utils import BASEDIR


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
                                    'test_resolver_exec_test') as simple_test:
            res = ExecTestResolver().resolve(simple_test.path)
            self.assertEqual(res.reference, simple_test.path)
            self.assertEqual(res.result, resolver.ReferenceResolutionResult.SUCCESS)
            self.assertEqual(len(res.resolutions), 1)
            resolution = res.resolutions[0]
            self.assertEqual(resolution.kind, 'exec-test')
            self.assertEqual(resolution.uri, simple_test.path)
            self.assertEqual(resolution.args, ())
            self.assertEqual(resolution.kwargs, {})
            self.assertEqual(resolution.tags, None)


if __name__ == '__main__':
    unittest.main()
