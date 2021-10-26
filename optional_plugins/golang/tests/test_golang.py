import os
import unittest.mock

import avocado_golang

from avocado.core.resolver import ReferenceResolutionResult

THIS_DIR = os.path.dirname(os.path.abspath(__file__))


@unittest.skipIf(avocado_golang.GO_BIN is None, "go binary not found")
class ResolverModule(unittest.TestCase):
    """
    Test golang resolution when a module name is given
    """

    def setUp(self):
        self.previous_go_path = os.environ.get('GOPATH', None)
        os.environ['GOPATH'] = THIS_DIR

    def test_resolver_no_go_bin(self):
        with unittest.mock.patch('avocado_golang.GO_BIN', None):
            res = avocado_golang.GolangResolver().resolve('countavocados')
        self.assertEqual(res.reference, 'countavocados')
        self.assertEqual(res.result, ReferenceResolutionResult.NOTFOUND)

    def test_resolver(self):
        res = avocado_golang.GolangResolver().resolve('countavocados')
        self.assertEqual(res.result, ReferenceResolutionResult.SUCCESS)
        self.assertEqual(len(res.resolutions), 3)
        empty_container = res.resolutions[0]
        self.assertEqual(empty_container.kind, 'golang')
        self.assertEqual(empty_container.uri, 'countavocados:TestEmptyContainers')
        no_container = res.resolutions[1]
        self.assertEqual(no_container.kind, 'golang')
        self.assertEqual(no_container.uri, 'countavocados:TestNoContainers')
        example = res.resolutions[2]
        self.assertEqual(example.kind, 'golang')
        self.assertEqual(example.uri, 'countavocados:ExampleContainers')

    def tearDown(self):
        if self.previous_go_path is not None:
            os.environ['GOPATH'] = self.previous_go_path
