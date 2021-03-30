import os
import unittest.mock

from avocado.utils import process, ssh


class Session(unittest.TestCase):

    def test_minimal(self):
        session = ssh.Session('host')
        self.assertEqual(session.host, 'host')
        self.assertIsNone(session.port)
        self.assertIsNone(session.user)
        self.assertIsNone(session.key)
        self.assertIsNone(session._connection)

    def test_ssh_cmd_port(self):
        session = ssh.Session('hostname', port=22)
        ssh_cmd = session._ssh_cmd()
        self.assertIn(" -p ", ssh_cmd)

    def test_ssh_cmd_user_key(self):
        session = ssh.Session('hostname', user='user', key='/path/to/key')
        ssh_cmd = session._ssh_cmd()
        self.assertIn(" -l ", ssh_cmd)
        self.assertIn(" -i ", ssh_cmd)

    def test_master_connection_key(self):
        session = ssh.Session('hostname', user='user', key='/path/to/key')
        master_connection = session._master_connection()
        self.assertIn(" -o 'PubkeyAuthentication=yes'", master_connection)

    def test_master_connection_no_key(self):
        session = ssh.Session('hostname', user='user')
        master_connection = session._master_connection()
        self.assertIn(" -o 'PubkeyAuthentication=no'", master_connection)

    def test_master_connection_password(self):
        session = ssh.Session('hostname', user='user', password='PASSWORD')
        master_connection = session._master_connection()
        self.assertIn(" -o 'PasswordAuthentication=yes'", master_connection)

    def test_master_connection_no_password(self):
        session = ssh.Session('hostname', user='user')
        master_connection = session._master_connection()
        self.assertIn(" -o 'PasswordAuthentication=no'", master_connection)

    def test_master_connection_ssh_askpass_script(self):
        password = 'PASSWORD'
        session = ssh.Session('hostname', user='user', password=password)
        ssh_askpass_path = session._create_ssh_askpass()
        ssh_askpass_password = process.run(ssh_askpass_path)
        os.unlink(ssh_askpass_path)
        self.assertEqual(ssh_askpass_password.stdout_text.rstrip(), password)

    def test_no_ssh_client_binary(self):
        session = ssh.Session('hostname')
        with unittest.mock.patch('avocado.utils.ssh.SSH_CLIENT_BINARY', None):
            self.assertFalse(session.connect())


if __name__ == '__main__':
    unittest.main()
