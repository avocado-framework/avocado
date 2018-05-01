import sys
import unittest

from avocado.utils import astring


class AstringTest(unittest.TestCase):

    def test_tabular_output(self):
        matrix = [('foo', 'bar'), ('/bin/bar/sbrubles',
                                   '/home/myuser/sbrubles')]
        self.assertEqual(astring.tabular_output(matrix),
                         ('foo               bar\n'
                          '/bin/bar/sbrubles /home/myuser/sbrubles'))
        header = ['id', 'path']
        self.assertEqual(astring.tabular_output(matrix, header),
                         ('id                path\n'
                          'foo               bar\n'
                          '/bin/bar/sbrubles /home/myuser/sbrubles'))

    def test_tabular_with_console_codes(self):
        matrix = [("a", "an", "dog", "word", "last"),
                  ("\x1b[94ma",             # {BLUE}a
                   "\033[0man",             # {END}an
                   "cc\033[91mc",   # cc{RED}c
                   # {RED}d{GREEN}d{BLUE}d{GRAY}d{END}
                   "\033[91md\033[92md\033[94md\033[90md\033[0m",
                   "last")]
        header = ['0', '1', '2', '3', '4']
        self.assertEqual(astring.tabular_output(matrix, header),
                         "0 1  2   3    4\n"
                         "a an dog word last\n"
                         "[94ma [0man cc[91mc "
                         "[91md[92md[94md[90md[0m last")

    def test_tabular_output_different_no_cols(self):
        matrix = [[], [1], [2, 2], [333, 333, 333], [4, 4, 4, 4444]]
        self.assertEqual(astring.tabular_output(matrix),
                         "1\n"
                         "2   2\n"
                         "333 333 333\n"
                         "4   4   4   4444")

    # This could be a skip based on the Python version, but this is more
    # specific to the exact reason why it does/doesn't make sense to run it
    @unittest.skipUnless(sys.getdefaultencoding() == 'ascii',
                         "Test verifies conversion behavior of between ascii "
                         "and utf-8 only")
    def test_unicode_tabular(self):
        """
        Verifies tabular can handle utf-8 chars properly

        It tries valid encoded utf-8 string as well as unicode ones of
        various lengths and verifies calculates the right length and reports
        the correct results. (the string_safe_encode function is in use here)
        """

        matrix = [("\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4\xff",
                   123),
                  (u'\u0430\u0432\u043e\u043a\u0430\u0434\xff', 123),
                  ("avok\xc3\xa1do", 123),
                  ("a\u0430", 123)]
        str_matrix = ("\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
                      "\xef\xbf\xbd 123\n"
                      "\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
                      "\xc3\xbf 123\n"
                      "avok\xc3\xa1do 123\n"
                      "a\u0430 123")
        self.assertEqual(astring.tabular_output(matrix), str_matrix)

    def test_safe_path(self):
        self.assertEqual(astring.string_to_safe_path('a<>:"/\\|\\?*b'),
                         "a__________b")
        self.assertEqual(astring.string_to_safe_path('..'), "_.")
        self.assertEqual(len(astring.string_to_safe_path(" " * 300)), 255)
        avocado = u'\u0430\u0432\u043e\u043a\u0430\u0434\xff<>'
        self.assertEqual(astring.string_to_safe_path(avocado),
                         "%s__" % avocado[:-2])

    def test_is_bytes(self):
        """
        Verifies what bytes means, basically that they are the same
        thing accross Python 2 and 3 and can be decoded into "text"
        """
        binary = b''
        text = u''
        self.assertTrue(astring.is_bytes(binary))
        self.assertFalse(astring.is_bytes(text))
        self.assertTrue(hasattr(binary, 'decode'))
        self.assertTrue(astring.is_text(binary.decode()))
        # on Python 2, each str member is also a single byte char
        if sys.version_info[0] < 3:
            self.assertTrue(astring.is_bytes(str('')))
        else:
            self.assertFalse(astring.is_bytes(str('')))

    def test_is_text(self):
        """
        Verifies what text means, basically that they can represent
        extended set of characters and can be encoded into "bytes"
        """
        binary = b''
        text = u''
        self.assertTrue(astring.is_text(text))
        self.assertFalse(astring.is_text(binary))
        self.assertTrue(hasattr(text, 'encode'))
        self.assertTrue(astring.is_bytes(text.encode()))

    def test_to_text_is_text(self):
        self.assertTrue(astring.is_text(astring.to_text(b'')))
        self.assertTrue(astring.is_text(astring.to_text('')))
        self.assertTrue(astring.is_text(astring.to_text(u'')))

    def test_to_text_decode_is_text(self):
        self.assertTrue(astring.is_text(astring.to_text(b'', 'ascii')))
        self.assertTrue(astring.is_text(astring.to_text('', 'ascii')))
        self.assertTrue(astring.is_text(astring.to_text(u'', 'ascii')))

    def test_to_text(self):
        text_1 = astring.to_text(b'\xc3\xa1', 'utf-8')
        text_2 = astring.to_text(u'\u00e1', 'utf-8')
        self.assertTrue(astring.is_text(text_1))
        self.assertEqual(text_1, text_2)
        self.assertEqual(astring.to_text(Exception(u'\u00e1')),
                         u"\xe1")
        # For tuple, dict and others astring.to_text is equivalent of str()
        # because on py3 it's unicode and on py2 it uses __repr__ (is encoded)
        self.assertEqual(astring.to_text({u'\xe1': 1}), str({u'\xe1': 1}))


if __name__ == '__main__':
    unittest.main()
