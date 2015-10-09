import unittest

from avocado.utils import gdb


class GDBRemoteTest(unittest.TestCase):

    def test_checksum(self):
        in_out = (('!', '21'),
                  ('OK', '9A'),
                  ('foo', '44'))
        for io in in_out:
            i, o = io
            self.assertTrue(gdb.remote_checksum(i), o)

    def test_encode_command(self):
        in_out = (('!', '$!#21'),
                  ('OK', '$OK#9a'),
                  ('foo', '$foo#44'))
        for io in in_out:
            i, o = io
            self.assertTrue(gdb.remote_encode(i), o)

    def test_decode_response(self):
        in_out = (('$!#21', '!'),
                  ('$OK#9a', 'OK'),
                  ('$foo#44', 'foo'))
        for io in in_out:
            i, o = io
            self.assertTrue(gdb.remote_decode(i), o)

    def test_decode_invalid(self):
        invalid_packets = ['$!#22',
                           '$foo$bar#21',
                           '!!#21',
                           '+$!#21']
        for p in invalid_packets:
            self.assertRaises(gdb.InvalidPacketError,
                              gdb.remote_decode, p)


if __name__ == '__main__':
    unittest.main()
