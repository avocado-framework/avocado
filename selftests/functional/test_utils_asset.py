import os
import tempfile
import unittest

from avocado.utils import asset
from avocado.utils.filelock import FileLock
from selftests.utils import TestCaseTmpDir, setup_avocado_loggers

setup_avocado_loggers()


class TestAsset(TestCaseTmpDir):

    def setUp(self):
        super(TestAsset, self).setUp()
        self.assetdir = tempfile.mkdtemp(dir=self.tmpdir.name)
        self.assetname = 'foo.tgz'
        self.assethash = '3a033a8938c1af56eeb793669db83bcbd0c17ea5'
        self.localpath = os.path.join(self.assetdir, self.assetname)
        with open(self.localpath, 'w') as f:
            f.write('Test!')
        self.url = 'file://%s' % self.localpath
        self.cache_dir = tempfile.mkdtemp(dir=self.tmpdir.name)

    def test_fetch_url_cache_by_location(self):
        foo_tarball = asset.Asset(self.url,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=None,
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        expected_location = os.path.join(self.cache_dir, 'by_location')
        self.assertTrue(foo_tarball.startswith(expected_location))
        self.assertTrue(foo_tarball.endswith(self.assetname))

    def test_fetch_name_hash_cache_by_name(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[self.url],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        expected_location = os.path.join(self.cache_dir, 'by_name',
                                         self.assetname)
        self.assertEqual(foo_tarball, expected_location)

    def test_fetch_name_locations_cache_by_name(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=None,
                                  algorithm='sha1',
                                  locations=[self.url, 'file://fake_dir'],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        expected_location = os.path.join(self.cache_dir, 'by_name',
                                         self.assetname)
        self.assertEqual(foo_tarball, expected_location)

    def test_fetch_expire(self):
        foo_tarball = asset.Asset(self.assetname,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=[self.url],
                                  cache_dirs=[self.cache_dir],
                                  expire=None).fetch()
        with open(foo_tarball, 'r') as f:
            content1 = f.read()

        # Create the file in a different location with a different content
        new_assetdir = tempfile.mkdtemp(dir=self.tmpdir.name)
        new_localpath = os.path.join(new_assetdir, self.assetname)
        new_hash = '9f1ad57044be4799f288222dc91d5eab152921e9'
        new_url = 'file://%s' % new_localpath
        with open(new_localpath, 'w') as f:
            f.write('Changed!')

        # Don't expire cached file
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

    def test_fetch_lockerror(self):
        dirname = os.path.join(self.cache_dir, 'by_name')
        os.makedirs(dirname)
        with FileLock(os.path.join(dirname, self.assetname)):
            a = asset.Asset(self.assetname,
                            asset_hash=self.assethash,
                            algorithm='sha1',
                            locations=['file://foo1', 'file://foo2'],
                            cache_dirs=[self.cache_dir],
                            expire=None)
            self.assertRaises(OSError, a.fetch)

    def test_unknown_scheme(self):
        invalid = asset.Asset("weird-protocol://location/?params=foo",
                              None, None, None, [self.cache_dir], None)
        self.assertRaises(asset.UnsupportedProtocolError, invalid.fetch)

    def test_fetch_different_files(self):
        """
        Checks that when different assets which happen to have the
        same *filename*, are properly stored in the cache directory
        and that the right one will be given to the user, no matter if
        a hash is used or not.
        """
        second_assetname = self.assetname
        second_asset_origin_dir = tempfile.mkdtemp(dir=self.tmpdir.name)
        second_asset_local_path = os.path.join(second_asset_origin_dir,
                                               second_assetname)
        second_asset_content = 'This is not your first asset content!'
        with open(second_asset_local_path, 'w') as f:
            f.write(second_asset_content)
        second_asset_origin_url = 'file://%s' % second_asset_local_path

        a1 = asset.Asset(self.url, self.assethash, 'sha1', None,
                         [self.cache_dir], None)
        a1.fetch()
        a2 = asset.Asset(second_asset_origin_url, None, None,
                         None, [self.cache_dir], None)
        a2_path = a2.fetch()
        with open(a2_path, 'r') as a2_file:
            self.assertEqual(a2_file.read(), second_asset_content)

        third_assetname = self.assetname
        third_asset_origin_dir = tempfile.mkdtemp(dir=self.tmpdir.name)
        third_asset_local_path = os.path.join(third_asset_origin_dir,
                                              third_assetname)
        third_asset_content = 'Another content!'
        with open(third_asset_local_path, 'w') as f:
            f.write(third_asset_content)
        third_asset_origin_url = 'file://%s' % third_asset_local_path
        a3 = asset.Asset(third_asset_origin_url, None, None,
                         None, [self.cache_dir], None)
        a3_path = a3.fetch()
        with open(a3_path, 'r') as a3_file:
            self.assertEqual(a3_file.read(), third_asset_content)

    def test_create_metadata_file(self):
        expected_metadata = {"Name": "name", "version": 1.2}
        foo_tarball = asset.Asset(self.url,
                                  asset_hash=self.assethash,
                                  algorithm='sha1',
                                  locations=None,
                                  cache_dirs=[self.cache_dir],
                                  expire=None,
                                  metadata=expected_metadata).fetch()
        expected_file = "%s_metadata.json" % os.path.splitext(foo_tarball)[0]
        self.assertTrue(os.path.exists(expected_file))

    def test_get_metadata_file_exists(self):
        expected_metadata = {"Name": "name", "version": 1.2}
        a = asset.Asset(self.url,
                        asset_hash=self.assethash,
                        algorithm='sha1',
                        locations=None,
                        cache_dirs=[self.cache_dir],
                        expire=None,
                        metadata=expected_metadata)
        a.fetch()
        metadata = a.get_metadata()
        self.assertEqual(expected_metadata, metadata)

    def test_get_metadata_file_not_exists(self):
        expected_metadata = {"Name": "name", "version": 1.2}
        a = asset.Asset(self.url,
                        asset_hash=self.assethash,
                        algorithm='sha1',
                        locations=None,
                        cache_dirs=[self.cache_dir],
                        expire=None,
                        metadata=expected_metadata)
        with self.assertRaises(OSError):
            a.get_metadata()


if __name__ == "__main__":
    unittest.main()
