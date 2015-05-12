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
import re

# Mapping for yaml flags
YAML_INCLUDE = 0
YAML_USING = 1
YAML_REMOVE_NODE = 2
YAML_REMOVE_VALUE = 3
YAML_JOIN = 4


class Control(object):  # Few methods pylint: disable=R0903

    """ Container used to identify node vs. control sequence """

    def __init__(self, code, value=None):
        self.code = code
        self.value = value


class TreeNode(object):

    """
    Class for bounding nodes into tree-structure.
    """

    def __init__(self, name='', value=None, parent=None, children=None):
        if value is None:
            value = {}
        if children is None:
            children = []
        self.name = name
        self.value = value
        self.parent = parent
        self.children = []
        self._environment = None
        self.environment_origin = {}
        self.ctrl = []
        self.multiplex = True
        for child in children:
            self.add_child(child)

    def __repr__(self):
        return 'TreeNode(name=%r)' % self.name

    def __str__(self):
        variables = ['%s=%s' % (k, v) for k, v in self.environment.items()]
        return '%s: %s' % (self.path, ', '.join(variables))

    def __len__(self):
        """ Return number of descended leaf nodes """
        return len(tuple(self.iter_leaves()))

    def __iter__(self):
        """ Iterate through descended leaf nodes """
        return self.iter_leaves()

    def __eq__(self, other):
        """ Compares node to other node or string to name of this node """
        if isinstance(other, str):  # Compare names
            if self.name == other:
                return True
        else:
            for attr in ('name', 'value', 'children'):
                if getattr(self, attr) != getattr(other, attr):
                    return False
            return True

    def add_child(self, node):
        """
        Append node as child. Nodes with the same name gets merged into the
        existing position.
        """
        if isinstance(node, TreeNode):
            if node.name in self.children:
                self.children[self.children.index(node.name)].merge(node)
            else:
                node.parent = self
                self.children.append(node)
        else:
            raise ValueError('Bad node type.')

    def merge(self, other):
        """
        Merges `other` node into this one without checking the name of the
        other node. New values are appended, existing values overwritten
        and unaffected ones are kept. Then all other node children are
        added as children (recursively they get either appended at the end
        or merged into existing node in the previous position.
        """
        for ctrl in other.ctrl:
            if isinstance(ctrl, Control):
                if ctrl.code == YAML_REMOVE_NODE:
                    remove = []
                    regexp = re.compile(ctrl.value)
                    for child in self.children:
                        if regexp.match(child.name):
                            remove.append(child)
                    for child in remove:
                        self.children.remove(child)
                elif ctrl.code == YAML_REMOVE_VALUE:
                    remove = []
                    regexp = re.compile(ctrl.value)
                    for key in self.value.iterkeys():
                        if regexp.match(key):
                            remove.append(key)
                    for key in remove:
                        self.value.pop(key, None)
        self.multiplex &= other.multiplex
        self.value.update(other.value)
        for child in other.children:
            self.add_child(child)

    @property
    def is_leaf(self):
        """ Is this a leaf node? """
        return not self.children

    @property
    def root(self):
        """ Root of this tree """
        return self.get_root()

    def get_root(self):
        """ Get root of this tree """
        root = self
        for root in self.iter_parents():
            pass
        return root

    def iter_parents(self):
        """ Iterate through parent nodes to root """
        node = self.parent
        while True:
            if node is None:
                raise StopIteration
            yield node
            node = node.parent

    @property
    def parents(self):
        """ List of parent nodes """
        return self.get_parents()

    def get_parents(self):
        """ Get list of parent nodes """
        return list(self.iter_parents())

    @property
    def path(self):
        """ Node path """
        return self.get_path()

    def get_path(self, sep='/'):
        """ Get node path """
        path = [str(self.name)]
        for node in self.iter_parents():
            path.append(str(node.name))
        return sep.join(reversed(path))

    @property
    def environment(self):
        """ Node environment (values + preceding envs) """
        return self.get_environment()

    def get_environment(self):
        """ Get node environment (values + preceding envs) """
        if self._environment is None:
            self._environment = (self.parent.environment.copy()
                                 if self.parent else {})
            self.environment_origin = (self.parent.environment_origin.copy()
                                       if self.parent else {})
            for key, value in self.value.iteritems():
                if isinstance(value, list):
                    if (key in self._environment and
                            isinstance(self._environment[key], list)):
                        self._environment[key] = self._environment[key] + value
                    else:
                        self._environment[key] = value
                else:
                    self._environment[key] = value
                self.environment_origin[key] = self
        return self._environment

    def set_environment_dirty(self):
        """
        Set the environment cache dirty. You should call this always when
        you query for the environment and then change the value or structure.
        Otherwise you'll get the old environment instead.
        """
        for child in self.children:
            child.set_environment_dirty()
        self._environment = None

    def iter_children_preorder(self):
        """ Iterate through children """
        queue = collections.deque()
        node = self
        while node is not None:
            yield node
            queue.extendleft(reversed(node.children))
            try:
                node = queue.popleft()
            except IndexError:
                node = None

    def iter_leaves(self):
        """ Iterate throuh leaf nodes """
        for node in self.iter_children_preorder():
            if node.is_leaf:
                yield node

    def get_leaves(self):
        """ Get list of leaf nodes """
        return list(self.iter_leaves())

    def get_ascii(self, show_internal=True, compact=False, attributes=None):
        """
        Get ascii-art tree structure
        :param show_internal: Show intermediary nodes
        :param compact: Compress the tree vertically
        :param attributes: List of node attributes to be printed out ['name']
        :return: string
        """
        (lines, _) = self.ascii_art(show_internal=show_internal,
                                    compact=compact, attributes=attributes)
        return '\n' + '\n'.join(lines)

    def ascii_art(self, char1='-', show_internal=True, compact=False,
                  attributes=None):
        """
        Generate ascii-art for this node
        :param char1: Incomming path character [-]
        :param show_internal: Show intermediary nodes
        :param compact: Compress the tree vertically
        :param attributes: List of node attributes to be printed out ['name']
        :return: list of strings
        """
        if not attributes:
            attributes = ["name"]
        node_name = ', '.join(map(str, [getattr(self, v)
                                        for v in attributes
                                        if hasattr(self, v)]))

        length = max(2, (len(node_name) + 1) if not self.children or show_internal else 3)
        pad = ' ' * length
        _pad = ' ' * (length - 1)
        if not self.is_leaf:
            mids = []
            result = []
            for char in self.children:
                if len(self.children) == 1:
                    char2 = '-'
                elif char is self.children[0]:
                    char2 = '/'
                elif char is self.children[-1]:
                    char2 = '\\'
                else:
                    char2 = '-'
                (clines, mid) = char.ascii_art(char2, show_internal, compact,
                                               attributes)
                mids.append(mid + len(result))
                result.extend(clines)
                if not compact:
                    result.append('')
            if not compact:
                result.pop()
            (low, high, end) = (mids[0], mids[-1], len(result))
            prefixes = ([pad] * (low + 1) + [_pad + '|'] * (high - low - 1) +
                        [pad] * (end - high))
            mid = (low + high) / 2
            prefixes[mid] = char1 + '-' * (length - 2) + prefixes[mid][-1]
            result = [p + l for (p, l) in zip(prefixes, result)]
            if show_internal:
                stem = result[mid]
                result[mid] = stem[0] + node_name + stem[len(node_name) + 1:]
            return result, mid
        else:
            return [char1 + '-' + node_name], 0

    def detach(self):
        """ Detach this node from parent """
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None
        return self
