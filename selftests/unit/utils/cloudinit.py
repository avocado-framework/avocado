import http.client
import os
import tempfile
import threading
import unittest.mock

from avocado.utils import cloudinit, data_factory, iso9660
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()

SSH_KEY = b"ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBCGtytDuWTzCZJ4FGy5OBKTgYwllftrmgZ3Z+mSTTRmNVlTCEDygSzALLdtC7MEilv/ezTN2uA3HIC72jYegrMc="


def has_iso_create_write():
    return iso9660.iso9660(os.devnull, ["create", "write"]) is not None


class CloudInit(unittest.TestCase):
    def test_iso_no_create_write(self):
        with unittest.mock.patch("avocado.utils.iso9660.iso9660", return_value=None):
            self.assertRaises(RuntimeError, cloudinit.iso, os.devnull, "INSTANCE_ID")


@unittest.skipUnless(
    has_iso_create_write(), "system lacks support for creating ISO images"
)
class CloudInitISO(unittest.TestCase):
    def iso_no_phone_home_check(
        self,
        instance_id,
        username=None,
        password=None,
        host=None,
        port=None,
        authorized_key=None,
    ):
        path = os.path.join(self.tmpdir.name, "cloudinit.iso")
        cloudinit.iso(
            path,
            instance_id,
            username=username,
            password=password,
            phone_home_host=host,
            phone_home_port=port,
            authorized_key=authorized_key,
        )
        iso = iso9660.iso9660(path)
        self.assertIn(instance_id, iso.read("/meta-data").decode("utf-8"))
        user_data = iso.read("/user-data")
        iso.close()
        return user_data.decode("utf-8")

    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_iso_no_phone_home(self):
        instance_id = "INSTANCE_ID"
        username = "AVOCADO_USER"
        password = "AVOCADO_PASSWORD"
        user_data = self.iso_no_phone_home_check(instance_id, username, password)
        self.assertIn(username, user_data)
        self.assertIn(password, user_data)

    def test_iso_no_phone_home_root(self):
        instance_id = "INSTANCE_ID"
        username = "root"
        password = "AVOCADO_PASSWORD"
        user_data = self.iso_no_phone_home_check(instance_id, username, password)
        self.assertIn("disable_root: False", user_data)

    def test_iso_no_phone_home_key(self):
        instance_id = "INSTANCE_ID"
        username = "AVOCADO_USER"
        user_data = self.iso_no_phone_home_check(
            instance_id, username, authorized_key=SSH_KEY
        )
        self.assertIn("ssh_authorized_keys:", user_data)

    def test_iso_no_phone_home_host(self):
        instance_id = "INSTANCE_ID"
        host = "127.0.0.1"
        port = "8888"
        user_data = self.iso_no_phone_home_check(instance_id, host=host, port=port)
        self.assertIn(f"url: http://{host}:{port}/$INSTANCE_ID/", user_data)

    def tearDown(self):
        self.tmpdir.cleanup()


class PhoneHome(unittest.TestCase):

    ADDRESS = "127.0.0.1"

    def post_response(self, url, port=None):
        if not port:
            port = self.server.socket.getsockname()[1]
        conn = http.client.HTTPConnection(self.ADDRESS, port)
        conn.request("POST", url)
        response = conn.getresponse()
        self.assertIs(response.status, 200)
        conn.close()

    def setUp(self):
        self.instance_id = data_factory.generate_random_string(12)
        self.server = cloudinit.PhoneHomeServer((self.ADDRESS, 0), self.instance_id)

    def test_phone_home_bad(self):
        self.assertFalse(self.server.instance_phoned_back)
        server_thread = threading.Thread(target=self.server.handle_request)
        server_thread.start()
        self.post_response("/BAD_INSTANCE_ID")
        self.assertFalse(self.server.instance_phoned_back)

    def test_phone_home_good(self):
        self.assertFalse(self.server.instance_phoned_back)
        server_thread = threading.Thread(target=self.server.handle_request)
        server_thread.start()
        self.post_response("/" + self.instance_id)
        self.assertTrue(self.server.instance_phoned_back)

    def test_phone_home_bad_good(self):
        self.test_phone_home_bad()
        self.test_phone_home_good()

    def tearDown(self):
        self.server.server_close()


if __name__ == "__main__":
    unittest.main()
