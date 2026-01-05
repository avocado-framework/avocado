import hashlib
import os
import unittest

from avocado.utils import crypto
from selftests.utils import TestCaseTmpDir


class HashFileFunctionalTest(TestCaseTmpDir):
    """Functional tests for crypto.hash_file with real-world scenarios."""

    def test_download_verification_with_known_checksums(self):
        """
        Test verifying a downloaded file against published checksums.

        Real-world scenario: Package managers and download sites publish
        checksums that users verify after downloading. This test uses
        a well-known test vector with pre-computed checksums.
        """
        content = b"The quick brown fox jumps over the lazy dog"
        filepath = os.path.join(self.tmpdir.name, "downloaded_file.bin")
        with open(filepath, "wb") as f:
            f.write(content)

        self.assertEqual(
            crypto.hash_file(filepath, algorithm="md5"),
            "9e107d9d372bb6826bd81d3542a419d6",
        )
        self.assertEqual(
            crypto.hash_file(filepath, algorithm="sha256"),
            "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592",
        )

    def test_file_tampering_detection(self):
        """
        Test detecting file modification through hash comparison.

        Real-world scenario: Security systems use hashes to detect if
        files have been tampered with. This tests the complete workflow.
        """
        filepath = os.path.join(self.tmpdir.name, "secure_config.conf")

        with open(filepath, "wb") as f:
            f.write(b"secure_setting=true\npassword_hash=abc123")
        original_hash = crypto.hash_file(filepath, algorithm="sha256")

        with open(filepath, "wb") as f:
            f.write(b"secure_setting=false\npassword_hash=abc123")
        tampered_hash = crypto.hash_file(filepath, algorithm="sha256")

        self.assertNotEqual(original_hash, tampered_hash)

    def test_create_file_manifest(self):
        """
        Test creating a manifest of file checksums for a directory.

        Real-world scenario: Build systems and package managers create
        manifests listing checksums of all files for verification.
        """
        files = {
            "src/main.py": b"print('hello')",
            "src/utils.py": b"def helper(): pass",
            "data/config.json": b'{"key": "value"}',
        }

        manifest = {}
        for relpath, content in files.items():
            filepath = os.path.join(self.tmpdir.name, relpath)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(content)
            manifest[relpath] = crypto.hash_file(filepath, algorithm="sha256")

        for relpath, content in files.items():
            expected = hashlib.sha256(content).hexdigest()
            self.assertEqual(manifest[relpath], expected)

        self.assertEqual(len(set(manifest.values())), len(files))

    def test_symlink_follows_to_target(self):
        """
        Test that hashing through symlink produces same result as original.

        Real-world scenario: Linux systems use symlinks extensively;
        hash verification must work regardless of access path.
        """
        original = os.path.join(self.tmpdir.name, "original.bin")
        symlink = os.path.join(self.tmpdir.name, "link.bin")

        with open(original, "wb") as f:
            f.write(b"Linked content")
        os.symlink(original, symlink)

        self.assertEqual(crypto.hash_file(original), crypto.hash_file(symlink))


if __name__ == "__main__":
    unittest.main()
