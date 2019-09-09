import unittest

from avocado.utils import ssh


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


if __name__ == '__main__':
    unittest.main()
