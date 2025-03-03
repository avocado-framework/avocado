import os
import tempfile
import unittest

from avocado.utils import archive, process


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory(prefix="avocado_" + __name__)
        self.base_dir = self.tmpdir.name

        # Create a simple text file to archive
        self.test_file = os.path.join(self.base_dir, "test_file.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("This is a test file for archive testing.")

    def tearDown(self):
        self.tmpdir.cleanup()

    # Tests for archives without extensions

    def test_tar_without_extension(self):
        """Test that tar archives without proper extensions can be opened."""
        # Create a tar archive without extension
        tar_file = os.path.join(self.base_dir, "tarfile")

        # Create a tar file without extension
        process.run(f"tar cf {tar_file} {self.test_file}")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(tar_file))

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(tar_file) as arch:
                # Just opening it is enough to verify our fix works
                self.assertIsNotNone(arch)
                # List the contents to verify it's a valid archive
                files = arch._engine.getnames()
                self.assertTrue(len(files) > 0, "Archive should contain files")
                # The path in the archive might be absolute or relative
                # Just check that the filename is in one of the paths
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
        import zipfile

        # Create a zip archive without extension
        zip_file = os.path.join(self.base_dir, "zipfile")

        # Create a zip file without extension using Python's zipfile module
        with zipfile.ZipFile(zip_file, "w") as zip_out:
            zip_out.write(self.test_file, arcname=os.path.basename(self.test_file))

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zip_file))

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(zip_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.namelist()
                self.assertTrue(len(files) > 0, "Archive should contain files")
                self.assertIn(
                    "test_file.txt", files, "test_file.txt should be in the archive"
                )
        except archive.ArchiveException as e:
            self.fail(f"Failed to open ZIP archive without extension: {e}")

    def test_gzip_without_extension(self):
        """Test that gzip archives without proper extensions can be detected and extracted."""
        import gzip

        # Create a gzip archive without extension
        gzip_file = os.path.join(self.base_dir, "gzipfile")

        # Create a gzip file without extension using Python's gzip module
        with open(self.test_file, "rb") as f_in:
            with gzip.open(gzip_file, "wb") as f_out:
                f_out.write(f_in.read())

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(gzip_file))

        # Extract the archive
        extract_dir = os.path.join(self.base_dir, "extract_gzip")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(gzip_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        with open(extracted_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "This is a test file for archive testing.")

    def test_xz_without_extension(self):
        """Test that xz archives without proper extensions can be detected and extracted."""
        import lzma

        # Create an xz archive without extension
        xz_file = os.path.join(self.base_dir, "xzfile")

        # Create an xz file without extension using Python's lzma module
        with open(self.test_file, "rb") as f_in:
            with lzma.open(xz_file, "wb") as f_out:
                f_out.write(f_in.read())

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(xz_file))

        # Extract the archive
        extract_dir = os.path.join(self.base_dir, "extract_xz")
        os.makedirs(extract_dir, exist_ok=True)
        extracted_file = archive.extract(xz_file, extract_dir)

        # Verify the file was extracted
        self.assertTrue(
            os.path.exists(extracted_file),
            f"Extracted file not found at {extracted_file}",
        )

        with open(extracted_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "This is a test file for archive testing.")

    def test_bzip2_without_extension(self):
        """Test that bzip2 archives without proper extensions can be detected and extracted."""
        import bz2

        # Create a bzip2 archive without extension
        bz2_file = os.path.join(self.base_dir, "bz2file")

        # Create a bzip2 file without extension using Python's bz2 module
        with open(self.test_file, "rb") as f_in:
            with bz2.open(bz2_file, "wb") as f_out:
                f_out.write(f_in.read())

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(bz2_file))

        # Since bzip2 is not directly supported in the extract function,
        # we'll just verify it's detected correctly
        self.assertTrue(archive.is_archive(bz2_file))

    # Tests for archives with extensions

    def test_tar_with_extension(self):
        """Test that tar archives with proper extensions can be opened."""
        # Create a tar archive with extension
        tar_file = os.path.join(self.base_dir, "archive.tar")

        # Create a tar file with extension
        process.run(f"tar cf {tar_file} {self.test_file}")

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(tar_file))

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(tar_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.getnames()
                self.assertTrue(len(files) > 0, "Archive should contain files")
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
        import zipfile

        # Create a zip archive with extension
        zip_file = os.path.join(self.base_dir, "archive.zip")

        # Create a zip file with extension
        with zipfile.ZipFile(zip_file, "w") as zip_out:
            zip_out.write(self.test_file, arcname=os.path.basename(self.test_file))

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(zip_file))

        # Verify we can open it with ArchiveFile
        try:
            with archive.ArchiveFile.open(zip_file) as arch:
                self.assertIsNotNone(arch)
                files = arch._engine.namelist()
                self.assertTrue(len(files) > 0, "Archive should contain files")
                self.assertIn(
                    "test_file.txt", files, "test_file.txt should be in the archive"
                )
        except archive.ArchiveException as e:
            self.fail(f"Failed to open ZIP archive with extension: {e}")

    def test_gzip_with_extension(self):
        """Test that gzip archives with proper extensions can be detected and extracted."""
        import gzip

        # Create a gzip archive with extension
        gzip_file = os.path.join(self.base_dir, "test_file.gz")

        # Create a gzip file with extension
        with open(self.test_file, "rb") as f_in:
            with gzip.open(gzip_file, "wb") as f_out:
                f_out.write(f_in.read())

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

        with open(extracted_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "This is a test file for archive testing.")

    def test_xz_with_extension(self):
        """Test that xz archives with proper extensions can be detected and extracted."""
        import lzma

        # Create an xz archive with extension
        xz_file = os.path.join(self.base_dir, "test_file.xz")

        # Create an xz file with extension
        with open(self.test_file, "rb") as f_in:
            with lzma.open(xz_file, "wb") as f_out:
                f_out.write(f_in.read())

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

        with open(extracted_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "This is a test file for archive testing.")

    def test_bzip2_with_extension(self):
        """Test that bzip2 archives with proper extensions can be detected."""
        import bz2

        # Create a bzip2 archive with extension
        bz2_file = os.path.join(self.base_dir, "test_file.bz2")

        # Create a bzip2 file with extension
        with open(self.test_file, "rb") as f_in:
            with bz2.open(bz2_file, "wb") as f_out:
                f_out.write(f_in.read())

        # Verify it's detected as an archive
        self.assertTrue(archive.is_archive(bz2_file))


if __name__ == "__main__":
    unittest.main()
