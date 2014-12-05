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
# Copyright: Jaime Huerta-Cepas <jhcepas@gmail.com> 2009
#
# Authors: Ruda Moura <rmoura@redhat.com>
#          Lucas Meneghel Rodrigues <lmr@redhat.com>
#          Jaime Huerta-Cepas <jhcepas@gmail.com>
#

"""
Tree data strucure with nodes.

This tree structure (Tree drawing code) was inspired in the base tree data
structure of the ETE 2 project:

http://pythonhosted.org/ete2/

A library for analysis of phylogenetics trees.

Explicit permission has been given by the copyright owner of ETE 2
Jaime Huerta-Cepas <jhcepas@gmail.com> to take ideas/use snippets from his
original base tree code and re-license under GPLv2+, given that GPLv3 and GPLv2
(used in some avocado files) are incompatible.
"""

import collections
import yaml


try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


class TreeNode(object):

    def __init__(self, name='', value=None, parent=None, children=None):
        if value is None:
            value = collections.OrderedDict()
        if children is None:
            children = []
        self.name = name
        self.value = value
        self.parent = parent
        self.children = []
        for child in children:
            self.add_child(child)

    def __repr__(self):
        return 'TreeNode(name=%r)' % self.name

    def __str__(self):
        variables = ['%s=%s' % (k, v) for k, v in self.environment.items()]
        return '%s: %s' % (self.path, ', '.join(variables))

    def __len__(self):
        return len(tuple(self.iter_leaves()))

    def __iter__(self):
        return self.iter_leaves()

    def __eq__(self, other):
        if isinstance(other, str):  # Compare names
            if self.name == other:
                return True
        elif isinstance(other, self.__class__):
            first = self.__dict__.copy()
            first.pop('parent')
            second = other.__dict__.copy()
            second.pop('parent')
            return first == second
        return False

    def add_child(self, node):
        if isinstance(node, self.__class__):
            if node.name in self.children:
                self.children[self.children.index(node.name)].merge(node)
            else:
                node.parent = self
                self.children.append(node)
        else:
            raise ValueError('Bad node type.')

    def merge(self, other):
        """ Merges $other node into this one (doesn't check the name) """
        self.value.update(other.value)
        for child in other.children:
            self.add_child(child)

    @property
    def is_leaf(self):
        return len(self.children) == 0

    @property
    def root(self):
        return self.get_root()

    def get_root(self):
        root = None
        for root in self.iter_parents():
            pass
        return root

    def iter_parents(self):
        node = self.parent
        while True:
            if node is None:
                raise StopIteration
            yield node
            node = node.parent

    @property
    def parents(self):
        return self.get_parents()

    def get_parents(self):
        return list(self.iter_parents())

    @property
    def path(self):
        return self.get_path()

    def get_path(self, sep='/'):
        path = [str(self.name)]
        for node in self.iter_parents():
            path.append(str(node.name))
        return sep.join(reversed(path))

    @property
    def environment(self):
        return self.get_environment()

    def get_environment(self):
        def update_or_extend(target, source):
            for k, _ in source.items():
                if k in target and isinstance(target[k], list):
                    target[k].extend(source[k])
                else:
                    if isinstance(source[k], list):
                        target[k] = source[k][:]
                    else:
                        target[k] = source[k]
        env = collections.OrderedDict()
        rev_parents = reversed(self.get_parents())
        for parent in rev_parents:
            update_or_extend(env, parent.value)
        update_or_extend(env, self.value)
        return env

    def iter_children_preorder(self, node=None):
        q = collections.deque()
        node = self
        while node is not None:
            yield node
            q.extendleft(reversed(node.children))
            try:
                node = q.popleft()
            except:
                node = None

    def iter_leaves(self):
        for node in self.iter_children_preorder():
            if node.is_leaf:
                yield node

    def get_leaves(self):
        return list(self.iter_leaves())

    def get_ascii(self, show_internal=True, compact=False, attributes=None):
        (lines, _) = self._ascii_art(show_internal=show_internal,
                                     compact=compact, attributes=attributes)
        return '\n' + '\n'.join(lines)

    def _ascii_art(self, char1='-', show_internal=True, compact=False,
                   attributes=None):
        if attributes is None:
            attributes = ["name"]
        node_name = ', '.join(map(str, [getattr(self, v)
                                        for v in attributes
                                        if hasattr(self, v)]))

        LEN = max(3, len(node_name)
                  if not self.children or show_internal else 3)
        PAD = ' ' * LEN
        PA = ' ' * (LEN - 1)
        if not self.is_leaf:
            mids = []
            result = []
            for c in self.children:
                if len(self.children) == 1:
                    char2 = '/'
                elif c is self.children[0]:
                    char2 = '/'
                elif c is self.children[-1]:
                    char2 = '\\'
                else:
                    char2 = '-'
                (clines, mid) = c._ascii_art(char2, show_internal, compact,
                                             attributes)
                mids.append(mid + len(result))
                result.extend(clines)
                if not compact:
                    result.append('')
            if not compact:
                result.pop()
            (lo, hi, end) = (mids[0], mids[-1], len(result))
            prefixes = ([PAD] * (lo + 1) + [PA + '|'] * (hi - lo - 1)
                        + [PAD] * (end - hi))
            mid = (lo + hi) / 2
            prefixes[mid] = char1 + '-' * (LEN - 2) + prefixes[mid][-1]
            result = [p + l for (p, l) in zip(prefixes, result)]
            if show_internal:
                stem = result[mid]
                result[mid] = stem[0] + node_name + stem[len(node_name) + 1:]
            return result, mid
        else:
            return [char1 + '-' + node_name], 0

    def detach(self):
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None
        return self


def _create_from_yaml(stream):
    """ Create tree structure from yaml stream """
    class Value(tuple):

        """ Used to mark values to simplify checking for node vs. value """
        pass

    def tree_node_from_values(name, values):
        """ Create $name node and add values  """
        node_children = []
        node_values = []
        for value in values:
            if isinstance(value, TreeNode):
                node_children.append(value)
            else:
                node_values.append(value)
        return TreeNode(name, dict(node_values), children=node_children)

    def mapping_to_tree_loader(loader, node):
        def is_node(values):
            if (isinstance(values, list) and values
                    and isinstance(values[0], (Value, TreeNode))):
                # When any value is TreeNode or Value, all of them are already
                # parsed and we can wrap them into self
                return True

        _value = loader.construct_pairs(node)
        objects = []
        for name, values in _value:
            if is_node(values):    # New node
                objects.append(tree_node_from_values(name, values))
            elif values is None:            # Empty node
                objects.append(TreeNode(name))
            else:                           # Values
                objects.append(Value((name, values)))
        return objects
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                           mapping_to_tree_loader)
    return tree_node_from_values('', yaml.load(stream, Loader))


def create_from_yaml(paths):
    """
    Create tree structure from yaml-like file
    :param fileobj: File object to be processed
    :raise SyntaxError: When yaml-file is corrupted
    :return: Root of the created tree structure
    """
    data = TreeNode()
    try:
        for path in paths:
            data.merge(_create_from_yaml(open(path).read()))
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as err:
        raise SyntaxError(err)
    return data


def path_parent(path):
    """
    From a given path, return its parent path.

    :param path: the node path as string.
    :return: the parent path as string.
    """
    parent = path.rpartition('/')[0]
    if parent == '':
        return ''
    return parent


def apply_filters(tree, filter_only=None, filter_out=None):
    """
    Apply a set of filters to the tree.

    The basic filtering is filter only, which includes nodes,
    and the filter out rules, that exclude nodes.

    Note that filter_out is stronger than filter_only, so if you filter out
    something, you could not bypass some nodes by using a filter_only rule.

    :param filter_only: the list of paths which will include nodes.
    :param filter_out: the list of paths which will exclude nodes.
    :return: the original tree minus the nodes filtered by the rules.
    """
    if filter_only is None:
        filter_only = []
    if filter_out is None:
        filter_out = []
    for node in tree.iter_children_preorder():
        keep_node = True
        for path in filter_only:
            if path == '':
                continue
            if node.path == path:
                keep_node = True
                break
            if node.parent and node.parent.path == path_parent(path):
                keep_node = False
                continue
        for path in filter_out:
            if path == '':
                continue
            if node.path == path:
                keep_node = False
                break
        if not keep_node:
            node.detach()
    return tree
