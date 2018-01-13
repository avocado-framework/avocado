import unittest

from avocado.core import dispatcher


def broken_crypto_libs():
    '''
    Check if the loading of the the remote plugin by the dispatcher
    code will trigger a Fabric3/paramiko/cryptography issue on
    Python 3.
    '''
    try:
        from cryptography.hazmat.backends import default_backend
    except ImportError:
        return True
    return False


class DispatcherTest(unittest.TestCase):

    @unittest.skipIf(broken_crypto_libs(),
                     "Skipping on Python 3 because of Fabric3/paramiko issues")
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
