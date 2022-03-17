import unittest

from avocado.core.dispatcher import EnabledExtensionManager
from avocado.core.extension_manager import PluginPriority


class DispatcherTest(unittest.TestCase):

    def test_order(self):
        """
        Simply checks that the default order is based on the extension names
        """
        namespaces = [('avocado.plugins.cli', {}),
                      ('avocado.plugins.cli.cmd', {}),
                      ('avocado.plugins.job.prepost', {}),
                      ('avocado.plugins.result', {}),
                      ('avocado.plugins.resolver', {'config': None})]
        for namespace in namespaces:
            with self.subTest(i=namespace):
                namespace, invoke_kwds = namespace
                ext_objects = EnabledExtensionManager(namespace,
                                                      invoke_kwds).extensions
                sort = sorted(ext_objects, key=lambda x: x.name)
                sort = sorted(sort, key=lambda x:
                              getattr(x.obj, 'priority', PluginPriority.NORMAL),
                              reverse=True)
                self.assertEqual(ext_objects, sort)


if __name__ == '__main__':
    unittest.main()
