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
#          Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Tree data strucure with nodes.
"""

import collections

import yaml


class TreeNode(object):

    def __init__(self, name='/root', value=None, parent=None, children=None):
        if value is None:
            value = {}
        if children is None:
            children = []
        self.name = name
        self.value = value
        self.parent = parent
        self.children = children

    def __repr__(self):
        return 'TreeNode(name=%r, value=%r, parent=%r, children=%r)' % (self.name, self.value, self.parent, self.children)

    def __str__(self):
        return '%s=%r' % (self.name, self.environment)

    def __len__(self):
        return len(self.get_leaves())

    def __iter__(self):
        return self.iter_leaves()

    def add_child(self, node):
        if isinstance(node, self.__class__):
            node.parent = self
            self.children.append(node)
        else:
            raise ValueError('Bad node type.')
        return node

    @property
    def is_leaf(self):
        return len(self.children) == 0

    @property
    def root(self):
        return self.get_root()

    def get_root(self):
        root = self
        while root.parent is not None:
            root = root.parent
        return root

    def iter_parents(self):
        node = self
        while node.parent is not None:
            yield node.parent
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
        path = [self.name]
        for node in self.iter_parents():
            path.append(node.name)
        return sep.join(reversed(path))

    @property
    def environment(self):
        return self.get_environment()

    def get_environment(self):
        def update_or_extend(target, source):
            for k, v in source.items():
                if target.has_key(k) and isinstance(target[k], list):
                    target[k].extend(source[k])
                else:
                    if isinstance(source[k], list):
                        target[k] = source[k][:]
                    else:
                        target[k] = source[k]
        env = {}
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
        (lines, mid) = self._ascii_art(show_internal=show_internal,
                                       compact=compact, attributes=attributes)
        return '\n' + '\n'.join(lines)

    def _ascii_art(self, char1='-', show_internal=True, compact=False, attributes=None):
        if attributes is None:
            attributes = ["name"]
        node_name = ', '.join(map(str, [getattr(self, v) for v in attributes if hasattr(self, v)]))

        LEN = max(3, len(node_name) if not self.children or show_internal else 3)
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
                (clines, mid) = c._ascii_art(char2, show_internal, compact, attributes)
                mids.append(mid + len(result))
                result.extend(clines)
                if not compact:
                    result.append('')
            if not compact:
                result.pop()
            (lo, hi, end) = (mids[0], mids[-1], len(result))
            prefixes = [PAD] * (lo + 1) + [PA + '|'] * (hi - lo - 1) + [PAD] * (end - hi)
            mid = (lo + hi) / 2
            prefixes[mid] = char1 + '-' * (LEN - 2) + prefixes[mid][-1]
            result = [p + l for (p, l) in zip(prefixes, result)]
            if show_internal:
                stem = result[mid]
                result[mid] = stem[0] + node_name + stem[len(node_name) + 1:]
            return result, mid
        else:
            return [char1 + '-' + node_name], 0


def ordered_load(stream, Loader=yaml.Loader,
                 object_pairs_hook=collections.OrderedDict):
    class OrderedLoader(Loader):
        pass
    OrderedLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                                  lambda loader, node:
                                  object_pairs_hook(loader.construct_pairs(node)))
    return yaml.load(stream, OrderedLoader)


def read_ordered_yaml(fileobj):
    try:
        data = ordered_load(fileobj.read())
    except (yaml.scanner.ScannerError, yaml.parser.ParserError) as err:
        raise SyntaxError(err)
    return data


def create_from_ordered_data(data, tree=None, root=None, name='/root'):
    if tree is None:
        tree = TreeNode(name)
    if root is None:
        root = tree
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                leaf = True
                for k, v in value.items():
                    if isinstance(v, dict):
                        leaf = False
                node = TreeNode(key)
                tree.add_child(node)
                create_from_ordered_data(value, node, root)
            elif value is None:
                # Leaf without variable
                node = TreeNode(key)
                tree.add_child(node)
            else:
                # Node/leaf with variable
                tree.value.update({key: value})
    return root


def create_from_yaml(input_yaml):
    data = read_ordered_yaml(input_yaml)
    return create_from_ordered_data(data)
