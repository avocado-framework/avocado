import unittest

from avocado.core.test_id import TestID
from avocado.utils import astring


class Test(unittest.TestCase):

    def test_uid_name(self):
        uid = 1
        name = 'file.py:klass.test_method'
        test_id = TestID(uid, name)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '1')
        self.assertEqual(test_id.str_filesystem,
                         astring.string_to_safe_path(f'{uid}-{name}'))
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_no_digits(self):
        uid = 1
        name = 'file.py:klass.test_method'
        test_id = TestID(uid, name, no_digits=2)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '01')
        self.assertEqual(test_id.str_filesystem,
                         astring.string_to_safe_path(f"{'01'}-{name}"))
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_large_digits(self):
        """
        Tests that when the filesystem can only cope with the size of
        the Test ID, that's the only thing that will be kept.
        """
        uid = 1
        name = 'test'
        test_id = TestID(uid, name, no_digits=255)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '%0255i' % uid)  # pylint: disable=C0209
        self.assertEqual(test_id.str_filesystem, '%0255i' % uid)  # pylint: disable=C0209
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_uid_too_large_digits(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, not even the test uid, an exception will be
        raised.
        """
        test_id = TestID(1, 'test', no_digits=256)
        self.assertRaises(RuntimeError, lambda: test_id.str_filesystem)

    def test_uid_large_name(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, the name will be shortened.
        """
        uid = 1
        name = 'test_' * 51     # 255 characters
        test_id = TestID(uid, name)
        self.assertEqual(test_id.uid, 1)
        # only 253 can fit for the test name
        self.assertEqual(test_id.str_filesystem, f'{uid}-{name[:253]}')
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_large_variant(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, and a variant name is present, the name will be
        removed.
        """
        uid = 1
        name = 'test'
        variant_id = 'fast_' * 51    # 255 characters
        variant = {'variant_id': variant_id}
        test_id = TestID(uid, name, variant=variant)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_filesystem, f'{uid}_{variant_id[:253]}')
        self.assertIs(test_id.variant, variant_id)
        self.assertEqual(test_id.str_variant, f";{variant_id}")


if __name__ == '__main__':
    unittest.main()
