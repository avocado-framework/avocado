#!/usr/bin/env python

import unittest
import StringIO

from avocado.core.tree import *

source_yaml = """
hw:
    cpu:
        arch:
            - noarch
        intel:
            arch:
                - i386
                - x86-64
        arm:
            arch:
                - arm
                - arm64
os:
    linux:
        dev-tools: gcc
        pm: tar
        fedora:
            pm: rpm
        mint:
            pm: deb
        centos:
            pm: rpm
    win:
        dev-tools: 'cygwin'
        win7:
            metro: false
        win8:
            metro: true
"""


class TestReadYAML(unittest.TestCase):

    def setUp(self):
        self.yaml = StringIO.StringIO(source_yaml)

    def test_read_yaml_values(self):
        data = read_ordered_yaml(self.yaml)
        self.assertIsInstance(data, dict)
        self.assertIn('hw', data)
        self.assertIn('os', data)
        self.assertIn('cpu', data['hw'])
        self.assertIn('intel', data['hw']['cpu'])
        self.assertIsInstance(data['hw']['cpu']['intel']['arch'], list)
        self.assertIn('arm', data['hw']['cpu'])
        self.assertIsInstance(data['hw']['cpu']['arm']['arch'], list)
        self.assertIn('os', data)
        self.assertIn('linux', data['os'])
        self.assertIn('dev-tools', data['os']['linux'])
        self.assertIn('fedora', data['os']['linux'])
        self.assertIn('mint', data['os']['linux'])
        self.assertIn('centos', data['os']['linux'])
        self.assertIn('win', data['os'])
        self.assertIn('dev-tools', data['os']['win'])
        self.assertIn('win7', data['os']['win'])
        self.assertIn('win8', data['os']['win'])


class TestTreeNode(unittest.TestCase):

    def setUp(self):
        self.data = read_ordered_yaml(StringIO.StringIO(source_yaml))
        self.treenode = create_from_ordered_data(self.data)

    def test_create_treenode(self):
        self.assertIsInstance(self.treenode, TreeNode)

    def test_node_order(self):
        self.assertEqual(self.treenode.children[0].name, 'hw')
        self.assertEqual(self.treenode.children[0].children[0].name, 'cpu')
        self.assertEqual(self.treenode.children[0].children[0].children[0].name, 'intel')
        self.assertEqual(self.treenode.children[0].children[0].children[1].name, 'arm')
        self.assertEqual(self.treenode.children[1].name, 'os')
        self.assertEqual(self.treenode.children[1].children[0].name, 'linux')
        self.assertEqual(self.treenode.children[1].children[0].children[0].name, 'fedora')
        self.assertEqual(self.treenode.children[1].children[0].children[1].name, 'mint')
        self.assertEqual(self.treenode.children[1].children[0].children[2].name, 'centos')
        self.assertEqual(self.treenode.children[1].children[1].name, 'win')
        self.assertEqual(self.treenode.children[1].children[1].children[0].name, 'win7')
        self.assertEqual(self.treenode.children[1].children[1].children[1].name, 'win8')

    def test_values(self):
        self.assertDictEqual(self.treenode.children[0].children[0].children[0].value, {'arch': ['i386', 'x86-64']})
        self.assertDictEqual(self.treenode.children[0].children[0].children[1].value, {'arch': ['arm', 'arm64']})
        self.assertDictEqual(self.treenode.children[1].children[0].value, {'dev-tools': 'gcc', 'pm': 'tar'})
        self.assertDictEqual(self.treenode.children[1].children[1].value, {'dev-tools': 'cygwin'})

    def test_parent(self):
        self.assertIsNone(self.treenode.parent)
        self.assertIsNone(self.treenode.children[0].parent.parent)
        self.assertEqual(self.treenode.children[0].parent, self.treenode)
        self.assertEqual(self.treenode.children[0].children[0].parent, self.treenode.children[0])
        self.assertEqual(self.treenode.children[0].children[0].parent.parent, self.treenode)

    def test_environment(self):
        self.assertDictEqual(self.treenode.children[0].children[0].environment, {'arch': ['noarch']})
        self.assertDictEqual(self.treenode.children[0].children[0].children[0].environment, {'arch': ['noarch', 'i386', 'x86-64']})
        self.assertDictEqual(self.treenode.children[0].children[0].children[1].environment, {'arch': ['noarch', 'arm', 'arm64']})
        self.assertDictEqual(self.treenode.children[1].children[0].environment, {'dev-tools': 'gcc', 'pm': 'tar'})
        self.assertDictEqual(self.treenode.children[1].children[0].children[0].environment, {'dev-tools': 'gcc', 'pm': 'rpm'})
        self.assertDictEqual(self.treenode.children[1].children[0].children[1].environment, {'dev-tools': 'gcc', 'pm': 'deb'})
        self.assertDictEqual(self.treenode.children[1].children[0].children[2].environment, {'dev-tools': 'gcc', 'pm': 'rpm'})
        self.assertDictEqual(self.treenode.children[1].children[1].environment, {'dev-tools': 'cygwin'})
        self.assertDictEqual(self.treenode.children[1].children[1].children[0].environment, {'dev-tools': 'cygwin', 'metro': False})
        self.assertDictEqual(self.treenode.children[1].children[1].children[1].environment, {'dev-tools': 'cygwin', 'metro': True})

    def test_detach(self):
        n = self.treenode.children[1].detach()
        self.assertEqual(n.name, 'os')
        self.assertNotIn(n, self.treenode.children)


class TestPathParent(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(path_parent(''), '')

    def test_on_root(self):
        self.assertEqual(path_parent('/'), '')

    def test_direct_parent(self):
        self.assertEqual(path_parent('/os/linux'), '/os')

    def test_false_direct_parent(self):
        self.assertNotEqual(path_parent('/os/linux'), '/')


if __name__ == '__main__':
    unittest.main()
