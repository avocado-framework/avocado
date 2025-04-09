import hashlib
import json
import os
import random
import sys
import tempfile
import unittest

from avocado.utils import archive, crypto, data_factory
from selftests.utils import BASEDIR, temp_dir_prefix

ZSTD_AVAILABLE = archive.probe_zstd_cmd() is not None


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.basedir = tempfile.TemporaryDirectory(prefix=prefix)
        self.compressdir = tempfile.mkdtemp(dir=self.basedir.name)
        self.decompressdir = tempfile.mkdtemp(dir=self.basedir.name)
        self.sys_random = random.SystemRandom()

        # Use the golden archives from selftests/.data/archive.py.data
        self.test_data_dir = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data"
        )

        # Path to test file for verification
        self.test_file_path = os.path.join(self.test_data_dir, "test_file.txt")
        try:
            with open(self.test_file_path, "r", encoding="utf-8") as f:
                self.test_file_content = f.read()
        except FileNotFoundError:
            # If the file doesn't exist, use a default content
            self.test_file_content = "This is a test file for archive testing."

    def compress_and_check_dir(self, extension):
        hash_map_1 = {}
        for i in range(self.sys_random.randint(10, 20)):
            if i % 2 == 0:
                compressdir = tempfile.mkdtemp(dir=self.compressdir)
            else:
                compressdir = self.compressdir
            str_length = self.sys_random.randint(30, 50)
            fd, filename = tempfile.mkstemp(dir=compressdir, text=True)
            with os.fdopen(fd, "w") as f:
                f.write(data_factory.generate_random_string(str_length))
            relative_path = filename.replace(self.compressdir, "")
            hash_map_1[relative_path] = crypto.hash_file(filename)

        archive_filename = self.compressdir + extension
        archive.compress(archive_filename, self.compressdir)
        archive.uncompress(archive_filename, self.decompressdir)

        hash_map_2 = {}
        for root, _, files in os.walk(self.decompressdir):
            for name in files:
                file_path = os.path.join(root, name)
                relative_path = file_path.replace(self.decompressdir, "")
                hash_map_2[relative_path] = crypto.hash_file(file_path)

        self.assertEqual(hash_map_1, hash_map_2)

    def compress_and_check_file(self, extension):
        str_length = self.sys_random.randint(30, 50)
        fd, filename = tempfile.mkstemp(dir=self.basedir.name, text=True)
        with os.fdopen(fd, "w") as f:
            f.write(data_factory.generate_random_string(str_length))
        original_hash = crypto.hash_file(filename)
        dstfile = filename + extension
        archive_filename = os.path.join(self.basedir.name, dstfile)
        archive.compress(archive_filename, filename)
        extracted_path = archive.uncompress(archive_filename, self.basedir.name)
        # Adjust assertion for destination directory
        # Check if extracted_path is not None before comparing basenames
        self.assertIsNotNone(
            extracted_path, "uncompress should return the extracted file path"
        )
        # Compare basenames as uncompress returns relative path for archives
        self.assertEqual(os.path.basename(extracted_path), os.path.basename(filename))
        decompress_file = os.path.join(self.basedir.name, os.path.basename(filename))
        decompress_hash = crypto.hash_file(decompress_file)
        self.assertEqual(original_hash, decompress_hash)

    def test_zip_dir(self):
        self.compress_and_check_dir(".zip")

    def test_zip_file(self):
        self.compress_and_check_file(".zip")

    def test_tar_dir(self):
        self.compress_and_check_dir(".tar")

    def test_tar_file(self):
        self.compress_and_check_file(".tar")

    def test_tgz_dir(self):
        self.compress_and_check_dir(".tar.gz")

    def test_tgz_file(self):
        self.compress_and_check_file(".tar.gz")

    def test_tbz2_dir(self):
        self.compress_and_check_dir(".tar.bz2")

    def test_tbz2_file(self):
        self.compress_and_check_file(".tar.bz2")

    @unittest.skipIf(
        sys.platform.startswith("darwin"),
        "macOS does not support archive extra attributes",
    )
    def test_zip_extra_attrs(self):
        """
        Check that utils.archive reflects extra attrs of file like symlinks
        and file permissions.
        """

        def get_path(*args):
            """Get path with decompressdir prefix"""
            return os.path.join(self.basedir.name, *args)

        # File types
        zip_path = os.path.abspath(
            os.path.join(
                BASEDIR,
                "selftests",
                ".data",
                "archive.py.data",
                "test_archive__symlinks.zip",
            )
        )
        # TODO: Handle permission correctly for all users
        # The umask is not yet handled by utils.archive, hardcode it for now
        os.umask(2)
        archive.uncompress(zip_path, self.basedir.name)
        self.assertTrue(os.path.islink(get_path("link_to_dir")))
        self.assertTrue(os.path.islink(get_path("link_to_file")))
        self.assertTrue(os.path.islink(get_path("link_to_file2")))
        self.assertTrue(os.path.islink(get_path("dir", "2nd_link_to_file")))
        self.assertTrue(os.path.islink(get_path("dir", "link_to_link_to_file2")))
        self.assertTrue(os.path.islink(get_path("dir", "2nd_link_to_file")))
        self.assertTrue(os.path.islink(get_path("link_to_dir", "2nd_link_to_file")))
        self.assertTrue(os.path.isfile(get_path("file")))
        self.assertTrue(os.path.isfile(get_path("dir", "file2")))
        self.assertTrue(os.path.isfile(get_path("link_to_dir", "file2")))
        act = os.path.realpath(get_path("link_to_dir", "link_to_link_to_file2"))
        exp = get_path("dir", "file2")
        self.assertEqual(act, exp)
        self.assertEqual(os.path.realpath(get_path("link_to_dir")), get_path("dir"))
        # File permissions
        self.assertEqual(os.stat(get_path("dir", "file2")).st_mode & 0o777, 0o664)
        self.assertEqual(os.stat(get_path("file")).st_mode & 0o777, 0o753)
        self.assertEqual(os.stat(get_path("dir")).st_mode & 0o777, 0o775)
        self.assertEqual(os.stat(get_path("link_to_file2")).st_mode & 0o777, 0o664)
        self.assertEqual(os.stat(get_path("link_to_dir")).st_mode & 0o777, 0o775)
        self.assertEqual(os.stat(get_path("link_to_file")).st_mode & 0o777, 0o753)

    def test_empty_tbz2(self):
        extracted_path = archive.uncompress(
            os.path.join(
                BASEDIR, "selftests", ".data", "archive.py.data", "empty.tar.bz2"
            ),
            self.basedir.name,
        )
        self.assertEqual(
            extracted_path,
            None,
            (f"Empty archive should return None " f"({extracted_path})"),
        )

    def test_is_gzip_file(self):
        gz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.gz"
        )
        self.assertTrue(archive.is_gzip_file(gz_path))

    def test_gzip_uncompress_to_dir(self):
        gz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.gz"
        )
        extracted_path = archive.gzip_uncompress(gz_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))

    def test_gzip_uncompress_to_file(self):
        gz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.gz"
        )
        filename = os.path.join(self.basedir.name, "other")
        extracted_path = archive.gzip_uncompress(gz_path, filename)
        self.assertEqual(extracted_path, filename)

    def test_gzip_is_archive(self):
        gz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.gz"
        )
        self.assertTrue(archive.is_archive(gz_path))

    def test_uncompress_gzip(self):
        gz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.gz"
        )
        extracted_path = archive.uncompress(gz_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))
        with open(extracted_path, "rb") as decompressed:
            self.assertEqual(decompressed.read(), b"avocado\n")

    def test_is_lzma_file(self):
        xz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.xz"
        )
        self.assertTrue(archive.is_lzma_file(xz_path))

    def test_null_is_not_lzma_file(self):
        self.assertFalse(archive.is_lzma_file(os.devnull))

    def test_lzma_uncompress_to_dir(self):
        xz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.xz"
        )
        extracted_path = archive.lzma_uncompress(xz_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))

    def test_lzma_uncompress_to_file(self):
        xz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.xz"
        )
        filename = os.path.join(self.basedir.name, "other")
        extracted_path = archive.lzma_uncompress(xz_path, filename)
        self.assertEqual(extracted_path, filename)

    def test_lzma_is_archive(self):
        xz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.xz"
        )
        self.assertTrue(archive.is_archive(xz_path))

    def test_uncompress_lzma(self):
        xz_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.xz"
        )
        extracted_path = archive.uncompress(xz_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))
        with open(extracted_path, "rb") as decompressed:
            self.assertEqual(decompressed.read(), b"avocado\n")

    def test_is_zstd_file(self):
        zstd_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.zst"
        )
        self.assertTrue(archive.is_zstd_file(zstd_path))

    def test_null_is_not_zstd_file(self):
        self.assertFalse(archive.is_zstd_file(os.devnull))

    def test_zstd_is_archive(self):
        zstd_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.zst"
        )
        self.assertTrue(archive.is_archive(zstd_path))

    @unittest.skipUnless(ZSTD_AVAILABLE, "zstd tool is not available")
    def test_zstd_uncompress_to_dir(self):
        zstd_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.zst"
        )
        extracted_path = archive.zstd_uncompress(zstd_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))

    @unittest.skipUnless(ZSTD_AVAILABLE, "zstd tool is not available")
    def test_zstd_uncompress_to_file(self):
        zstd_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.zst"
        )
        filename = os.path.join(self.basedir.name, "other")
        extracted_path = archive.zstd_uncompress(zstd_path, filename)
        self.assertEqual(extracted_path, filename)

    @unittest.skipUnless(ZSTD_AVAILABLE, "zstd tool is not available")
    def test_uncompress_zstd(self):
        zstd_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "avocado.zst"
        )
        extracted_path = archive.uncompress(zstd_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "avocado"))
        with open(extracted_path, "rb") as decompressed:
            self.assertEqual(decompressed.read(), b"avocado\n")

    def test_is_bzip2_file(self):
        # Test with extension
        bz2_path_ext = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "test_file.bz2"
        )
        self.assertTrue(archive.is_bzip2_file(bz2_path_ext))
        # Test without extension (using the golden file)
        bz2_path_noext = os.path.join(self.test_data_dir, "bzip2file")
        self.assertTrue(archive.is_bzip2_file(bz2_path_noext))

    def test_null_is_not_bzip2_file(self):
        self.assertFalse(archive.is_bzip2_file(os.devnull))

    def test_bzip2_uncompress_to_dir(self):
        bz2_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "test_file.bz2"
        )
        extracted_path = archive.bzip2_uncompress(bz2_path, self.basedir.name)
        self.assertEqual(extracted_path, os.path.join(self.basedir.name, "test_file"))
        with open(extracted_path, "rb") as decompressed:
            self.assertEqual(
                decompressed.read().decode("utf-8"), self.test_file_content
            )

    def test_bzip2_uncompress_without_extension(self):
        """Test bzip2_uncompress on a file without standard extension."""
        bz2_path_noext = os.path.join(self.test_data_dir, "bzip2file")
        extracted_path = archive.bzip2_uncompress(bz2_path_noext, self.basedir.name)
        # The output path should be based on the input filename without extension
        # Since input is 'bzip2file', output should be 'bzip2file' in the target dir
        expected_output_path = os.path.join(self.basedir.name, "bzip2file")
        self.assertEqual(extracted_path, expected_output_path)
        with open(extracted_path, "rb") as decompressed:
            # Assuming 'bzip2file' contains the same content as 'avocado.bz2'
            self.assertEqual(
                decompressed.read().decode("utf-8"), self.test_file_content
            )

    def test_bzip2_uncompress_to_file(self):
        bz2_path = os.path.join(
            BASEDIR, "selftests", ".data", "archive.py.data", "test_file.bz2"
        )
        filename = os.path.join(self.basedir.name, "other_bz2")
        # Assuming avocado.utils.archive now has bzip2_uncompress
        extracted_path = archive.bzip2_uncompress(bz2_path, filename)
        self.assertEqual(extracted_path, filename)
        with open(extracted_path, "rb") as decompressed:
            self.assertEqual(
                decompressed.read().decode("utf-8"), self.test_file_content
            )

    def test_null_is_not_archive(self):
        self.assertFalse(archive.is_archive(os.devnull))

    def _get_archive_metadata(self, archive_path):
        """Get metadata for an archive if it exists"""
        metadata_path = f"{archive_path}.metadata"
        if os.path.exists(metadata_path):
            with open(metadata_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _calculate_file_hash(self, file_path):
        """Calculate SHA-256 hash of a file"""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _verify_file_hash(self, file_path, expected_hash):
        """Verify that a file's hash matches the expected hash"""
        # Skip hash verification for symlinks
        if expected_hash.startswith("symlink:"):
            return True

        actual_hash = self._calculate_file_hash(file_path)
        return actual_hash == expected_hash

    # Tests for archives without extensions

    def test_tar_without_extension(self):
        """Test that tar archives without proper extensions can be opened."""
        # Use the existing tar archive without extension
        tar_file = os.path.join(self.test_data_dir, "tarfile")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(tar_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(tar_file)

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(tar_file) as arch:
                # Just opening it is enough to verify our fix works
                self.assertIsNotNone(arch)
                # List the contents to verify it's a valid archive
                files = arch._engine.getnames()
                self.assertTrue(len(files) > 0, "Archive should contain files")

                # If we have metadata, verify the contents match
                if metadata and "members" in metadata:
                    # Extract the archive to verify hash
                    extract_dir = os.path.join(self.basedir.name, "extract_tar_test")
                    os.makedirs(extract_dir, exist_ok=True)
                    arch.extract(extract_dir)

                    for member, expected_hash in metadata["members"]:
                        found = False
                        member_path = None
                        for path in files:
                            if member in path:
                                found = True
                                member_path = os.path.join(extract_dir, path)
                                break
                        self.assertTrue(found, f"{member} should be in the archive")

                        # Verify the hash if the file was found
                        if (
                            found
                            and member_path
                            and os.path.exists(member_path)
                            and not os.path.islink(member_path)
                        ):
                            self.assertTrue(
                                self._verify_file_hash(member_path, expected_hash),
                                f"Hash mismatch for {member}: expected {expected_hash}",
                            )
                else:
                    # Fallback to basic check
                    found = False
                    for path in files:
                        if "test_file.txt" in path:
                            found = True
                            break
                    self.assertTrue(found, "test_file.txt should be in the archive")
        except archive.ArchiveException as e:
            self.fail(f"Failed to open archive without extension: {e}")

    def test_zip_without_extension(self):
        """Test that ZIP archives without proper extensions can be opened."""
        # Use the existing zip archive without extension
        zip_file = os.path.join(self.test_data_dir, "zipfile")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zip_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(zip_file)

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(zip_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.namelist()
                self.assertTrue(len(files) > 0, "Archive should contain files")

                # If we have metadata, verify the contents match
                if metadata and "members" in metadata:
                    # Extract the archive to verify hash
                    extract_dir = os.path.join(self.basedir.name, "extract_zip_test")
                    os.makedirs(extract_dir, exist_ok=True)
                    arch.extract(extract_dir)

                    for member, expected_hash in metadata["members"]:
                        self.assertIn(
                            member, files, f"{member} should be in the archive"
                        )

                        # Verify the hash if the file was found
                        member_path = os.path.join(extract_dir, member)
                        if os.path.exists(member_path) and not os.path.islink(
                            member_path
                        ):
                            self.assertTrue(
                                self._verify_file_hash(member_path, expected_hash),
                                f"Hash mismatch for {member}: expected {expected_hash}",
                            )
                else:
                    # Fallback to basic check
                    self.assertIn(
                        "test_file.txt", files, "test_file.txt should be in the archive"
                    )
        except archive.ArchiveException as e:
            self.fail(f"Failed to open ZIP archive without extension: {e}")

    def test_gzip_without_extension(self):
        """Test that gzip archives without proper extensions can be detected and extracted."""
        # Use the existing gzip archive without extension
        gzip_file = os.path.join(self.test_data_dir, "gzipfile")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(gzip_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(gzip_file)

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_gzip")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(gzip_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(gzip_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For gzip files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    def test_xz_without_extension(self):
        """Test that xz archives without proper extensions can be detected and extracted."""
        # Use the existing xz archive without extension
        xz_file = os.path.join(self.test_data_dir, "xzfile")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(xz_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(xz_file)

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_xz")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(xz_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(xz_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For xz files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    def test_bzip2_without_extension(self):
        """Test that bzip2 archives without proper extensions can be detected and extracted."""
        # Use the existing bzip2 archive without extension
        bzip2_file = os.path.join(self.test_data_dir, "bzip2file")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(bzip2_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(bzip2_file)

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_bzip2")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(bzip2_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(bzip2_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For bzip2 files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    # Tests for archives with extensions

    def test_tar_with_extension(self):
        """Test that tar archives with proper extensions can be opened."""
        # Use the existing tar archive with extension
        tar_file = os.path.join(self.test_data_dir, "archive.tar")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(tar_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(tar_file)

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(tar_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.getnames()
                self.assertTrue(len(files) > 0, "Archive should contain files")

                # If we have metadata, verify the contents match
                if metadata and "members" in metadata:
                    # Extract the archive to verify hash
                    extract_dir = os.path.join(self.basedir.name, "extract_tar_ext")
                    os.makedirs(extract_dir, exist_ok=True)
                    arch.extract(extract_dir)

                    for member, expected_hash in metadata["members"]:
                        found = False
                        member_path = None
                        for path in files:
                            if member in path:
                                found = True
                                member_path = os.path.join(extract_dir, path)
                                break
                        self.assertTrue(found, f"{member} should be in the archive")

                        # Verify the hash if the file was found
                        if (
                            found
                            and member_path
                            and os.path.exists(member_path)
                            and not os.path.islink(member_path)
                        ):
                            self.assertTrue(
                                self._verify_file_hash(member_path, expected_hash),
                                f"Hash mismatch for {member}: expected {expected_hash}",
                            )
                else:
                    # Fallback to basic check
                    found = False
                    for path in files:
                        if "test_file.txt" in path:
                            found = True
                            break
                    self.assertTrue(found, "test_file.txt should be in the archive")
        except archive.ArchiveException as e:
            self.fail(f"Failed to open tar archive with extension: {e}")

    def test_zip_with_extension(self):
        """Test that ZIP archives with proper extensions can be opened."""
        # Use the existing zip archive with extension
        zip_file = os.path.join(self.test_data_dir, "archive.zip")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zip_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(zip_file)

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(zip_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.namelist()
                self.assertTrue(len(files) > 0, "Archive should contain files")

                # If we have metadata, verify the contents match
                if metadata and "members" in metadata:
                    # Extract the archive to verify hash
                    extract_dir = os.path.join(self.basedir.name, "extract_zip_ext")
                    os.makedirs(extract_dir, exist_ok=True)
                    arch.extract(extract_dir)

                    for member, expected_hash in metadata["members"]:
                        self.assertIn(
                            member, files, f"{member} should be in the archive"
                        )

                        # Verify the hash if the file was found
                        member_path = os.path.join(extract_dir, member)
                        if os.path.exists(member_path) and not os.path.islink(
                            member_path
                        ):
                            self.assertTrue(
                                self._verify_file_hash(member_path, expected_hash),
                                f"Hash mismatch for {member}: expected {expected_hash}",
                            )
                else:
                    # Fallback to basic check
                    self.assertIn(
                        "test_file.txt", files, "test_file.txt should be in the archive"
                    )
        except archive.ArchiveException as e:
            self.fail(f"Failed to open ZIP archive with extension: {e}")

    def test_gzip_with_extension(self):
        """Test that gzip archives with proper extensions can be detected and extracted."""
        # Use the existing gzip archive with extension
        gzip_file = os.path.join(self.test_data_dir, "test_file.gz")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(gzip_file))

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_gzip_ext")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(gzip_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(gzip_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For gzip files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    def test_xz_with_extension(self):
        """Test that xz archives with proper extensions can be detected and extracted."""
        # Use the existing xz archive with extension
        xz_file = os.path.join(self.test_data_dir, "test_file.xz")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(xz_file))

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_xz_ext")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(xz_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(xz_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For xz files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    @unittest.skipUnless(ZSTD_AVAILABLE, "zstd tool is not available")
    def test_zstd_without_extension(self):
        """Test that zstd archives without proper extensions can be detected and extracted."""
        # Use the existing zstd archive without extension (assuming it exists)
        zstd_file = os.path.join(self.test_data_dir, "zstdfile")
        if not os.path.exists(zstd_file):
            self.skipTest(f"Test data file not found: {zstd_file}")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zstd_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(zstd_file)

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_zstd_noext")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(zstd_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For zstd files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    @unittest.skipUnless(ZSTD_AVAILABLE, "zstd tool is not available")
    def test_zstd_with_extension(self):
        """Test that zstd archives with proper extensions can be detected and extracted."""
        # Use the existing zstd archive with extension (assuming it exists)
        zstd_file = os.path.join(self.test_data_dir, "test_file.zst")
        if not os.path.exists(zstd_file):
            self.skipTest(f"Test data file not found: {zstd_file}")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zstd_file))

        # Check metadata if available
        metadata = self._get_archive_metadata(zstd_file)

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_zstd_ext")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(zstd_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For zstd files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    def test_bzip2_with_extension(self):
        """Test that bzip2 archives with proper extensions can be detected and extracted."""
        # Use the existing bzip2 archive with extension
        bzip2_file = os.path.join(self.test_data_dir, "test_file.bz2")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(bzip2_file))

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_bzip2_ext")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(bzip2_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        # Check content if possible
        try:
            with open(extracted_file, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertEqual(content, self.test_file_content)
        except UnicodeDecodeError:
            # If not a text file, just verify it exists
            pass

        # Verify hash if metadata is available
        metadata = self._get_archive_metadata(bzip2_file)
        if metadata and "members" in metadata:
            for _, expected_hash in metadata["members"]:
                # For bzip2 files, the member name might not match the extracted file name
                # So we check if the extracted file exists and verify its hash
                if os.path.exists(extracted_file) and not os.path.islink(
                    extracted_file
                ):
                    self.assertTrue(
                        self._verify_file_hash(extracted_file, expected_hash),
                        f"Hash mismatch for extracted file: expected {expected_hash}",
                    )

    def test_metadata_support(self):
        """Test that metadata files are correctly read and used for verification."""
        # Test with an archive that has metadata
        tar_file = os.path.join(self.test_data_dir, "archive.tar")
        metadata = self._get_archive_metadata(tar_file)
        self.assertIsNotNone(metadata, "Metadata should exist for archive.tar")
        self.assertIn("members", metadata, "Metadata should contain 'members' key")

        # Extract the archive
        extract_dir = os.path.join(self.basedir.name, "extract_metadata_test")
        os.makedirs(extract_dir, exist_ok=True)
        with archive.ArchiveFile.open(tar_file) as arch:
            arch.extract(extract_dir)

        # Verify hashes using metadata
        for member, expected_hash in metadata["members"]:
            member_path = os.path.join(extract_dir, member)
            if os.path.exists(member_path) and not os.path.islink(member_path):
                self.assertTrue(
                    self._verify_file_hash(member_path, expected_hash),
                    f"Hash mismatch for {member}: expected {expected_hash}",
                )
            elif expected_hash.startswith("symlink:"):
                self.assertTrue(
                    os.path.islink(member_path), f"{member} should be a symlink"
                )
                link_target = os.readlink(member_path)
                expected_target = expected_hash.split(":", 1)[1]
                self.assertEqual(
                    link_target,
                    expected_target,
                    f"Symlink target mismatch for {member}",
                )

    def tearDown(self):
        try:
            # Use self.basedir consistently
            self.basedir.cleanup()
        except OSError:
            pass


if __name__ == "__main__":
    unittest.main()
