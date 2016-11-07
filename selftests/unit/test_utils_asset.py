import os
import shutil
import tempfile
import unittest

from avocado.utils import asset
from avocado.utils.filelock import FileLock


class TestAsset(unittest.TestCase):

    def setUp(self):
        self.basedir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.assetdir = tempfile.mkdtemp(dir=self.basedir)
        self.assetname = 'foo.tgz'
        self.assethash = '3a033a8938c1af56eeb793669db83bcbd0c17ea5'
        self.localpath = os.path.join(self.assetdir, self.assetname)
        with open(self.localpath, 'w') as f:
            f.write('Test!')
        self.url = 'file://%s' % self.localpath
        self.cache_dir = tempfile.mkdtemp(dir=self.basedir)

    def testFetch_urlname(self):
        foo_tarball = asset.Asset(self.url,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=None,
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        expected_tarball = os.path.join(self.cache_dir, self.assetname)
        self.assertEqual(foo_tarball, expected_tarball)

    def testFetch_location(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[self.url],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        expected_tarball = os.path.join(self.cache_dir, self.assetname)
        self.assertEqual(foo_tarball, expected_tarball)

    def testFecth_expire(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[self.url],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        with open(foo_tarball, 'r') as f:
            content1 = f.read()

        # Create the file in a different location with a different content
        new_assetdir = tempfile.mkdtemp(dir=self.basedir)
        new_localpath = os.path.join(new_assetdir, self.assetname)
        new_hash = '9f1ad57044be4799f288222dc91d5eab152921e9'
        new_url = 'file://%s' % new_localpath
        with open(new_localpath, 'w') as f:
            f.write('Changed!')

        # Dont expire cached file
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[new_url],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        with open(foo_tarball, 'r') as f:
            content2 = f.read()
        self.assertEqual(content1, content2)

        # Expire cached file
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=new_hash,
                                  algorithm='sha1',
                                  locations=[new_url],
                                  cache_dirs=[self.cache_dir],
                                  expire=-1).fetch()

        with open(foo_tarball, 'r') as f:
            content2 = f.read()
        self.assertNotEqual(content1, content2)

    def testException(self):
        a = asset.Asset(name='bar.tgz', asset_hash=None, algorithm=None,
                        locations=None, cache_dirs=[self.cache_dir],
                        expire=None)
        self.assertRaises(EnvironmentError, a.fetch)

    def testFetch_lockerror(self):
        with FileLock(os.path.join(self.cache_dir, self.assetname)):
            a = asset.Asset(self.url,
                            asset_hash=self.assethash,
                            algorithm='sha1',
                            locations=None,
                            cache_dirs=[self.cache_dir],
                            expire=None)
            self.assertRaises(EnvironmentError, a.fetch)

    def tearDown(self):
        shutil.rmtree(self.basedir)


if __name__ == "__main__":
    unittest.main()
