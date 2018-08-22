import os
import shutil
import tempfile
import unittest     # pylint: disable=C0411
try:
    from unittest import mock
except ImportError:
    import mock

from avocado.utils import cloudinit
from avocado.utils import iso9660


def has_iso_create_write():
    return iso9660.iso9660(os.devnull, ["create", "write"]) is not None


class CloudInit(unittest.TestCase):

    def test_iso_no_create_write(self):
        with mock.patch('avocado.utils.iso9660.iso9660', return_value=None):
            self.assertRaises(RuntimeError, cloudinit.iso, os.devnull, "INSTANCE_ID")


class CloudInitISO(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)

    @unittest.skipUnless(has_iso_create_write(),
                         "system lacks support for creating ISO images")
    def test_iso_no_phone_home(self):
        path = os.path.join(self.tmpdir, "cloudinit.iso")
        instance_id = b"INSTANCE_ID"
        username = b"AVOCADO_USER"
        password = b"AVOCADO_PASSWORD"
        cloudinit.iso(path, instance_id, username, password)
        iso = iso9660.iso9660(path)
        self.assertIn(instance_id, iso.read("/meta-data"))
        user_data = iso.read("/user-data")
        self.assertIn(username, user_data)
        self.assertIn(password, user_data)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == '__main__':
    unittest.main()
