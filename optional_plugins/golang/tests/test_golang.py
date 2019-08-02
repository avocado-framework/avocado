import os
import unittest

import avocado_golang


THIS_DIR = os.path.dirname(os.path.abspath(__file__))


class Loader(unittest.TestCase):

    def setUp(self):
        self.previous_go_path = os.environ.get('GOPATH', None)
        os.environ['GOPATH'] = THIS_DIR

    @unittest.skipIf(avocado_golang.GO_BIN is None, "go binary not found")
    def test_discover(self):
        loader = avocado_golang.GolangLoader(None, {})
        results = loader.discover('countavocados')
        self.assertEqual(len(results), 2)
        empty_container_klass, empty_container_params = results[0]
        self.assertIs(empty_container_klass, avocado_golang.GolangTest)
        self.assertEqual(empty_container_params['name'],
                         "countavocados:TestEmptyContainers")
        no_container_klass, no_container_params = results[1]
        self.assertIs(no_container_klass, avocado_golang.GolangTest)
        self.assertEqual(no_container_params['name'],
                         "countavocados:TestNoContainers")

    def tearDown(self):
        if self.previous_go_path is not None:
            os.environ['GOPATH'] = self.previous_go_path
