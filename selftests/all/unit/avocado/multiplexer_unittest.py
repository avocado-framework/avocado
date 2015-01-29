import unittest

from avocado import multiplexer
from avocado.core import tree


TREE = tree.create_from_yaml(['examples/mux-selftest.yaml'])


class TestAnySibling(unittest.TestCase):
    # /hw/cpu/{intel,amd,arm}
    tree = TREE
    sibl_a_1 = tree.children[0].children[0].children[0]
    sibl_a_2 = tree.children[0].children[0].children[1]
    sibl_a_3 = tree.children[0].children[0].children[2]
    # /hw/{cpu,disk}
    sibl_b_1 = tree.children[1].children[0]
    sibl_b_2 = tree.children[1].children[1]

    def test_empty(self):
        self.assertFalse(multiplexer.any_sibling())

    def test_one_node(self):
        single_node = self.tree.children[2].children[0]
        self.assertFalse(multiplexer.any_sibling(single_node))

    def test_all_siblings(self):
        self.assertTrue(multiplexer.any_sibling(self.sibl_b_1, self.sibl_b_2))
        self.assertTrue(multiplexer.any_sibling(self.sibl_a_1, self.sibl_a_2,
                                                self.sibl_a_3))

    def test_mixed(self):
        self.assertTrue(multiplexer.any_sibling(self.sibl_a_1, self.sibl_a_2,
                                                self.sibl_b_1))

    def test_no_relation(self):
        self.assertFalse(multiplexer.any_sibling(self.sibl_a_1, self.sibl_b_1))


class TestMultiplex(unittest.TestCase):
    tree = TREE
    mux_full = tuple(multiplexer.multiplex(tree))

    def test_empty(self):
        self.assertEqual(tuple(multiplexer.multiplex([])), tuple())

    def test_partial(self):
        exp = (('intel', 'scsi'), ('intel', 'virtio'), ('amd', 'scsi'),
               ('amd', 'virtio'), ('arm', 'scsi'), ('arm', 'virtio'))
        act = tuple(multiplexer.multiplex(self.tree.children[0]))
        self.assertEqual(act, exp)

    def test_full(self):
        self.assertEqual(len(self.mux_full), 12)

    def test_create_variants(self):
        from_file = multiplexer.multiplex_yamls(['examples/mux-selftest.yaml'])
        self.assertEqual(self.mux_full, tuple(from_file))

    # Filters are tested in tree_unittests, only verify `multiplex_yamls` calls
    def test_filter_only(self):
        exp = (('intel', 'scsi'), ('intel', 'virtio'))
        act = tuple(multiplexer.multiplex_yamls(['examples/mux-selftest.yaml'],
                                                ('/hw/cpu/intel',
                                                 '/distro/fedora',
                                                 '/hw')))
        self.assertEqual(act, exp)

    def test_filter_out(self):
        act = tuple(multiplexer.multiplex_yamls(['examples/mux-selftest.yaml'],
                                                None,
                                                ('/hw/cpu/intel',
                                                 '/distro/fedora',
                                                 '/distro')))
        self.assertEqual(len(act), 4)
        self.assertEqual(len(act[0]), 3)
        str_act = str(act)
        self.assertIn('amd', str_act)
        self.assertIn('prod', str_act)
        self.assertNotIn('intel', str_act)
        self.assertNotIn('fedora', str_act)


if __name__ == '__main__':
    unittest.main()
