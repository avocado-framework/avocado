"""
Verifies the avocado.utils.iso9660 functionality
"""
import os
import tempfile
import unittest.mock

from avocado.utils import iso9660, path, process
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


class Capabilities(unittest.TestCase):
    def setUp(self):
        self.iso_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                os.path.pardir,
                ".data",
                "sample.iso",
            )
        )

    @unittest.mock.patch("avocado.utils.iso9660.has_pycdlib", return_value=True)
    def test_capabilities_pycdlib(self, has_pycdlib_mocked):
        instance = iso9660.iso9660(self.iso_path, ["read", "create", "write"])
        self.assertIsInstance(instance, iso9660.ISO9660PyCDLib)
        self.assertTrue(has_pycdlib_mocked.called)

    @unittest.mock.patch("avocado.utils.iso9660.has_pycdlib", return_value=False)
    @unittest.mock.patch("avocado.utils.iso9660.has_isoinfo", return_value=False)
    @unittest.mock.patch("avocado.utils.iso9660.has_isoread", return_value=False)
    @unittest.mock.patch("avocado.utils.iso9660.can_mount", return_value=False)
    def test_capabilities_nobackend(
        self,
        has_pycdlib_mocked,
        has_isoinfo_mocked,
        has_isoread_mocked,
        can_mount_mocked,
    ):
        self.assertIsNone(iso9660.iso9660(self.iso_path, ["read"]))
        self.assertTrue(has_pycdlib_mocked.called)
        self.assertTrue(has_isoinfo_mocked.called)
        self.assertTrue(has_isoread_mocked.called)
        self.assertTrue(can_mount_mocked.called)

    def test_non_existing_capabilities(self):
        self.assertIsNone(
            iso9660.iso9660(self.iso_path, ["non-existing", "capabilities"])
        )


class BaseIso9660:

    """
    Base class defining setup and tests for shared Iso9660 functionality
    """

    def setUp(self):
        self.iso_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                os.path.pardir,
                ".data",
                "sample.iso",
            )
        )
        self.iso = None
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_basic_workflow(self):
        """
        Check the basic Iso9660 workflow
        """
        self.assertEqual(self.iso.read("file"), b"file content\n")
        dst = os.path.join(self.tmpdir.name, "file")
        self.iso.copy(os.path.join("Dir", "in_dir_file"), dst)
        self.assertEqual(open(dst, encoding="utf-8").read(), "content of in-dir-file\n")
        self.iso.close()
        self.iso.close()  # check that double-close won't fail

    @unittest.skipIf(
        not process.can_sudo("mount"),
        "This test requires mount to run under sudo or root",
    )
    @unittest.skipUnless(
        process.has_capability("cap_sys_admin"),
        "Capability to mount is required (cap_sys_admin)",
    )
    def test_mnt_dir_workflow(self):
        """
        Check the mnt_dir functionality
        """
        base = self.iso.mnt_dir
        dir_path = os.path.join(base, "Dir")
        self.assertTrue(os.path.isdir(dir_path))
        self.assertEqual(
            bytes(open(os.path.join(base, "file"), "rb").read()), b"file content\n"
        )
        in_dir_file_path = os.path.join(base, "Dir", "in_dir_file")
        self.assertEqual(
            bytes(open(in_dir_file_path, "rb").read()), b"content of in-dir-file\n"
        )
        self.iso.close()
        self.assertFalse(
            os.path.exists(base),
            "the mnt_dir is suppose to be " "destroyed after iso.close()",
        )

    def tearDown(self):
        if self.iso is not None:
            self.iso.close()
        self.tmpdir.cleanup()


class IsoInfo(BaseIso9660, unittest.TestCase):

    """
    IsoInfo-based check
    """

    @unittest.skipUnless(
        path.find_command("isoinfo", default=False), "isoinfo not installed."
    )
    def setUp(self):
        super().setUp()
        self.iso = iso9660.Iso9660IsoInfo(self.iso_path)


class IsoRead(BaseIso9660, unittest.TestCase):

    """
    IsoRead-based check
    """

    @unittest.skipUnless(
        path.find_command("iso-read", default=False), "iso-read not installed."
    )
    def setUp(self):
        super().setUp()
        self.iso = iso9660.Iso9660IsoRead(self.iso_path)


class IsoMount(BaseIso9660, unittest.TestCase):

    """
    Mount-based check
    """

    @unittest.skipIf(not process.can_sudo("mount"), "This test requires sudo or root")
    @unittest.skipUnless(
        process.has_capability("cap_sys_admin"),
        "Capability to mount is required (cap_sys_admin)",
    )
    def setUp(self):
        super().setUp()
        self.iso = iso9660.Iso9660Mount(self.iso_path)


class PyCDLib(BaseIso9660, unittest.TestCase):

    """
    PyCDLib-based check
    """

    @unittest.skipUnless(iso9660.has_pycdlib(), "pycdlib not installed")
    def setUp(self):
        super().setUp()
        self.iso = iso9660.ISO9660PyCDLib(self.iso_path)

    def test_create_write(self):
        new_iso_path = os.path.join(self.tmpdir.name, "new.iso")
        new_iso = iso9660.ISO9660PyCDLib(new_iso_path)
        new_iso.create()
        content = b"AVOCADO"
        for file_path in ("README", "/readme", "readme.txt", "quite-long-readme.txt"):
            new_iso.write(file_path, content)
            new_iso.close()
            read_iso = iso9660.ISO9660PyCDLib(new_iso_path)
            self.assertEqual(read_iso.read(file_path), content)
            self.assertTrue(os.path.isfile(new_iso_path))


if __name__ == "__main__":
    unittest.main()
