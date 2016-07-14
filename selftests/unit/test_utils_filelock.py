import os
import shutil
import tempfile
import unittest

from avocado.utils import filelock


class TestAsset(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.filename = os.path.join(self.basedir, 'file.img')
        self.content = 'Foo bar'
        with open(self.filename, 'w') as f:
            f.write(self.content)

    def _readfile(self):
        lock = filelock.LockFile(self.filename)
        try:
            lock.acquire()
            with open(self.filename, 'r') as f:
                return f.read()
        finally:
            lock.release()

    def test_readfile(self):
        self.assertEqual(self._readfile(), self.content)

    def test_alreadylocked(self):
        lock = filelock.LockFile(self.filename)
        lock.acquire()
        self.assertRaises(filelock.AlreadyLocked, self._readfile)
        lock.release()

    def test_notmylock(self):
        with open(self.filename+'.lock', 'w') as f:
            f.write('1')
        self.assertRaises(filelock.AlreadyLocked, self._readfile)

    def tearDown(self):
        shutil.rmtree(self.basedir)

if __name__ == "__main__":
    unittest.main()
