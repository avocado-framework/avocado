import unittest

from avocado.utils import gdb


class GDBRemoteTest(unittest.TestCase):

    def test_checksum(self):
        self.assertEqual(gdb.remote_checksum(b'!'), b'21')
        self.assertEqual(gdb.remote_checksum(b'OK'), b'9a')
        self.assertEqual(gdb.remote_checksum(b'foo'), b'44')

    def test_encode_command(self):
        self.assertEqual(gdb.remote_encode('!'), '$!#21')
        self.assertEqual(gdb.remote_encode('OK'), '$OK#9a')
        self.assertEqual(gdb.remote_encode('foo'), '$foo#44')

    def test_decode_response(self):
        self.assertEqual(gdb.remote_decode('$!#21'), '!')
        self.assertEqual(gdb.remote_decode('$OK#9a'), 'OK')
        self.assertEqual(gdb.remote_decode('$foo#44'), 'foo')

    def test_decode_invalid(self):
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode('$!#22')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode('$foo$bar#21')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode('!!#21')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode('+$!#21')


if __name__ == '__main__':
    unittest.main()
