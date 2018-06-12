import unittest

from avocado.utils import astring


class AstringUtilsTest(unittest.TestCase):

    def test_tabular_output(self):

        self.assertEqual(astring.tabular_output([]), "")
        self.assertEqual(astring.tabular_output([],
                                                header=('C1', 'C2', 'C3')),
                         "C1 C2 C3")
        self.assertEqual(astring.tabular_output([['v11', 'v12', 'v13']]),
                         "v11 v12 v13")
        self.assertEqual(astring.tabular_output([['v11', 'v12', 'v13'],
                                                 ['v21', 'v22', 'v23']],
                                                header=('C1', 'C2', 'C3')),
                         "C1  C2  C3" + "\n" +
                         "v11 v12 v13" + "\n" +
                         "v21 v22 v23")
        self.assertEqual(astring.tabular_output([['v11', 'v12', ''],
                                                 ['v21', 'v22', 'v23']],
                                                header=('C1', 'C2', 'C3')),
                         "C1  C2  C3" + "\n" +
                         "v11 v12 " + "\n" +
                         "v21 v22 v23")
        self.assertEqual(astring.tabular_output([['v11', 'v12', ''],
                                                 ['v21', 'v22', 'v23']],
                                                header=('C1', 'C2', 'C3'),
                                                strip=True),
                         "C1  C2  C3" + "\n" +
                         "v11 v12" + "\n" +
                         "v21 v22 v23")

        self.assertEqual(astring.tabular_output([['v11', 'v12', ''],
                                                 ['v2100', 'v22', 'v23'],
                                                 ['v31', 'v320', 'v33']],
                                                header=('C1', 'C02', 'COL3')),
                         "C1    C02  COL3" + "\n" +
                         "v11   v12  " + "\n" +
                         "v2100 v22  v23" + "\n" +
                         "v31   v320 v33")

    def test_to_bytes(self):
        self.assertEqual(astring.to_bytes(b'\x00\x80\xff'), b'\x00\x80\xff')
        self.assertEqual(astring.to_bytes(u'avok\xe1do', 'utf-8'),
                         b'avok\xc3\xa1do')
        self.assertEqual(astring.to_bytes(b'avok\xe1do', 'ISO-8859-15'),
                         b'avok\xe1do')
        data = Exception(b'avok\xc3\xa1do'.decode('utf-8'))
        self.assertEqual(astring.to_bytes(data, 'utf-8'), b'avok\xc3\xa1do')


if __name__ == '__main__':
    unittest.main()
