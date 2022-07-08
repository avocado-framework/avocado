import unittest

from avocado.core.test_id import TestID
from avocado.utils import astring, path


class Test(unittest.TestCase):
    def test_uid_name(self):
        uid = 1
        name = "file.py:klass.test_method"
        test_id = TestID(uid, name)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, "1")
        self.assertEqual(
            test_id.str_filesystem, astring.string_to_safe_path(f"{uid}-{name}")
        )
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_no_digits(self):
        uid = 1
        name = "file.py:klass.test_method"
        test_id = TestID(uid, name, no_digits=2)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, "01")
        self.assertEqual(
            test_id.str_filesystem, astring.string_to_safe_path(f"{'01'}-{name}")
        )
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_large_digits(self):
        """
        Tests that when the filesystem can only cope with the size of
        the Test ID, that's the only thing that will be kept.
        """
        uid = 1
        name = "test"
        max_length = path.get_max_file_name_length(name)
        test_id = TestID(uid, name, no_digits=max_length)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, f"{uid:0{max_length}d}")
        self.assertEqual(test_id.str_filesystem, f"{uid:0{max_length}d}")
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_uid_too_large_digits(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, not even the test uid, an exception will be
        raised.
        """
        name = "test"
        max_length = path.get_max_file_name_length(name)
        over_limit = max_length + 1
        test_id = TestID(1, name, no_digits=over_limit)
        self.assertRaises(RuntimeError, lambda: test_id.str_filesystem)

    def test_uid_large_name(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, the name will be shortened.
        """
        uid = 1
        name = "test_" * 51  # 255 characters
        test_id = TestID(uid, name)
        max_length = path.get_max_file_name_length(name)
        self.assertEqual(test_id.uid, 1)
        # 2 chars are taken by the uid and dash
        max_name_length = max_length - 2
        self.assertEqual(test_id.str_filesystem, f"{uid}-{name[:max_name_length]}")
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_large_variant(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, and a variant name is present, the name will be
        removed.
        """
        uid = 1
        name = "test"
        variant_id = "fast_" * 51  # 255 characters
        variant = {"variant_id": variant_id}
        test_id = TestID(uid, name, variant=variant)
        max_length = path.get_max_file_name_length(name)
        # 2 chars are taken by the uid and dash
        max_name_length = max_length - 2
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(
            test_id.str_filesystem, f"{uid}_{variant_id[:max_name_length]}"
        )
        self.assertIs(test_id.variant, variant_id)
        self.assertEqual(test_id.str_variant, f";{variant_id}")


if __name__ == "__main__":
    unittest.main()
