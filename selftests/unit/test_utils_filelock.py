import os
import shutil
import tempfile
import unittest

from avocado.utils.filelock import AlreadyLocked
from avocado.utils.filelock import FileLock


class TestFileLock(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.filename = os.path.join(self.basedir, 'file.img')
        self.content = 'Foo bar'
        with open(self.filename, 'w') as f:
            f.write(self.content)

    def _readfile(self):
        with FileLock(self.filename):
            with open(self.filename, 'r') as f:
                return f.read()

    def test_readfile(self):
        self.assertEqual(self._readfile(), self.content)

    def test_locked_by_me(self):
        with FileLock(self.filename):
            self.assertRaises(AlreadyLocked, self._readfile)

    def test_locked_by_other(self):
        with open(self.filename+'.lock', 'w') as f:
            f.write('1')
        self.assertRaises(AlreadyLocked, self._readfile)

    def tearDown(self):
        shutil.rmtree(self.basedir)


if __name__ == "__main__":
    unittest.main()
