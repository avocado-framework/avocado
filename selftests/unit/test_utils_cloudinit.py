import os
import shutil
import tempfile
import threading
import unittest     # pylint: disable=C0411
try:
    from unittest import mock
except ImportError:
    import mock

from six.moves import http_client

from avocado.utils import cloudinit
from avocado.utils import iso9660
from avocado.utils import network
from avocado.utils import data_factory

from .. import setup_avocado_loggers


setup_avocado_loggers()


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


class PhoneHome(unittest.TestCase):

    ADDRESS = '127.0.0.1'

    def post_ignore_response(self, url):
        conn = http_client.HTTPConnection(self.ADDRESS, self.port)
        conn.request('POST', url)
        try:
            conn.getresponse()
        except Exception:
            pass
        finally:
            conn.close()

    def setUp(self):
        self.port = network.find_free_port(address=self.ADDRESS)
        self.instance_id = data_factory.generate_random_string(12)
        self.server = cloudinit.PhoneHomeServer((self.ADDRESS, self.port),
                                                self.instance_id)

    def test_phone_home_bad(self):
        self.assertFalse(self.server.instance_phoned_back)
        server_thread = threading.Thread(target=self.server.handle_request)
        server_thread.start()
        self.post_ignore_response('/BAD_INSTANCE_ID')
        self.assertFalse(self.server.instance_phoned_back)

    def test_phone_home_good(self):
        self.assertFalse(self.server.instance_phoned_back)
        server_thread = threading.Thread(target=self.server.handle_request)
        server_thread.start()
        self.post_ignore_response('/' + self.instance_id)
        self.assertTrue(self.server.instance_phoned_back)

    def test_phone_home_bad_good(self):
        self.test_phone_home_bad()
        self.test_phone_home_good()

    def tearDown(self):
        self.server.server_close()


if __name__ == '__main__':
    unittest.main()
