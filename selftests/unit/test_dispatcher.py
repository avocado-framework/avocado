import unittest

from avocado.core.dispatcher import EnabledExtensionManager


class DispatcherTest(unittest.TestCase):

    def test_order(self):
        """
        Simply checks that the default order is based on the extension names
        """
        namespaces = ['avocado.plugins.cli',
                      'avocado.plugins.cli.cmd',
                      'avocado.plugins.job.prepost',
                      'avocado.plugins.result']
        for namespace in namespaces:
            ext_names = [ext.name for ext in
                         EnabledExtensionManager(namespace).extensions]
            self.assertEqual(ext_names, sorted(ext_names))


if __name__ == '__main__':
    unittest.main()
