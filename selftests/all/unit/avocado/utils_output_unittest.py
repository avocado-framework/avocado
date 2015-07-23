import unittest
import os
import sys

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import output


class UtilsOutputTest(unittest.TestCase):

    def testDisplayDataSizeFactor1024(self):
        self.assertEqual(output.display_data_size(103), '103.00 B')
        self.assertEqual(output.display_data_size(1024**1), '1.02 KB')
        self.assertEqual(output.display_data_size(1024**2), '1.05 MB')
        self.assertEqual(output.display_data_size(1024**3), '1.07 GB')
        self.assertEqual(output.display_data_size(1024**4), '1.10 TB')
        self.assertEqual(output.display_data_size(1024**5), '1.13 PB')
        self.assertEqual(output.display_data_size(1024**6), '1152.92 PB')

    def testDisplayDataSizeFactor1000(self):
        self.assertEqual(output.display_data_size(1000**1), '1.00 KB')
        self.assertEqual(output.display_data_size(1000**2), '1.00 MB')
        self.assertEqual(output.display_data_size(1000**3), '1.00 GB')
        self.assertEqual(output.display_data_size(1000**4), '1.00 TB')
        self.assertEqual(output.display_data_size(1000**5), '1.00 PB')
        self.assertEqual(output.display_data_size(1000**6), '1000.00 PB')


if __name__ == '__main__':
    unittest.main()
