import http.client
import os
import tempfile
import threading
import unittest.mock

from avocado.utils import cloudinit, data_factory, iso9660
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


def has_iso_create_write():
    return iso9660.iso9660(os.devnull, ["create", "write"]) is not None


class CloudInit(unittest.TestCase):

    def test_iso_no_create_write(self):
        with unittest.mock.patch('avocado.utils.iso9660.iso9660', return_value=None):
            self.assertRaises(RuntimeError, cloudinit.iso, os.devnull, "INSTANCE_ID")


class CloudInitISO(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    @unittest.skipUnless(has_iso_create_write(),
                         "system lacks support for creating ISO images")
    def test_iso_no_phone_home(self):
        path = os.path.join(self.tmpdir.name, "cloudinit.iso")
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
        self.tmpdir.cleanup()


class PhoneHome(unittest.TestCase):

    ADDRESS = '127.0.0.1'

    def post_ignore_response(self, url):
        port = self.server.socket.getsockname()[1]
        conn = http.client.HTTPConnection(self.ADDRESS, port)
        conn.request('POST', url)
        try:
            conn.getresponse()
        except Exception:
            pass
        finally:
            conn.close()

    def setUp(self):
        self.instance_id = data_factory.generate_random_string(12)
        self.server = cloudinit.PhoneHomeServer((self.ADDRESS, 0),
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
