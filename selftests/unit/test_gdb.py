import unittest

from avocado.utils import gdb


class GDBRemoteTest(unittest.TestCase):

    def test_checksum(self):
        self.assertEqual(gdb.remote_checksum(b'!'), b'21')
        self.assertEqual(gdb.remote_checksum(b'OK'), b'9a')
        self.assertEqual(gdb.remote_checksum(b'foo'), b'44')

    def test_encode_command(self):
        self.assertEqual(gdb.remote_encode(b'!'), b'$!#21')
        self.assertEqual(gdb.remote_encode(b'OK'), b'$OK#9a')
        self.assertEqual(gdb.remote_encode(b'foo'), b'$foo#44')

    def test_decode_response(self):
        self.assertEqual(gdb.remote_decode(b'$!#21'), b'!')
        self.assertEqual(gdb.remote_decode(b'$OK#9a'), b'OK')
        self.assertEqual(gdb.remote_decode(b'$foo#44'), b'foo')

    def test_decode_invalid(self):
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode(b'$!#22')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode(b'$foo$bar#21')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode(b'!!#21')
        with self.assertRaises(gdb.InvalidPacketError):
            gdb.remote_decode(b'+$!#21')

if __name__ == '__main__':
    unittest.main()
