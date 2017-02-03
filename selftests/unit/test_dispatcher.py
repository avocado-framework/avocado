import unittest

from avocado.core import dispatcher


class DispatcherTest(unittest.TestCase):

    def test_order(self):
        namespaces = ['avocado.plugins.cli',
                      'avocado.plugins.cli.cmd',
                      'avocado.plugins.job.prepost',
                      'avocado.plugins.result']
        for namespace in namespaces:
            names = dispatcher.Dispatcher(namespace).names()
            ext_names = [ext.name for ext in
                         dispatcher.Dispatcher(namespace).extensions]
            self.assertEqual(names, ext_names)
            self.assertEqual(names, sorted(names))
            self.assertEqual(ext_names, sorted(ext_names))


if __name__ == '__main__':
    unittest.main()
