import os
import shutil
import tempfile
import unittest

from avocado.utils import asset


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
                                  cache_dirs=[self.cache_dir]).fetch()
        expected_tarball = os.path.join(self.cache_dir, self.assetname)
        self.assertEqual(foo_tarball, expected_tarball)
        hashfile = '.'.join([expected_tarball, 'sha1'])
        self.assertTrue(os.path.isfile(hashfile))
        expected_content = '%s %s\n' % (self.assethash, self.assetname)
        with open(hashfile, 'r') as f:
            content = f.read()
        self.assertEqual(content, expected_content)

    def testFetch_location(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[self.url],
                                  cache_dirs=[self.cache_dir]).fetch()
        expected_tarball = os.path.join(self.cache_dir, self.assetname)
        self.assertEqual(foo_tarball, expected_tarball)
        hashfile = '.'.join([expected_tarball, 'sha1'])
        self.assertTrue(os.path.isfile(hashfile))
        expected_content = '%s %s\n' % (self.assethash, self.assetname)
        with open(hashfile, 'r') as f:
            content = f.read()
        self.assertEqual(content, expected_content)

    def testException(self):
        a = asset.Asset(name='bar.tgz', asset_hash=None, algorithm=None,
                        locations=None, cache_dirs=[self.cache_dir])
        self.assertRaises(EnvironmentError, a.fetch)

    def tearDown(self):
        shutil.rmtree(self.basedir)

if __name__ == "__main__":
    unittest.main()
