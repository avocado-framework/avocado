import os
import pathlib
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

    def test_getpath(self):
        abspath = pathlib.Path().resolve()
        url = "https://example.com/path/to/file"
        user_path = "example.txt"
        self.assertEqual(path.get_path(abspath, abspath), abspath)
        self.assertEqual(path.get_path(abspath, url), url)
        self.assertEqual(
            path.get_path(abspath, user_path), os.path.join(abspath, user_path)
        )

    @unittest.mock.patch("avocado.utils.path.os.environ", {"PATH": ""})
    def test_find_command_not_found(self):
        default_path = "/opt/custom/bin/mycmd"
        result = path.find_command("mycmd", default=default_path)
        self.assertEqual(result, default_path)

    @unittest.mock.patch("avocado.utils.path.os.environ", {})
    @unittest.mock.patch("avocado.utils.path.os.path.isfile", return_value=True)
    @unittest.mock.patch("avocado.utils.path.os.access", return_value=False)
    def test_find_command_not_executable(self, mock_access, mock_isfile):
        with self.assertRaises(path.CmdNotFoundError) as e:
            path.find_command("unexecutable_cmd")
        self.assertIn("Command 'unexecutable_cmd' could not be found", str(e.exception))

    def test_PathInspector_get_first_line_not_exists(self):
        inspector = path.PathInspector("nonexistent_file.txt")
        self.assertEqual(inspector.get_first_line(), "")

    @unittest.mock.patch("avocado.utils.path.os.path.isfile", return_value=True)
    @unittest.mock.patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data="Line 1\nLine 2",
    )
    def test_PathInspector_get_first_line(
        self, mock_open, mock_isfile
    ):  # pylint: disable=unused-argument
        inspector = path.PathInspector("empty_file.txt")
        self.assertEqual(inspector.get_first_line(), "Line 1\n")

    def test_PathInspector_has_exec_permission_not_exists(self):
        inspector = path.PathInspector("nonexistent_file.txt")
        self.assertFalse(inspector.has_exec_permission())

    @unittest.mock.patch("avocado.utils.path.os.path.exists", return_value=True)
    @unittest.mock.patch("avocado.utils.path.os.stat")
    def test_PathInspector_has_exec_permission_exists(
        self, mock_stat, mock_exists
    ):  # pylint: disable=unused-argument
        mock_stat_result = unittest.mock.MagicMock()
        mock_stat_result.st_mode = 0o755
        mock_stat.return_value = mock_stat_result

        inspector = path.PathInspector("existent_file.txt")
        self.assertTrue(inspector.has_exec_permission())

    def test_PathInspector_is_empty_not_exists(self):
        inspector = path.PathInspector("nonexistent_file.txt")
        self.assertFalse(inspector.is_empty())

    @unittest.mock.patch("avocado.utils.path.os.path.exists", return_value=True)
    @unittest.mock.patch("avocado.utils.path.os.stat")
    def test_PathInspector_is_empty(
        self, mock_stat, mock_exists
    ):  # pylint: disable=unused-argument
        mock_stat_result = unittest.mock.MagicMock()
        mock_stat_result.st_size = 1024
        mock_stat.return_value = mock_stat_result

        inspector = path.PathInspector("existent_file.txt")
        self.assertFalse(inspector.is_empty())

    @unittest.mock.patch("avocado.utils.path.os.path.isfile", return_value=True)
    @unittest.mock.patch(
        "builtins.open", new_callable=unittest.mock.mock_open, read_data="#!/bin/bash"
    )
    def test_PathInspector_is_script_with_bash(
        self, mock_isfile, mock_open
    ):  # pylint: disable=unused-argument
        inspector = path.PathInspector("test.sh")
        self.assertTrue(inspector.is_script(language="bash"))

    @unittest.mock.patch("avocado.utils.path.os.path.isfile", return_value=True)
    @unittest.mock.patch(
        "builtins.open",
        new_callable=unittest.mock.mock_open,
        read_data="This is not a shebang",
    )
    def test_PathInspector_is_script_no_shebang(
        self, mock_isfile, mock_open
    ):  # pylint: disable=unused-argument
        inspector = path.PathInspector("test.txt")
        self.assertFalse(inspector.is_script())

    @unittest.mock.patch("avocado.utils.path.os.path.isfile", return_value=True)
    @unittest.mock.patch(
        "builtins.open", new_callable=unittest.mock.mock_open, read_data="#!/bin/bash"
    )
    def test_PathInspector_is_python_not_python(
        self, mock_isfile, mock_open
    ):  # pylint: disable=unused-argument
        inspector = path.PathInspector("test.sh")
        self.assertFalse(inspector.is_python())

    @unittest.mock.patch("avocado.utils.path.os.path.isdir", return_value=False)
    @unittest.mock.patch("avocado.utils.path.os.makedirs", side_effect=OSError)
    def test_usable_rw_dir_create_fails(
        self, mock_makedirs, mock_isdir
    ):  # pylint: disable=unused-argument
        self.assertFalse(path.usable_rw_dir("/tmp/test_dir"))

    @unittest.mock.patch("avocado.utils.path.os.path.isdir", return_value=True)
    @unittest.mock.patch("avocado.utils.path.tempfile.mkstemp", side_effect=OSError)
    def test_usable_rw_dir_fails(
        self, mock_mkstemp, mock_isdir
    ):  # pylint: disable=unused-argument
        self.assertFalse(path.usable_rw_dir("/tmp"))

    @unittest.mock.patch("avocado.utils.path.os.getcwd", side_effect=FileNotFoundError)
    def test_usable_ro_dir_getcwd_fails(
        self, mock_getcwd
    ):  # pylint: disable=unused-argument
        self.assertFalse(path.usable_ro_dir("/tmp"))

    @unittest.mock.patch("avocado.utils.path.os.getcwd", return_value="/")
    @unittest.mock.patch("avocado.utils.path.os.path.isdir", return_value=True)
    @unittest.mock.patch("avocado.utils.path.os.chdir", side_effect=OSError)
    def test_usable_ro_dir_chdir_fails(
        self, mock_chdir, mock_isdir, mock_getcwd
    ):  # pylint: disable=unused-argument
        self.assertFalse(path.usable_ro_dir("/tmp"))


if __name__ == "__main__":
    unittest.main()
