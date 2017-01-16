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
        matrix = [("a", "an", "dog", "word", "final"),
                  ("\x1b[94ma",             # {BLUE}a
                   "\033[0man",             # {END}an
                   "cc\033[91mc",   # cc{RED}c
                   # {RED}d{GREEN}d{BLUE}d{GRAY}d{END}
                   "\033[91md\033[92md\033[94md\033[90md\033[0m",
                   "final")]
        header = ['0', '1', '2', '3', '4']
        open('/tmp/foo', 'w').write(astring.tabular_output(matrix, header))
        self.assertEqual(astring.tabular_output(matrix, header),
                         "0 1  2   3    4\n"
                         "a an dog word final\n"
                         "[94ma [0man cc[91mc "
                         "[91md[92md[94md[90md[0m final")

    def testTabularOutputDifferentNOCols(self):
        matrix = [[], [1], [2, 2], [333, 333, 333], [4, 4, 4, 4444]]
        self.assertEqual(astring.tabular_output(matrix),
                         "1\n"
                         "2   2\n"
                         "333 333 333\n"
                         "4   4   4   4444")

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


if __name__ == '__main__':
    unittest.main()
