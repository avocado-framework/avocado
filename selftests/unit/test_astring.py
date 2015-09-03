import unittest
import os
import sys

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

if __name__ == '__main__':
    unittest.main()
