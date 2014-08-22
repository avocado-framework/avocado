#!/usr/bin/env python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2014
#
# Authors: Ruda Moura <rmoura@redhat.com>
#          Ademar Reis <areis@redhat.com>

import unittest

from avocado.core.tree import *
from avocado.multiplexer import *

f_only = []
f_out = []


class TestMultiplex(unittest.TestCase):

    def setUp(self):

        t1 = TreeNode()
        e = t1.add_child(TreeNode('env'))
        e.add_child(TreeNode('production'))
        e.add_child(TreeNode('debug'))
        t = t1.add_child(TreeNode('tests')).add_child(TreeNode('sync_test'))
        t.add_child(TreeNode('standard'))
        t.add_child(TreeNode('aggressive'))
        self.leaves = t1.get_leaves()

        t2 = TreeNode()
        e = t2.add_child(TreeNode('env'))
        e.add_child(TreeNode('production'))
        e.add_child(TreeNode('debug'))
        st = t2.add_child(TreeNode('tests')).add_child(TreeNode('sync_test'))
        st.add_child(TreeNode('standard'))
        st.add_child(TreeNode('aggressive'))
        pt = t2.add_child(TreeNode('tests')).add_child(TreeNode('ping_test'))
        pt.add_child(TreeNode('standard'))
        pt.add_child(TreeNode('aggressive'))
        self.leaves2 = t2.get_leaves()

        t3 = TreeNode()
        e = t3.add_child(TreeNode('env'))
        e.add_child(TreeNode('production'))
        e.add_child(TreeNode('debug'))
        l = t3.add_child(TreeNode('linux'))
        l.add_child(TreeNode('fedora'))
        l.add_child(TreeNode('ubuntu'))
        a = t3.add_child(TreeNode('arch'))
        a.add_child(TreeNode('i386'))
        a.add_child(TreeNode('x86_64'))
        t = t3.add_child(TreeNode('tests')).add_child(TreeNode('sleep_test'))
        self.leaves3 = t3.get_leaves()

        t4 = TreeNode()
        t4.add_child(TreeNode('tests')).add_child(TreeNode('sync_test'))
        e = t4.add_child(TreeNode('env'))
        e.add_child(TreeNode('production'))
        e.add_child(TreeNode('debug'))
        e.add_child(TreeNode('foobar'))
        l = t4.add_child(TreeNode('linux'))
        l.add_child(TreeNode('fedora'))
        l.add_child(TreeNode('debian'))
        l.add_child(TreeNode('foobar'))
        hw = t4.add_child(TreeNode('hw'))
        dsk = hw.add_child(TreeNode('disk'))
        dsk.add_child(TreeNode('ide'))
        dsk.add_child(TreeNode('scsi'))
        cpu = hw.add_child(TreeNode('cpu'))
        cpu.add_child(TreeNode('intel'))
        cpu.add_child(TreeNode('amd'))
        cpu.add_child(TreeNode('arm'))
        cpu.add_child(TreeNode('power'))
        self.leaves4 = t4.get_leaves()

    def test_any_sibling(self):
        t = TreeNode()
        t.add_child(TreeNode('env'))
        t.add_child(TreeNode('tests'))
        t.add_child(TreeNode('linux'))
        prod = t.children[0].add_child(TreeNode('production'))
        debug = t.children[0].add_child(TreeNode('debug'))
        sleeptest = t.children[1].add_child(TreeNode('sleeptest'))
        fedora = t.children[2].add_child(TreeNode('fedora'))
        self.assertTrue(any_sibling(prod, debug, sleeptest))
        self.assertFalse(any_sibling(prod, fedora, sleeptest))

    def test_multiplex_no_dups(self):
        self.assertEqual(len(list(multiplex(self.leaves, filter_only=f_only, filter_out=f_out))), len(set(multiplex(self.leaves, filter_only=f_only, filter_out=f_out))))
        self.assertEqual(len(list(multiplex(self.leaves2, filter_only=f_only, filter_out=f_out))), len(set(multiplex(self.leaves2, filter_only=f_only, filter_out=f_out))))
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), len(set(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))))
        self.assertEqual(len(list(multiplex(self.leaves4, filter_only=f_only, filter_out=f_out))), len(set(multiplex(self.leaves4, filter_only=f_only, filter_out=f_out))))

    def test_multiplex_size(self):
        self.assertEqual(len(list(multiplex(self.leaves, filter_only=f_only, filter_out=f_out))), 4)
        self.assertEqual(len(list(multiplex(self.leaves2, filter_only=f_only, filter_out=f_out))), 8)
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 8)
        self.assertEqual(len(list(multiplex(self.leaves4, filter_only=f_only, filter_out=f_out))), 72)

    def test_multiplex_filter_only(self):
        f_only = ['']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 8)
        f_only = ['/root/arch']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)
        f_only = ['/root/arch', '/root/linux']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 4)
        f_only = ['/root/arch', '/root/linux/fedora']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)

    def test_multiplex_filter_only_invalid(self):
        f_only = ['/root/stage']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 0)
        self.assertEqual(len(list(multiplex(self.leaves4, filter_only=f_only, filter_out=f_out))), 0)

    def test_multiplex_filter_out_invalid(self):
        f_out = ['/foobar']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 8)
        self.assertEqual(len(list(multiplex(self.leaves4, filter_only=f_only, filter_out=f_out))), 72)

    def test_multiplex_filter_out(self):
        f_out = ['']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 8)
        f_out = ['/root/arch']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 4)
        f_out = ['/root/arch', '/root/linux']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)
        f_out = ['/root/arch', '/root/linux/fedora']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)

    def test_multiplex_filter_combined(self):
        f_out = ['']
        f_only = ['']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 8)
        f_only = ['/root/arch']
        f_out = ['/root/arch']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 0)
        f_out = ['/root/arch']
        f_only = ['/root/arch']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 0)
        f_out = ['/root/arch', '/root/linux']
        f_only = ['/root/linux/fedora']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)
        f_out = ['/root/arch']
        f_only = ['/root/linux']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)
        f_out = ['/root/arch']
        f_only = ['/root/linux']
        self.assertEqual(len(list(multiplex(self.leaves3, filter_only=f_only, filter_out=f_out))), 2)

if __name__ == '__main__':
    unittest.main()
