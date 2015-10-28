import os
import shutil
import unittest
import tempfile


from avocado.core import discovery


class DiscoverTest(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        files = ['foo.sh', 'bar', 'nopy']
        self.files = [os.path.join(self.basedir, f) for f in files]
        py_files = ['foo.py', 'bar.py']
        self.py_files = [os.path.join(self.basedir, f) for f in py_files]
        self.all_files = self.files + self.py_files
        for f in self.all_files:
            os.mknod(f)

    def tearDown(self):
        try:
            shutil.rmtree(self.basedir)
        except OSError:
            pass

    def test_file_discovery(self):
        file_discovery = discovery.FileLocationDiscovery(self.basedir)
        locations = file_discovery.get_locations()
        self.assertEquals(locations.sort(), self.all_files.sort())

    def test_python_file_discovery(self):
        python_discovery = discovery.PythonFileLocationDiscovery(self.basedir)
        locations = python_discovery.get_locations()
        self.assertEquals(locations.sort(), self.py_files.sort())

if __name__ == '__main__':
    unittest.main()
