import copy
import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import tree
from avocado.plugins import yaml_to_mux

if __name__ == "__main__":
    PATH_PREFIX = "../../../../"
else:
    PATH_PREFIX = ""


class TestTree(unittest.TestCase):
    # Share tree with all tests
    tree = yaml_to_mux.create_from_yaml(['/:' + PATH_PREFIX +
                                         'examples/mux-selftest.yaml'])

    def test_node_order(self):
        self.assertIsInstance(self.tree, tree.TreeNode)
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
        child = tree.TreeNode("20", {'name': 'Heisenbug'})
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
        tree3 = tree.TreeNode()
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
        self.assertEqual("TreeNode(name='hw')", repr(self.tree.children[0]))
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
        act = tree.apply_filters(tree2,
                                 filter_only=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)
        tree2 = copy.deepcopy(self.tree)
        exp = ['scsi', 'virtio', 'fedora', 'mint', 'prod']
        act = tree.apply_filters(tree2,
                                 filter_out=['/hw/cpu', '']).get_leaves()
        self.assertEqual(exp, act)

    def test_merge_trees(self):
        tree2 = copy.deepcopy(self.tree)
        tree3 = tree.TreeNode()
        tree3.add_child(tree.TreeNode('hw', {'another_value': 'bbb'}))
        tree3.children[0].add_child(tree.TreeNode('nic'))
        tree3.children[0].children[0].add_child(tree.TreeNode('default'))
        tree3.children[0].children[0].add_child(tree.TreeNode('virtio',
                                                              {'nic': 'virtio'}
                                                              ))
        tree3.children[0].add_child(tree.TreeNode('cpu',
                                                  {'test_value': ['z']}))
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


class TestPathParent(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(tree.path_parent(''), '/')

    def test_on_root(self):
        self.assertEqual(tree.path_parent('/'), '/')

    def test_direct_parent(self):
        self.assertEqual(tree.path_parent('/os/linux'), '/os')

    def test_false_direct_parent(self):
        self.assertNotEqual(tree.path_parent('/os/linux'), '/')

if __name__ == '__main__':
    unittest.main()
