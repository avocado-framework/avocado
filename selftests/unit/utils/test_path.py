import os
import unittest.mock

from avocado.utils import path


class Path(unittest.TestCase):
    def test_check_readable_exists(self):
        with unittest.mock.patch(
            "avocado.utils.path.os.path.exists", return_value=False
        ) as mocked_exists:
            with self.assertRaises(OSError) as cm:
                path.check_readable(os.devnull)
            self.assertEqual(
                f'File "{os.devnull}" does not exist', cm.exception.args[0]
            )
            mocked_exists.assert_called_with(os.devnull)

    def test_check_readable_access(self):
        with unittest.mock.patch(
            "avocado.utils.path.os.access", return_value=False
        ) as mocked_access:
            with self.assertRaises(OSError) as cm:
                path.check_readable(os.devnull)
            self.assertEqual(
                f'File "{os.devnull}" can not be read', cm.exception.args[0]
            )
            mocked_access.assert_called_with(os.devnull, os.R_OK)

    def test_get_path_mount_point(self):
        fictitious_path = "/.not.a.file.one.would.expect.to.find"
        self.assertEqual(path.get_path_mount_point(fictitious_path), "/")

    def test_get_path_mount_point_same(self):
        self.assertEqual(path.get_path_mount_point("/"), "/")


if __name__ == "__main__":
    unittest.main()
