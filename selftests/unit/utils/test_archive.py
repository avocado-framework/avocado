import os
import random
import sys
import tempfile
import unittest

from avocado.utils import archive, crypto, data_factory
from selftests.utils import BASEDIR, temp_dir_prefix


class ArchiveTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.basedir = tempfile.TemporaryDirectory(prefix=prefix)
        self.compressdir = tempfile.mkdtemp(dir=self.basedir.name)
        self.decompressdir = tempfile.mkdtemp(dir=self.basedir.name)
        self.sys_random = random.SystemRandom()

    def compress_and_check_dir(self, extension):
        hash_map_1 = {}
        for i in range(self.sys_random.randint(10, 20)):
            if i % 2 == 0:
                compressdir = tempfile.mkdtemp(dir=self.compressdir)
            else:
                compressdir = self.compressdir
            str_length = self.sys_random.randint(30, 50)
            fd, filename = tempfile.mkstemp(dir=compressdir, text=True)
            with os.fdopen(fd, 'w') as f:
                f.write(data_factory.generate_random_string(str_length))
            relative_path = filename.replace(self.compressdir, '')
            hash_map_1[relative_path] = crypto.hash_file(filename)

        archive_filename = self.compressdir + extension
        archive.compress(archive_filename, self.compressdir)
        archive.uncompress(archive_filename, self.decompressdir)

        hash_map_2 = {}
        for root, _, files in os.walk(self.decompressdir):
            for name in files:
                file_path = os.path.join(root, name)
                relative_path = file_path.replace(self.decompressdir, '')
                hash_map_2[relative_path] = crypto.hash_file(file_path)

        self.assertEqual(hash_map_1, hash_map_2)

    def compress_and_check_file(self, extension):
        str_length = self.sys_random.randint(30, 50)
        fd, filename = tempfile.mkstemp(dir=self.basedir.name, text=True)
        with os.fdopen(fd, 'w') as f:
            f.write(data_factory.generate_random_string(str_length))
        original_hash = crypto.hash_file(filename)
        dstfile = filename + extension
        archive_filename = os.path.join(self.basedir.name, dstfile)
        archive.compress(archive_filename, filename)
        ret = archive.uncompress(archive_filename, self.decompressdir)
        self.assertEqual(ret, os.path.basename(filename))
        decompress_file = os.path.join(self.decompressdir,
                                       os.path.basename(filename))
        decompress_hash = crypto.hash_file(decompress_file)
        self.assertEqual(original_hash, decompress_hash)

    def test_zip_dir(self):
        self.compress_and_check_dir('.zip')

    def test_zip_file(self):
        self.compress_and_check_file('.zip')

    def test_tar_dir(self):
        self.compress_and_check_dir('.tar')

    def test_tar_file(self):
        self.compress_and_check_file('.tar')

    def test_tgz_dir(self):
        self.compress_and_check_dir('.tar.gz')

    def test_tgz_file(self):
        self.compress_and_check_file('.tar.gz')

    def test_tgz_2_dir(self):
        self.compress_and_check_dir('.tgz')

    def test_tgz_2_file(self):
        self.compress_and_check_file('.tgz')

    def test_tbz2_dir(self):
        self.compress_and_check_dir('.tar.bz2')

    def test_tbz2_file(self):
        self.compress_and_check_file('.tar.bz2')

    def test_tbz2_2_dir(self):
        self.compress_and_check_dir('.tbz2')

    def test_tbz2_2_file(self):
        self.compress_and_check_file('.tbz2')

    @unittest.skipIf(sys.platform.startswith('darwin'),
                     'macOS does not support archive extra attributes')
    def test_zip_extra_attrs(self):
        """
        Check that utils.archive reflects extra attrs of file like symlinks
        and file permissions.
        """
        def get_path(*args):
            """ Get path with decompressdir prefix """
            return os.path.join(self.decompressdir, *args)
        # File types
        zip_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                os.path.pardir,
                                                os.path.pardir, ".data",
                                                "test_archive__symlinks.zip"))
        # TODO: Handle permission correctly for all users
        # The umask is not yet handled by utils.archive, hardcode it for now
        os.umask(2)
        archive.uncompress(zip_path, self.decompressdir)
        self.assertTrue(os.path.islink(get_path("link_to_dir")))
        self.assertTrue(os.path.islink(get_path("link_to_file")))
        self.assertTrue(os.path.islink(get_path("link_to_file2")))
        self.assertTrue(os.path.islink(get_path("dir", "2nd_link_to_file")))
        self.assertTrue(os.path.islink(get_path("dir",
                                                "link_to_link_to_file2")))
        self.assertTrue(os.path.islink(get_path("dir", "2nd_link_to_file")))
        self.assertTrue(os.path.islink(get_path("link_to_dir",
                                                "2nd_link_to_file")))
        self.assertTrue(os.path.isfile(get_path("file")))
        self.assertTrue(os.path.isfile(get_path("dir", "file2")))
        self.assertTrue(os.path.isfile(get_path("link_to_dir", "file2")))
        act = os.path.realpath(get_path("link_to_dir",
                                        "link_to_link_to_file2"))
        exp = get_path("dir", "file2")
        self.assertEqual(act, exp)
        self.assertEqual(os.path.realpath(get_path("link_to_dir")),
                         get_path("dir"))
        # File permissions
        self.assertEqual(os.stat(get_path("dir", "file2")).st_mode & 0o777,
                         0o664)
        self.assertEqual(os.stat(get_path("file")).st_mode & 0o777, 0o753)
        self.assertEqual(os.stat(get_path("dir")).st_mode & 0o777, 0o775)
        self.assertEqual(os.stat(get_path("link_to_file2")).st_mode & 0o777,
                         0o664)
        self.assertEqual(os.stat(get_path("link_to_dir")).st_mode & 0o777,
                         0o775)
        self.assertEqual(os.stat(get_path("link_to_file")).st_mode & 0o777,
                         0o753)

    def test_empty_tbz2(self):
        ret = archive.uncompress(os.path.join(BASEDIR, 'selftests', '.data',
                                              'empty.tar.bz2'), self.decompressdir)
        self.assertEqual(ret, None, "Empty archive should return None (%s)"
                         % ret)

    def test_is_gzip_file(self):
        gz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.gz')
        self.assertTrue(archive.is_gzip_file(gz_path))

    def test_gzip_uncompress_to_dir(self):
        gz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.gz')
        ret = archive.gzip_uncompress(gz_path, self.decompressdir)
        self.assertEqual(ret, os.path.join(self.decompressdir, 'avocado'))

    def test_gzip_uncompress_to_file(self):
        gz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.gz')
        filename = os.path.join(self.decompressdir, 'other')
        ret = archive.gzip_uncompress(gz_path, filename)
        self.assertEqual(ret, filename)

    def test_gzip_is_archive(self):
        gz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.gz')
        self.assertTrue(archive.is_archive(gz_path))

    def test_uncompress_gzip(self):
        gz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.gz')
        ret = archive.uncompress(gz_path, self.decompressdir)
        self.assertEqual(ret, os.path.join(self.decompressdir, 'avocado'))
        with open(ret, 'rb') as decompressed:
            self.assertEqual(decompressed.read(), b'avocado\n')

    def test_is_lzma_file(self):
        xz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.xz')
        self.assertTrue(archive.is_lzma_file(xz_path))

    def test_null_is_not_lzma_file(self):
        self.assertFalse(archive.is_lzma_file(os.devnull))

    def test_lzma_uncompress_to_dir(self):
        xz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.xz')
        ret = archive.lzma_uncompress(xz_path, self.decompressdir)
        self.assertEqual(ret, os.path.join(self.decompressdir, 'avocado'))

    def test_lzma_uncompress_to_file(self):
        xz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.xz')
        filename = os.path.join(self.decompressdir, 'other')
        ret = archive.lzma_uncompress(xz_path, filename)
        self.assertEqual(ret, filename)

    def test_lzma_is_archive(self):
        xz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.xz')
        self.assertTrue(archive.is_archive(xz_path))

    def test_null_lzma_is_not_archive(self):
        self.assertFalse(archive.is_archive(os.devnull))

    def test_uncompress_lzma(self):
        xz_path = os.path.join(BASEDIR, 'selftests', '.data', 'avocado.xz')
        ret = archive.uncompress(xz_path, self.decompressdir)
        self.assertEqual(ret, os.path.join(self.decompressdir, 'avocado'))
        with open(ret, 'rb') as decompressed:
            self.assertEqual(decompressed.read(), b'avocado\n')

    def tearDown(self):
        try:
            self.basedir.cleanup()
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main()
