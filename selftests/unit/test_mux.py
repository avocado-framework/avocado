import copy
import itertools
import pickle
import unittest
import yaml


import avocado_varianter_yaml_to_mux as yaml_to_mux
from avocado.core import mux, tree, varianter


if __name__ == "__main__":
    PATH_PREFIX = "../../"
else:
    PATH_PREFIX = ""


def combine(leaves_pools):
    """ Joins remaining leaves and pools and create product """
    if leaves_pools[0]:
        leaves_pools[1].extend(leaves_pools[0])
    return itertools.product(*leaves_pools[1])


class TestMuxTree(unittest.TestCase):
    # Share tree with all tests
    tree = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                         'examples/mux-selftest.yaml'])

    def test_node_order(self):
        self.assertIsInstance(self.tree, mux.MuxTreeNode)
        self.assertEqual('hw', self.tree.children[0])
        self.assertEqual({'cpu_CFLAGS': '-march=core2'},
                         self.tree.children[0].children[0].children[0].value)
        disk = self.tree.children[0].children[1]
        self.assertEqual('scsi', disk.children[0])
        self.assertEqual({'disk_type': 'scsi', 'corruptlist': ['againlist']},
                         disk.children[0].value)
        self.assertEqual('virtio', disk.children[1])
        self.assertEqual({}, disk.children[1].value)
        self.assertEqual('distro', self.tree.children[1])
        self.assertEqual('env', self.tree.children[2])
        self.assertEqual({'opt_CFLAGS': '-O2'},
                         self.tree.children[2].children[0].value)

    def test_eq(self):
        # Copy
        tree2 = copy.deepcopy(self.tree)
        self.assertEqual(self.tree, tree2)
        # Additional node
        child = mux.MuxTreeNode("20", {'name': 'Heisenbug'})
        tree2.children[1].children[1].add_child(child)
        self.assertNotEqual(self.tree, tree2)
        # Should match again
        child.detach()
        self.assertEqual(self.tree, tree2)
        # Missing node
        tree2.children[1].children[1].detach()
        self.assertNotEqual(self.tree, tree2)
        self.assertEqual(self.tree.children[0], tree2.children[0])
        # Different value
        tree2.children[0].children[0].children[0].value = {'something': 'else'}
        self.assertNotEqual(self.tree.children[0], tree2.children[0])
        tree3 = mux.MuxTreeNode()
        self.assertNotEqual(tree3, tree2)
        # Merge
        tree3.merge(tree2)
        self.assertEqual(tree3, tree2)
        # Add_child existing
        tree3.add_child(tree2.children[0])
        self.assertEqual(tree3, tree2)

    def test_links(self):
        """ Verify child->parent links """
        for leaf in self.tree:
            self.assertEqual(leaf.root, self.tree)

    def test_basic_functions(self):
        # repr
        self.assertEqual("MuxTreeNode(name='hw')", repr(self.tree.children[0]))
        # str
        self.assertEqual("/distro/mint: init=systemv",
                         str(self.tree.children[1].children[1]))
        # len
        self.assertEqual(8, len(self.tree))  # number of leaves
        # __iter__
        self.assertEqual(8, sum((1 for _ in self.tree)))  # number of leaves
        # .root
        self.assertEqual(id(self.tree),
                         id(self.tree.children[0].children[0].children[0].root)
                         )
        # .parents
        self.assertEqual(['hw', ''], self.tree.children[0].children[0].parents)
        # environment / (root)
        self.assertEqual({}, self.tree.environment)
        # environment /hw (nodes first)
        self.assertEqual({'corruptlist': ['upper_node_list']},
                         self.tree.children[0].environment)
        cpu = self.tree.children[0].children[0]
        # environment /hw/cpu (mixed env)
        self.assertEqual({'corruptlist': ['upper_node_list'],
                          'joinlist': ['first_item']},
                         cpu.environment)
        # environment /hw/cpu/amd (list extension)
        vals = {'corruptlist': ['upper_node_list'],
                'cpu_CFLAGS': '-march=athlon64',
                'joinlist': ['first_item', 'second', 'third']}
        self.assertEqual(vals, cpu.children[1].environment)
        # environment /hw/cpu/arm (deep env)
        vals = {'corruptlist': ['upper_node_list'], 'joinlist': ['first_item'],
                'cpu_CFLAGS': '-mabi=apcs-gnu '
                '-march=armv8-a -mtune=arm8'}
        self.assertEqual(vals, cpu.children[2].environment)
        # environment /hw/disk (list -> string)
        vals = {'corruptlist': 'nonlist', 'disk_type': 'virtio'}
        disk = self.tree.children[0].children[1]
        self.assertEqual(vals, disk.environment)
        # environment /hw/disk/scsi (string -> list)
        vals = {'corruptlist': ['againlist'], 'disk_type': 'scsi'}
        self.assertEqual(vals, disk.children[0].environment)
        # environment /env
        vals = {'opt_CFLAGS': '-Os'}
        self.assertEqual(vals, self.tree.children[2].environment)
        # leaves order
        leaves = ['intel', 'amd', 'arm', 'scsi', 'virtio', 'fedora', 'mint',
                  'prod']
        self.assertEqual(leaves, self.tree.get_leaves())
        # ascii contain all leaves and doesn't raise any exceptions
        ascii = tree.tree_view(self.tree, 0, False)
        for leaf in leaves:
            self.assertIn(leaf, ascii, "Leaf %s not in asci:\n%s"
                          % (leaf, ascii))

    def test_filters(self):
        tree2 = copy.deepcopy(self.tree)
        exp = ['intel', 'amd', 'arm', 'fedora', 'mint', 'prod']
        act = mux.apply_filters(tree2,
                                filter_only=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)
        tree2 = copy.deepcopy(self.tree)
        exp = ['scsi', 'virtio', 'fedora', 'mint', 'prod']
        act = mux.apply_filters(tree2,
                                filter_out=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)

    def test_merge_trees(self):
        tree2 = copy.deepcopy(self.tree)
        tree3 = mux.MuxTreeNode()
        tree3.add_child(mux.MuxTreeNode('hw', {'another_value': 'bbb'}))
        tree3.children[0].add_child(mux.MuxTreeNode('nic'))
        tree3.children[0].children[0].add_child(mux.MuxTreeNode('default'))
        tree3.children[0].children[0].add_child(mux.MuxTreeNode('virtio', {'nic': 'virtio'}))
        tree3.children[0].add_child(mux.MuxTreeNode('cpu', {'test_value': ['z']}))
        tree2.merge(tree3)
        exp = ['intel', 'amd', 'arm', 'scsi', 'virtio', 'default', 'virtio',
               'fedora', 'mint', 'prod']
        self.assertEqual(exp, tree2.get_leaves())
        self.assertEqual({'corruptlist': ['upper_node_list'],
                          'another_value': 'bbb'},
                         tree2.children[0].value)
        self.assertEqual({'joinlist': ['first_item'], 'test_value': ['z']},
                         tree2.children[0].children[0].value)
        self.assertFalse(tree2.children[0].children[2].children[0].value)
        self.assertEqual({'nic': 'virtio'},
                         tree2.children[0].children[2].children[1].value)

    def test_advanced_yaml(self):
        tree2 = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                              'examples/mux-selftest-advanced.'
                                              'yaml'])
        exp = ['intel', 'amd', 'arm', 'scsi', 'virtio', 'fedora', '6',
               '7', 'gentoo', 'mint', 'prod', 'new_node', 'on']
        act = tree2.get_leaves()
        oldroot = tree2.children[0]
        self.assertEqual(exp, act)
        self.assertEqual(tree2.children[0].children[0].path, "/virt/hw")
        self.assertEqual({'enterprise': True},
                         oldroot.children[1].children[1].value)
        self.assertEqual({'new_init': 'systemd'},
                         oldroot.children[1].children[0].value)
        self.assertEqual({'is_cool': True},
                         oldroot.children[1].children[2].value)
        self.assertEqual({'new_value': 'something'},
                         oldroot.children[3].children[0].children[0].value)
        # Convert values, but not keys
        self.assertEqual({'on': True, "true": "true"},
                         oldroot.children[4].value)
        # multiplex root (always True)
        self.assertEqual(tree2.multiplex, None)
        # multiplex /virt/
        self.assertEqual(tree2.children[0].multiplex, None)
        # multiplex /virt/hw
        self.assertEqual(tree2.children[0].children[0].multiplex, None)
        # multiplex /virt/distro
        self.assertEqual(tree2.children[0].children[1].multiplex, True)
        # multiplex /virt/env
        self.assertEqual(tree2.children[0].children[2].multiplex, True)
        # multiplex /virt/absolutely
        self.assertEqual(tree2.children[0].children[3].multiplex, None)
        # multiplex /virt/distro/fedora
        self.assertEqual(tree2.children[0].children[1].children[0].multiplex,
                         None)

    def test_get_node(self):
        self.assertRaises(ValueError,
                          self.tree.get_node, '/non-existing-node')

    def test_fingerprint_order(self):
        """
        Checks whether different order changes the fingerprint
        """
        children1 = (tree.TreeNode("child1"), tree.TreeNode("child2"))
        tree1 = tree.TreeNode("root", children=children1)
        children2 = (tree.TreeNode("child2"), tree.TreeNode("child1"))
        tree2 = tree.TreeNode("root", children=children2)
        mux1 = mux.MuxPlugin()
        mux2 = mux.MuxPlugin()
        mux1.initialize_mux(tree1, "", False)
        mux2.initialize_mux(tree2, "", False)
        mux1.update_defaults(tree.TreeNode())
        mux2.update_defaults(tree.TreeNode())
        variant1 = iter(mux1).next()
        variant2 = iter(mux2).next()
        self.assertNotEqual(variant1, variant2)
        self.assertEqual(str(variant1), "{'mux_path': '', 'variant': "
                         "[TreeNode(name='child1'), TreeNode(name="
                         "'child2')], 'variant_id': 'child1-child2-9154'}")


class TestMultiplex(unittest.TestCase):

    @unittest.skipIf(not yaml_to_mux.MULTIPLEX_CAPABLE,
                     "Not multiplex capable")
    def setUp(self):
        self.mux_tree = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                                      'examples/mux-selftest.'
                                                      'yaml'])
        self.mux_full = tuple(mux.MuxTree(self.mux_tree))

    def test_empty(self):
        act = tuple(mux.MuxTree(mux.MuxTreeNode()))
        self.assertEqual(act, (['', ],))

    def test_partial(self):
        exp = (['intel', 'scsi'], ['intel', 'virtio'], ['amd', 'scsi'],
               ['amd', 'virtio'], ['arm', 'scsi'], ['arm', 'virtio'])
        act = tuple(mux.MuxTree(self.mux_tree.children[0]))
        self.assertEqual(act, exp)

    def test_full(self):
        self.assertEqual(len(self.mux_full), 12)

    def test_create_variants(self):
        from_file = yaml_to_mux.create_from_yaml(
            ["/:" + PATH_PREFIX + 'examples/mux-selftest.yaml'])
        from_file = mux.MuxTree(from_file)
        self.assertEqual(self.mux_full, tuple(from_file))

    # Filters are tested in tree_unittests, only verify `multiplex_yamls` calls
    def test_filter_only(self):
        exp = (['intel', 'scsi'], ['intel', 'virtio'])
        act = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                            'examples/mux-selftest.yaml'])
        act = mux.apply_filters(act, ('/hw/cpu/intel', '/distro/fedora',
                                      '/hw'))
        act = tuple(mux.MuxTree(act))
        self.assertEqual(act, exp)

    def test_filter_out(self):
        act = yaml_to_mux.create_from_yaml(["/:" + PATH_PREFIX +
                                            'examples/mux-selftest.yaml'])
        act = mux.apply_filters(act, None, ('/hw/cpu/intel', '/distro/fedora',
                                            '/distro'))
        act = tuple(mux.MuxTree(act))
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
        self.yamls = iter(mux.MuxTree(yamls))
        self.params1 = varianter.AvocadoParams(self.yamls.next(), 'Unittest1',
                                               ['/ch0/*', '/ch1/*'], {})
        self.yamls.next()    # Skip 2nd
        self.yamls.next()    # and 3rd
        self.params2 = varianter.AvocadoParams(self.yamls.next(), 'Unittest2',
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
        str(varianter.AvocadoParams([], 'Unittest', [], {}))
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


class TestMultipleLoaders(unittest.TestCase):

    def test_multiple_loaders(self):
        """
        Verifies that `create_from_yaml` does not affects the main yaml.Loader
        """
        nondebug = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                                 'examples/mux-selftest.'
                                                 'yaml'])
        self.assertEqual(type(nondebug), mux.MuxTreeNode)
        self.assertEqual(type(nondebug.children[0]), mux.MuxTreeNode)
        debug = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                              'examples/mux-selftest.'
                                              'yaml'],
                                             debug=True)
        self.assertEqual(type(debug), mux.MuxTreeNodeDebug)
        # Debug nodes are of generated "NamedTreeNodeDebug" type
        self.assertEqual("<class 'avocado.core.tree.NamedTreeNodeDebug'>",
                         str(type(debug.children[0])))
        plain = yaml.load("foo: bar")
        self.assertEqual(type(plain), dict)


class TestInternalFilters(unittest.TestCase):

    def check_scenario(self, *args):
        """
        Turn args into scenario.

        :param *args: Definitions of variant's nodes. Each arg has to be of
                      length 3, where on index:
                        [0] is path
                        [1] is filter-only
                        [2] is filter-out
        """
        variant = []
        # Turn scenario into variant
        for arg in args:
            variant.append(tree.TreeNode().get_node(arg[0], True))
            variant[-1].filters = [arg[1], arg[2]]
        # Check directly the MuxTree._valid_variant function
        return mux.MuxTree._valid_variant(variant)  # pylint: disable=W0212

    def test_basic(self):
        """
        Check basic internal filters
        """
        self.assertTrue(self.check_scenario())
        self.assertTrue(self.check_scenario(("foo", [], []),))
        self.assertTrue(self.check_scenario(("foo", ["/foo"], []),))
        self.assertFalse(self.check_scenario(("foo", [], ["/foo"]),))
        # Filter should be normalized automatically (tailing '/')
        self.assertTrue(self.check_scenario(("foo", ["/foo/"], []),))
        self.assertFalse(self.check_scenario(("foo", [], ["/foo/"]),))
        # Filter-out non-existing
        self.assertTrue(self.check_scenario(("foo", [], ["/nonexist"]),))
        self.assertTrue(self.check_scenario(("foo", [], []),
                                            ("bar", [], ["/nonexists"])))
        self.assertTrue(self.check_scenario(("1/foo", [], []),
                                            ("1/bar", ["/1"], [])))
        # The /1/foo is not the same parent as /2/bar filter
        self.assertTrue(self.check_scenario(("1/foo", [], []),
                                            ("2/bar", ["/2/bar"], [])))
        self.assertFalse(self.check_scenario(("/1/foo", ["/1/bar"], []),))
        # Even though it matches one of the leaves the other is banned
        self.assertFalse(self.check_scenario(("1/foo", ["/1/foo"], []),
                                             ("1/bar", ["/1"], [])))
        # ... unless you allow both of them
        self.assertTrue(self.check_scenario(("1/foo", ["/1/foo", "/1/bar"],
                                             []),
                                            ("1/bar", ["/1"], [])))
        # In current python the set of following filters produces
        # ['/1/1', '/1/1/foo', '/1'] which verifies the `/1` is skipped as
        # higher level of filter already decided to include it.
        self.assertTrue(self.check_scenario(("/1/1/foo", ["/1/1/foo", "/1",
                                                          "/1/1"], [])))
        # Three levels
        self.assertTrue(self.check_scenario(("/1/1/foo", ["/1/1/foo"], [],
                                             "/1/2/bar", ["/1/2/bar"], [],
                                             "/2/baz", ["/2/baz"], [])))

    def test_bad_filter(self):
        # "bar" is missing the "/", therefor it's parent is not / but ""
        self.assertTrue(self.check_scenario(("foo", ["bar"], []),))
        # Filter-out "foo" won't filter-out /foo as it's not parent of /
        self.assertTrue(self.check_scenario(("foo", [], ["foo"]),))
        # Similar cases with double "//"
        self.assertTrue(self.check_scenario(("foo", [], ["//foo"]),))
        self.assertTrue(self.check_scenario(("foo", ["//foo"], []),))

    def test_filter_order(self):
        # First we evaluate filter-out and then filter-only
        self.assertFalse(self.check_scenario(("foo", ["/foo"], ["/foo"])))


class TestPathParent(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(mux.path_parent(''), '/')

    def test_on_root(self):
        self.assertEqual(mux.path_parent('/'), '/')

    def test_direct_parent(self):
        self.assertEqual(mux.path_parent('/os/linux'), '/os')

    def test_false_direct_parent(self):
        self.assertNotEqual(mux.path_parent('/os/linux'), '/')


class TestFingerprint(unittest.TestCase):

    def test_fingerprint(self):
        """
        Verifies the fingerprint is correctly evaluated
        """
        node1 = tree.TreeNode("node1", {"foo": "bar"})
        node1_fingerprint = node1.fingerprint()
        node1duplicate = tree.TreeNode("node1", {"foo": "bar"})
        self.assertEqual(node1_fingerprint, node1duplicate.fingerprint())
        node1b_value = tree.TreeNode("node1", {"foo": "baz"})
        self.assertNotEqual(node1_fingerprint, node1b_value.fingerprint())
        node1b_name = tree.TreeNode("node2", {"foo": "bar"})
        self.assertNotEqual(node1_fingerprint, node1b_name)
        node1b_path = tree.TreeNode("node1", {"foo": "bar"})
        tree.TreeNode("root", children=(node1b_path,))
        self.assertNotEqual(node1_fingerprint, node1b_path.fingerprint())
        node1b_env_orig = tree.TreeNode("node1", {"foo": "bar"})
        tree.TreeNode("root", {"bar": "baz"}, children=(node1b_env_orig))
        node1b_env_origb = tree.TreeNode("node1",
                                         {"foo": "bar", "bar": "baz"})
        tree.TreeNode("root", children=(node1b_env_origb,))
        self.assertNotEqual(node1b_env_orig.fingerprint(),
                            node1b_env_origb.fingerprint())

    def test_tree_mux_node(self):
        """
        Check the extension of fingerprint in MuxTreeNode
        """
        node1 = tree.TreeNode("node1", {"foo": "bar"})
        node1m = mux.MuxTreeNode("node1", {"foo": "bar"})
        node1m_fingerprint = node1m.fingerprint()
        self.assertNotEqual(node1.fingerprint(), node1m_fingerprint)
        node1mduplicate = mux.MuxTreeNode("node1", {"foo": "bar"})
        self.assertEqual(node1m_fingerprint, node1mduplicate.fingerprint())
        node1mb_ctrl = mux.MuxTreeNode("node1", {"foo": "bar"})
        node1mb_ctrl.ctrl = [mux.Control(0, 0)]
        self.assertNotEqual(node1m_fingerprint, node1mb_ctrl.fingerprint())


if __name__ == '__main__':
    unittest.main()
