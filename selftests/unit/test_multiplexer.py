import itertools
import pickle
import sys

from avocado.core import multiplexer
from avocado.core import tree
from avocado.plugins import yaml_to_mux

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
if __name__ == "__main__":
    PATH_PREFIX = "../../../../"
else:
    PATH_PREFIX = ""


def combine(leaves_pools):
    """ Joins remaining leaves and pools and create product """
    if leaves_pools[0]:
        leaves_pools[1].extend(leaves_pools[0])
    return itertools.product(*leaves_pools[1])


class TestMultiplex(unittest.TestCase):

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE,
                     "Not multiplex capable")
    def setUp(self):
        self.mux_tree = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                                      'examples/mux-selftest.'
                                                      'yaml'])
        self.mux_full = tuple(multiplexer.MuxTree(self.mux_tree))

    def test_empty(self):
        act = tuple(multiplexer.MuxTree(tree.TreeNode()))
        self.assertEqual(act, (['', ],))

    def test_partial(self):
        exp = (['intel', 'scsi'], ['intel', 'virtio'], ['amd', 'scsi'],
               ['amd', 'virtio'], ['arm', 'scsi'], ['arm', 'virtio'])
        act = tuple(multiplexer.MuxTree(self.mux_tree.children[0]))
        self.assertEqual(act, exp)

    def test_full(self):
        self.assertEqual(len(self.mux_full), 12)

    def test_create_variants(self):
        from_file = yaml_to_mux.create_from_yaml(
            ["/:" + PATH_PREFIX + 'examples/mux-selftest.yaml'])
        from_file = multiplexer.MuxTree(from_file)
        self.assertEqual(self.mux_full, tuple(from_file))

    # Filters are tested in tree_unittests, only verify `multiplex_yamls` calls
    def test_filter_only(self):
        exp = (['intel', 'scsi'], ['intel', 'virtio'])
        act = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                            'examples/mux-selftest.yaml'])
        act = tree.apply_filters(act, ('/hw/cpu/intel', '/distro/fedora',
                                       '/hw'))
        act = tuple(multiplexer.MuxTree(act))
        self.assertEqual(act, exp)

    def test_filter_out(self):
        act = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                            'examples/mux-selftest.yaml'])
        act = tree.apply_filters(act, None, ('/hw/cpu/intel', '/distro/fedora',
                                             '/distro'))
        act = tuple(multiplexer.MuxTree(act))
        self.assertEqual(len(act), 4)
        self.assertEqual(len(act[0]), 3)
        str_act = str(act)
        self.assertIn('amd', str_act)
        self.assertIn('prod', str_act)
        self.assertNotIn('intel', str_act)
        self.assertNotIn('fedora', str_act)


class TestAvocadoParams(unittest.TestCase):

    def setUp(self):
        yamls = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                              'examples/mux-selftest-params.yaml'])
        self.yamls = iter(multiplexer.MuxTree(yamls))
        self.params1 = multiplexer.AvocadoParams(self.yamls.next(), 'Unittest1',
                                                 ['/ch0/*', '/ch1/*'], {})
        self.yamls.next()    # Skip 2nd
        self.yamls.next()    # and 3rd
        self.params2 = multiplexer.AvocadoParams(self.yamls.next(), 'Unittest2',
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
        str(multiplexer.AvocadoParams([], 'Unittest', [], {}))
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
