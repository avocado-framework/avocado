import pickle
import sys

from avocado.core import variants
from avocado.plugins import yaml_to_mux

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
if __name__ == "__main__":
    PATH_PREFIX = "../../../../"
else:
    PATH_PREFIX = ""


class TestAvocadoParams(unittest.TestCase):

    def setUp(self):
        yamls = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                              'examples/mux-selftest-params.yaml'])
        self.yamls = iter(yaml_to_mux.MuxTree(yamls))
        self.params1 = variants.AvocadoParams(self.yamls.next(), 'Unittest1',
                                              ['/ch0/*', '/ch1/*'], {})
        self.yamls.next()    # Skip 2nd
        self.yamls.next()    # and 3rd
        self.params2 = variants.AvocadoParams(self.yamls.next(), 'Unittest2',
                                              ['/ch1/*', '/ch0/*'], {})

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_pickle(self):
        params = pickle.dumps(self.params1, 2)  # protocol == 2
        params = pickle.loads(params)
        self.assertEqual(self.params1, params)

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_basic(self):
        self.assertEqual(self.params1, self.params1)
        self.assertNotEqual(self.params1, self.params2)
        repr(self.params1)
        str(self.params1)
        str(variants.AvocadoParams([], 'Unittest', [], {}))
        self.assertEqual(15, sum([1 for _ in self.params1.iteritems()]))

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_unhashable(self):
        """ Verifies that unhashable arguments can be passed to params.get """
        self.assertEqual(self.params1.get("root", "/ch0/", ["foo"]), ["foo"])
        self.assertEqual(self.params1.get('unique1',
                                          '/ch0/ch0.1/ch0.1.1/ch0.1.1.1/',
                                          ['bar']), 'unique1')

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_get_abs_path(self):
        # /ch0/ is not leaf thus it's not queryable
        self.assertEqual(self.params1.get('root', '/ch0/', 'bbb'), 'bbb')
        self.assertEqual(self.params1.get('unique1', '/ch0/*', 'ccc'),
                         'unique1')
        self.assertEqual(self.params2.get('unique1', '/ch0/*', 'ddd'),
                         'unique1-2')
        self.assertEqual(self.params1.get('unique3', '/ch0/*', 'eee'),
                         'unique3')
        # unique3 is not in self.params2
        self.assertEqual(self.params2.get('unique3', '/ch0/*', 'fff'),
                         'fff')
        # Use the leaf
        self.assertEqual(self.params1.get('unique1',
                                          '/ch0/ch0.1/ch0.1.1/ch0.1.1.1/',
                                          'ggg'), 'unique1')
        # '/ch0/ch0.1/ch0.1.1/' is in the tree, but not in current variant
        self.assertEqual(self.params2.get('unique1',
                                          '/ch0/ch0.1/ch0.1.1/ch0.1.1.1/',
                                          'hhh'), 'hhh')

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_get_greedy_path(self):
        self.assertEqual(self.params1.get('unique1', '/*/*/*/ch0.1.1.1/',
                                          111), 'unique1')
        # evaluated from right
        self.assertEqual(self.params1.get('unique1', '/*/*/ch0.1.1.1/', 222),
                         'unique1')
        # path too long so can't match from right
        self.assertEqual(self.params1.get('unique1', '/*/*/*/*/ch0.1.1.1/',
                                          333), 333)
        self.assertEqual(self.params1.get('unique1', '/ch*/c*1/*0*/*1/',
                                          444), 'unique1')
        # '/ch0/ch0.1/ch0.1.1/' is in the tree, but not in current variant
        self.assertEqual(self.params2.get('unique1', '/ch*/c*1/*0*/*1/',
                                          555), 555)
        self.assertEqual(self.params2.get('unique1', '/ch*/c*1/*', 666),
                         'unique1-2')
        self.assertEqual(self.params1.get('unique4', '/ch1*/*', 777),
                         'other_unique')
        self.assertEqual(self.params1.get('unique2', '/ch1*/*', 888),
                         'unique2')
        # path matches nothing
        self.assertEqual(self.params1.get('root', '', 999), 999)

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_get_rel_path(self):
        self.assertEqual(self.params1.get('root', default='iii'), 'root')
        self.assertEqual(self.params1.get('unique1', '*', 'jjj'), 'unique1')
        self.assertEqual(self.params2.get('unique1', '*', 'kkk'), 'unique1-2')
        self.assertEqual(self.params1.get('unique3', '*', 'lll'), 'unique3')
        # unique3 is not in self.params2
        self.assertEqual(self.params2.get('unique3', default='mmm'), 'mmm')
        # Use the leaf
        self.assertEqual(self.params1.get('unique1', '*/ch0.1.1.1/', 'nnn'),
                         'unique1')
        # '/ch0/ch0.1/ch0.1.1/' is in the tree, but not in current variant
        self.assertEqual(self.params2.get('unique1', '*/ch0.1.1.1/', 'ooo'),
                         'ooo')

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE, "Not multiplex capable")
    def test_get_clashes(self):
        # One inherited, the other is new
        self.assertRaisesRegexp(ValueError, r"'clash1'.* \['/ch0/ch0.1/ch0.1.1"
                                r"/ch0.1.1.1=>equal', '/ch0=>equal'\]",
                                self.params1.get, 'clash1',
                                default='nnn')
        # Only inherited ones
        self.assertEqual(self.params2.get('clash1', default='ooo'),
                         'equal')
        # Booth of different origin
        self.assertRaisesRegexp(ValueError,
                                r"'clash2'.* \['/ch11=>equal', "
                                r"'/ch111=>equal'\]", self.params1.get,
                                'clash2', path='/*')
        # Filter-out the clash
        self.assertEqual(self.params1.get('clash2', path='/ch11/*'), 'equal')
        # simple clash in params1
        self.assertRaisesRegexp(ValueError, r"'clash3'.* \['/ch0=>also equal',"
                                r" '/ch0/ch0.1b/ch0.1.2=>also equal'\]",
                                self.params1.get, 'clash3',
                                default='nnn')
        # params2 is sliced the other way around so it returns before the clash
        self.assertEqual(self.params2.get('clash3', default='nnn'),
                         'also equal')


if __name__ == '__main__':
    unittest.main()
