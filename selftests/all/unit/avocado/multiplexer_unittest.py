import itertools
import sys

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado import multiplexer
from avocado.core import tree


TREE = tree.create_from_yaml(['examples/mux-selftest.yaml'])


def combine(leaves_pools):
    """ Joins remaining leaves and pools and create product """
    if leaves_pools[0]:
        leaves_pools[1].extend(leaves_pools[0])
    return itertools.product(*leaves_pools[1])


class TestMultiplex(unittest.TestCase):
    tree = TREE
    mux_full = tuple(combine(multiplexer.tree2pools(tree)))

    def test_empty(self):
        act = tuple(combine(multiplexer.tree2pools(tree.TreeNode())))
        self.assertEqual(act, ((),))

    def test_partial(self):
        exp = (('intel', 'scsi'), ('intel', 'virtio'), ('amd', 'scsi'),
               ('amd', 'virtio'), ('arm', 'scsi'), ('arm', 'virtio'))
        act = tuple(combine(multiplexer.tree2pools(self.tree.children[0])))
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
