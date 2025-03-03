import hashlib
import json
import os
import tempfile
import unittest

from avocado.utils import archive
from selftests.utils import BASEDIR


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="avocado_" + __name__)
        self.base_dir = self.tmpdir.name

        # Use the golden archives from selftests/.data/test_archive
        self.test_data_dir = os.path.join(BASEDIR, "selftests", ".data", "test_archive")

        # Path to test file for verification
        self.test_file_path = os.path.join(self.test_data_dir, "test_file.txt")
        try:
            with open(self.test_file_path, "r", encoding="utf-8") as f:
                self.test_file_content = f.read()
        except FileNotFoundError:
            # If the file doesn't exist, use a default content
            self.test_file_content = "This is a test file for archive testing."

    def tearDown(self):
        self.tmpdir.cleanup()

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
                    extract_dir = os.path.join(self.base_dir, "extract_tar_test")
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
                    extract_dir = os.path.join(self.base_dir, "extract_zip_test")
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
        extract_dir = os.path.join(self.base_dir, "extract_gzip")
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
        extract_dir = os.path.join(self.base_dir, "extract_xz")
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
        extract_dir = os.path.join(self.base_dir, "extract_bzip2")
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
                    extract_dir = os.path.join(self.base_dir, "extract_tar_ext")
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
                    extract_dir = os.path.join(self.base_dir, "extract_zip_ext")
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
        extract_dir = os.path.join(self.base_dir, "extract_gzip_ext")
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
        extract_dir = os.path.join(self.base_dir, "extract_xz_ext")
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

    def test_bzip2_with_extension(self):
        """Test that bzip2 archives with proper extensions can be detected and extracted."""
        # Use the existing bzip2 archive with extension
        bzip2_file = os.path.join(self.test_data_dir, "test_file.bz2")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(bzip2_file))

        # Extract the archive
        extract_dir = os.path.join(self.base_dir, "extract_bzip2_ext")
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
        """Test that archive metadata files are properly handled if they exist."""
        # Create a sample metadata file for testing
        avocado_gz = os.path.join(self.test_data_dir, "avocado.gz")
        metadata_path = os.path.join(self.base_dir, "avocado.gz.metadata")

        # Create a sample metadata file
        metadata = {
            "members": [
                [
                    "avocado",
                    "f6bd93091d5d3df733b53b490f92b8a3f1a7b893928a21f8b0f96d1015b5490d",
                ]
            ]
        }

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

        # Test that we can read the metadata
        read_metadata = self._get_archive_metadata(
            os.path.join(self.base_dir, "avocado.gz")
        )
        self.assertEqual(read_metadata, metadata)

        # Extract the archive and verify the hash
        extract_dir = os.path.join(self.base_dir, "extract_metadata_test")
        os.makedirs(extract_dir, exist_ok=True)
        archive.extract(avocado_gz, extract_dir)

        # Verify the hash of the extracted file
        for member, expected_hash in metadata["members"]:
            member_path = os.path.join(extract_dir, member)
            if os.path.exists(member_path):
                self.assertTrue(
                    self._verify_file_hash(member_path, expected_hash),
                    f"Hash mismatch for {member}: expected {expected_hash}",
                )


if __name__ == "__main__":
    unittest.main()
