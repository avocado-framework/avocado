import unittest

from avocado.utils import astring


class AstringTest(unittest.TestCase):

    def testTabularOutput(self):
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

    def testTabularWithConsoleCodes(self):
        matrix = [("a", "bb", "ccc", "dddd", "last"),
                  ("\x1b[94ma",             # {BLUE}a
                   "\033[0mbb",             # {END}bb
                   "ccc\033[1D\033[1Dcc",   # ccc{MOVE_LEFT}{MOVE_LEFT}cc
                   "d\033[1C\033[1Cd",      # d{MOVE_RIGHT}{MOVE_RIGHT}d
                   "last")]
        header = ['0', '1', '2', '3', '4']
        self.assertEqual(astring.tabular_output(matrix, header),
                         "0 1  2   3    4\n"
                         "a bb ccc dddd last\n"
                         "\x1b[94ma \x1b[0mbb ccc\x1b[1D\x1b[1Dcc d\x1b[1C\x1b[1Cd last")

    def testUnicodeTabular(self):
        """
        Verifies tabular can handle utf-8 chars properly

        It tries valid encoded utf-8 string as well as unicode ones of
        various lengths and verifies calculates the right length and reports
        the correct results. (the string_safe_encode function is in use here)
        """

        matrix = [("\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4\xd0\xbe",
                   123),
                  (u'\u0430\u0432\u043e\u043a\u0430\u0434\u043e', 123),
                  ("avok\xc3\xa1do", 123),
                  ("avocado", 123)]
        str_matrix = ("\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
                      "\xd0\xbe 123\n"
                      "\xd0\xb0\xd0\xb2\xd0\xbe\xd0\xba\xd0\xb0\xd0\xb4"
                      "\xd0\xbe 123\n"
                      "avok\xc3\xa1do 123\n"
                      "avocado 123")
        self.assertEqual(astring.tabular_output(matrix), str_matrix)
        self.assertEqual(astring.tabular_output(matrix[1:], matrix[0]), str_matrix)


if __name__ == '__main__':
    unittest.main()
