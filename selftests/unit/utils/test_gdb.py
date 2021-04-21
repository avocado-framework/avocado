import unittest

from avocado.utils.gdb import GDBRemote, InvalidPacketError


class GDBRemoteTest(unittest.TestCase):

    def test_checksum(self):
        self.assertEqual(GDBRemote.checksum(b'!'), b'21')
        self.assertEqual(GDBRemote.checksum(b'OK'), b'9a')
        self.assertEqual(GDBRemote.checksum(b'foo'), b'44')

    def test_encode_command(self):
        self.assertEqual(GDBRemote.encode(b'!'), b'$!#21')
        self.assertEqual(GDBRemote.encode(b'OK'), b'$OK#9a')
        self.assertEqual(GDBRemote.encode(b'foo'), b'$foo#44')

    def test_decode_response(self):
        self.assertEqual(GDBRemote.decode(b'$!#21'), b'!')
        self.assertEqual(GDBRemote.decode(b'$OK#9a'), b'OK')
        self.assertEqual(GDBRemote.decode(b'$foo#44'), b'foo')

    def test_decode_invalid(self):
        with self.assertRaises(InvalidPacketError):
            GDBRemote.decode(b'$!#22')
        with self.assertRaises(InvalidPacketError):
            GDBRemote.decode(b'$foo$bar#21')
        with self.assertRaises(InvalidPacketError):
            GDBRemote.decode(b'!!#21')
        with self.assertRaises(InvalidPacketError):
            GDBRemote.decode(b'+$!#21')


if __name__ == '__main__':
    unittest.main()
