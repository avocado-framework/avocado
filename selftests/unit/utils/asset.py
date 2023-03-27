import os
import tempfile
import unittest

from avocado.utils.asset import Asset
from selftests.utils import TestCaseTmpDir, setup_avocado_loggers

setup_avocado_loggers()


class TestAsset(TestCaseTmpDir):
    def setUp(self):
        super().setUp()
        assetname = "foo.tgz"
        assethash = "3a033a8938c1af56eeb793669db83bcbd0c17ea5"
        cache_dir = tempfile.mkdtemp(dir=self.tmpdir.name)
        self.assetpath = os.path.join(cache_dir, assetname)
        with open(self.assetpath, "w", encoding="utf-8") as f:
            f.write("Test!")
        self.hash_file = Asset._get_hash_file(self.assetpath)
        with open(self.hash_file, "w", encoding="utf-8") as f:
            f.write(f"sha1 {assethash}i\n")

    def test_has_valid_hash_different_algorithm(self):
        hash_algorithm = "md5"
        md5_hash = "a258ca9eb8765b2b5541f42c9b232226"
        result = Asset._has_valid_hash(self.assetpath, md5_hash, hash_algorithm)
        msg = (
            "Asset._has_valid_hash doesn't confirm valid hash with "
            "different algorithm"
        )
        self.assertTrue(result, msg)

    def test_refuses_invalid_hash(self):
        hash_algorithm = "md5"
        md5_hash = "3a033a8938c1af56eeb793669db83bcbd0c17ea5"
        result = Asset._has_valid_hash(self.assetpath, md5_hash, hash_algorithm)
        msg = (
            "Asset._has_valid_hash doesn't refuse the invalid hash with"
            "different algorithm."
        )
        self.assertFalse(result, msg)

    def test_adds_valid_hash(self):
        hash_algorithm = "md5"
        md5_hash = "a258ca9eb8765b2b5541f42c9b232226"
        result = Asset._has_valid_hash(self.assetpath, md5_hash, hash_algorithm)
        with open(self.hash_file, "r", encoding="utf-8") as f:
            result = len(f.readlines())
        msg = "Assets._has_valid_hash doesn't add new hash entry to hash file"
        self.assertEqual(result, 2, msg)

    def test_adds_hash_multiple_times(self):
        hash_algorithm = "md5"
        md5_hash = "a258ca9eb8765b2b5541f42c9b232226"
        Asset._add_hash_to_hash_file(self.hash_file, md5_hash, hash_algorithm)
        Asset._add_hash_to_hash_file(self.hash_file, md5_hash, hash_algorithm)
        with open(self.hash_file, "r", encoding="utf-8") as f:
            result = len(f.readlines())
        msg = "Assets.Assets._has_valid_hash added the same hash multiple times"
        self.assertEqual(result, 2, msg)


if __name__ == "__main__":
    unittest.main()
