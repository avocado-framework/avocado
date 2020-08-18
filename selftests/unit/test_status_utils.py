from unittest import TestCase

from avocado.core.status import utils


class JSON(TestCase):

    def test_loads_bytes(self):
        self.assertEqual(utils.json_loads(b'{}'), {})

    def test_loads_str(self):
        self.assertEqual(utils.json_loads('{}'), {})

    def test_loads_invalid(self):
        with self.assertRaises(utils.StatusMsgInvalidJSONError):
            utils.json_loads('+-+-InvalidJSON-AFAICT-+-+')

    def test_loads_base64(self):
        data = '{"__base64_encoded__": "dGhpcyBpcyBob3cgd2UgZW5jb2RlIGJ5dGVz"}'
        self.assertEqual(utils.json_loads(data),
                         b'this is how we encode bytes')
