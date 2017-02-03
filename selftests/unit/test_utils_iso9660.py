"""
Verifies the avocado.utils.iso9660 functionality
"""
import os
import shutil
import tempfile
import unittest

from avocado.utils import iso9660, process


class BaseIso9660(unittest.TestCase):

    """
    Base class defining setup and tests for shared Iso9660 functionality
    """

    def setUp(self):
        self.iso_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                     os.path.pardir, ".data",
                                                     "sample.iso"))
        self.iso = None
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)

    def basic_workflow(self):
        """
        Check the basic Iso9660 workflow

        :warning: Make sure to include this in per-implementation tests
                  due to ast loader we can't just define a base-class.
        """
        self.assertEqual(self.iso.read("file"),
                         "file content\n")
        dst = os.path.join(self.tmpdir, "file")
        self.iso.copy(os.path.join("Dir", "in_dir_file"), dst)
        self.assertEqual(open(dst).read(), "content of in-dir-file\n")
        self.iso.close()
        self.iso.close()    # check that double-close won't fail

    @unittest.skipIf(not process.can_sudo("mount"),
                     "This test requires mount to run under sudo or root")
    def mnt_dir_workflow(self):
        """
        Check the mnt_dir functionality

        :warning: Make sure to include this in per-implementation tests
                  due to ast loader we can't just define a base-class.
        """
        base = self.iso.mnt_dir
        os.path.isdir(os.path.join(base, "Dir"))
        self.assertEqual(open(os.path.join(base, "file")).read(),
                         "file content\n")
        self.assertEqual(open(os.path.join(base, "Dir", "in_dir_file")).read(),
                         "content of in-dir-file\n")
        self.iso.close()
        self.assertFalse(os.path.exists(base), "the mnt_dir is suppose to be "
                         "destroyed after iso.close()")

    def tearDown(self):
        if self.iso is not None:
            self.iso.close()
        shutil.rmtree(self.tmpdir)


class IsoInfo(BaseIso9660):

    """
    IsoInfo-based check
    """

    @unittest.skipIf(process.system("which isoinfo", ignore_status=True),
                     "isoinfo not installed.")
    def setUp(self):
        super(IsoInfo, self).setUp()
        self.iso = iso9660.Iso9660IsoInfo(self.iso_path)

    def test_basic_workflow(self):
        """Call the basic workflow"""
        self.basic_workflow()

    def test_mnt_dir(self):
        """Use the mnt_dir property"""
        self.mnt_dir_workflow()


class IsoRead(BaseIso9660):

    """
    IsoRead-based check
    """

    @unittest.skipIf(process.system("which iso-read", ignore_status=True),
                     "iso-read not installed.")
    def setUp(self):
        super(IsoRead, self).setUp()
        self.iso = iso9660.Iso9660IsoRead(self.iso_path)

    def test_basic_workflow(self):
        """Call the basic workflow"""
        self.basic_workflow()

    def test_mnt_dir(self):
        """Use the mnt_dir property"""
        self.mnt_dir_workflow()


class IsoMount(BaseIso9660):

    """
    Mount-based check
    """

    @unittest.skipIf(not process.can_sudo("mount"),
                     "This test requires sudo or root")
    def setUp(self):
        super(IsoMount, self).setUp()
        self.iso = iso9660.Iso9660Mount(self.iso_path)

    def test_basic_workflow(self):
        """Call the basic workflow"""
        self.basic_workflow()

    def test_mnt_dir(self):
        """Use the mnt_dir property"""
        self.mnt_dir_workflow()


if __name__ == "__main__":
    unittest.main()
