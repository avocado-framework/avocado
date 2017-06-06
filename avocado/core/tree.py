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
Tree data structure with nodes.

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
import itertools
import locale
import os

from . import output


class FilterSet(set):

    """ Set of filters in standardized form """

    @staticmethod
    def __normalize(item):
        if not item.endswith("/"):
            item = item + "/"
        return item

    def add(self, item):
        return super(FilterSet, self).add(self.__normalize(item))

    def update(self, items):
        return super(FilterSet, self).update([self.__normalize(item)
                                              for item in items])


class TreeEnvironment(dict):

    """ TreeNode environment with values, origins and filters """

    def __init__(self):
        super(TreeEnvironment, self).__init__()     # values
        self.origin = {}    # origins of the values
        self.filter_only = FilterSet()   # list of filter_only
        self.filter_out = FilterSet()    # list of filter_out

    def copy(self):
        cpy = TreeEnvironment()
        cpy.update(self)
        cpy.origin = self.origin.copy()
        cpy.filter_only = self.filter_only.copy()
        cpy.filter_out = self.filter_out.copy()
        return cpy

    def __str__(self):
        # Use __str__ instead of __repr__ to improve readability
        if self:
            _values = ["%s: %s" % _ for _ in self.iteritems()]
            values = "{%s}" % ", ".join(_values)
            _origin = ["%s: %s" % (key, node.path)
                       for key, node in self.origin.iteritems()]
            origin = "{%s}" % ", ".join(_origin)
        else:
            values = "{}"
            origin = "{}"
        return ",".join((values, origin, str(self.filter_only),
                         str(self.filter_out)))


class TreeNodeEnvOnly(object):

    """
    Minimal TreeNode-like class providing interface for AvocadoParams
    """
    def __init__(self, path, environment=None):
        """
        :param path: Path of this node (must not end with '/')
        :param environment: List of pair/key/value items
        """
        self.name = path.rsplit("/")[-1]
        self.path = path
        self.environment = TreeEnvironment()
        if environment:
            self.__load_environment(environment)

    def __load_environment(self, environment):
        nodes = {}
        for path, key, value in environment:
            self.environment[key] = value
            if path not in nodes:
                nodes[path] = TreeNodeEnvOnly(path)
            self.environment.origin[key] = nodes[path]

    def get_environment(self):
        return self.environment

    def get_path(self):
        return self.path


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
        self.filters = [], []  # This node's filters, full filters are in env
        self.parent = parent
        self.children = []
        self._environment = None
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

    def __ne__(self, other):
        """ Inverted eq """
        return not self == other

    def fingerprint(self):
        """
        Reports string which represents the value of this node.
        """
        return "%s%s" % (self.path, self.environment)

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
        self.value.update(other.value)
        self.filters[0].extend(other.filters[0])
        self.filters[1].extend(other.filters[1])
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
        if not self.parent:
            return sep + str(self.name)
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
                                 if self.parent else TreeEnvironment())
            for key, value in self.value.iteritems():
                if isinstance(value, list):
                    if (key in self._environment and
                            isinstance(self._environment[key], list)):
                        self._environment[key] = self._environment[key] + value
                    else:
                        self._environment[key] = value
                else:
                    self._environment[key] = value
                self._environment.origin[key] = self
            self._environment.filter_only.update(self.filters[0])
            self._environment.filter_out.update(self.filters[1])
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

    def get_node(self, path, create=False):
        """
        :param path: Path of the desired node (relative to this node)
        :param create: Create the node (and intermediary ones) when not present
        :return: the node associated with this path
        :raise ValueError: When path doesn't exist and create not set
        """
        node = self
        for name in path.split('/'):
            if not name:
                continue
            try:
                node = node.children[node.children.index(name)]
            except ValueError:
                if create:
                    child = node.__class__(name)
                    node.add_child(child)
                    node = child
                else:
                    raise ValueError("Path %s does not exists in this tree\n%s"
                                     % (path, tree_view(self.root)))
        return node

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
        """ Iterate through leaf nodes """
        for node in self.iter_children_preorder():
            if node.is_leaf:
                yield node

    def get_leaves(self):
        """ Get list of leaf nodes """
        return list(self.iter_leaves())

    def detach(self):
        """ Detach this node from parent """
        if self.parent:
            self.parent.children.remove(self)
            self.parent = None
        return self


#
# Debug version of TreeNode with additional utilities.
#


class OutputValue(object):  # only container pylint: disable=R0903

    """ Ordinary value with some debug info """

    def __init__(self, value, node, srcyaml):
        self.value = value
        self.node = node
        self.yaml = srcyaml

    def __str__(self):
        return "%s%s@%s:%s%s" % (self.value,
                                 output.TERM_SUPPORT.LOWLIGHT,
                                 self.yaml, self.node.path,
                                 output.TERM_SUPPORT.ENDC)


class OutputList(list):  # only container pylint: disable=R0903

    """ List with some debug info """

    def __init__(self, values, nodes, yamls):
        super(OutputList, self).__init__(values)
        self.nodes = nodes
        self.yamls = yamls

    def __add__(self, other):
        """ Keep attrs separate in order to print the origins """
        value = super(OutputList, self).__add__(other)
        return OutputList(value,
                          self.nodes + other.nodes,
                          self.yamls + other.yamls)

    def __str__(self):
        color = output.TERM_SUPPORT.LOWLIGHT
        cend = output.TERM_SUPPORT.ENDC
        return ' + '.join("%s%s@%s:%s%s"
                          % (_[0], color, _[1], _[2].path, cend)
                          for _ in itertools.izip(self, self.yamls,
                                                  self.nodes))


class ValueDict(dict):  # only container pylint: disable=R0903

    """ Dict which stores the origin of the items """

    def __init__(self, srcyaml, node, values):
        super(ValueDict, self).__init__()
        self.yaml = srcyaml
        self.node = node
        self.yaml_per_key = {}
        for key, value in values.iteritems():
            self[key] = value

    def __setitem__(self, key, value):
        """ Store yaml_per_key and value """
        # Merge is responsible to set `self.yaml` to current file
        self.yaml_per_key[key] = self.yaml
        return super(ValueDict, self).__setitem__(key, value)

    def __getitem__(self, key):
        """
        This is debug run. Fake the results and return either
        OutputValue (let's call it string) and OutputList. These
        overrides the `__str__` and return string with origin.
        :warning: Returned values are unusable in tests!
        """
        value = super(ValueDict, self).__getitem__(key)
        origin = self.yaml_per_key.get(key)
        if isinstance(value, list):
            value = OutputList([value], [self.node], [origin])
        else:
            value = OutputValue(value, self.node, origin)
        return value

    def iteritems(self):
        """ Slower implementation with the use of __getitem__ """
        for key in self.iterkeys():
            yield key, self[key]
        raise StopIteration


class TreeNodeDebug(TreeNode):  # only container pylint: disable=R0903

    """
    Debug version of TreeNodeDebug
    :warning: Origin of the value is appended to all values thus it's not
    suitable for running tests.
    """

    def __init__(self, name='', value=None, parent=None, children=None,
                 srcyaml=None):
        if value is None:
            value = {}
        if srcyaml:
            srcyaml = os.path.relpath(srcyaml)
        super(TreeNodeDebug, self).__init__(name,
                                            ValueDict(srcyaml, self, value),
                                            parent, children)
        self.yaml = srcyaml

    def merge(self, other):
        """
        Override origin with the one from other tree. Updated/Newly set values
        are going to use this location as origin.
        """
        if hasattr(other, 'yaml') and other.yaml:
            srcyaml = os.path.relpath(other.yaml)
            # when we use TreeNodeDebug, value is always ValueDict
            self.value.yaml_per_key.update(other.value.yaml_per_key)    # pylint: disable=E1101
        else:
            srcyaml = "Unknown"
        self.yaml = srcyaml
        self.value.yaml = srcyaml
        return super(TreeNodeDebug, self).merge(other)


def get_named_tree_cls(path, klass=TreeNodeDebug):
    """ Return TreeNodeDebug class with hardcoded yaml path """
    class NamedTreeNodeDebug(klass):    # pylint: disable=R0903

        """ Fake class with hardcoded yaml path """

        def __init__(self, name='', value=None, parent=None,
                     children=None):
            super(NamedTreeNodeDebug, self).__init__(name, value, parent,
                                                     children,
                                                     path.split(':', 1)[-1])
    return NamedTreeNodeDebug


def tree_view(root, verbose=None, use_utf8=None):
    """
    Generate tree-view of the given node
    :param root: root node
    :param verbose: verbosity (0, 1, 2, 3)
    :param use_utf8: Use utf-8 encoding (None=autodetect)
    :return: string representing this node's tree structure
    """

    def prefixed_write(prefix1, prefix2, value):
        """
        Split value's lines and prepend empty prefix to 2nd+ lines
        :return: list of lines
        """
        value = str(value)
        if '\n' not in value:
            return [prefix1 + prefix2 + value]
        value = value.splitlines()
        empty_prefix2 = ' ' * len(prefix2)
        return [prefix1 + prefix2 + value[0]] + [prefix1 + empty_prefix2 +
                                                 _ for _ in value[1:]]

    def process_node(node):
        """
        Generate this node's tree-view
        :return: list of lines
        """
        if getattr(node, "multiplex", None):
            down = charset['DoubleDown']
            down_right = charset['DoubleDownRight']
            right = charset['DoubleRight']
        else:
            down = charset['Down']
            down_right = charset['DownRight']
            right = charset['Right']
        out = [node.name]
        if verbose >= 2 and node.is_leaf:
            values = itertools.chain(node.environment.iteritems(),
                                     [("filter-only", _)
                                      for _ in node.environment.filter_only],
                                     [("filter-out", _)
                                      for _ in node.environment.filter_out])
        elif verbose in (1, 3):
            values = itertools.chain(node.value.iteritems(),
                                     [("filter-only", _)
                                      for _ in node.filters[0]],
                                     [("filter-out", _)
                                      for _ in node.filters[1]])
        else:
            values = None
        if values:
            val = charset['Value']
            if node.children:
                val_prefix = down
            else:
                val_prefix = '  '
            for key, value in values:
                out.extend(prefixed_write(val_prefix, "%s%s: " % (val, key),
                                          value))
        if node.children:
            for child in node.children[:-1]:
                lines = process_node(child)
                out.append(down_right + lines[0])
                out.extend(down + line for line in lines[1:])
            lines = process_node(node.children[-1])
            out.append(right + lines[0])
            empty_down_right = ' ' * len(down_right)
            out.extend(empty_down_right + line for line in lines[1:])
        return out

    if use_utf8 is None:
        use_utf8 = locale.getdefaultlocale()[1] == 'UTF-8'
    if use_utf8:
        charset = {'DoubleDown': u' \u2551   ',
                   'DoubleDownRight': u' \u2560\u2550\u2550 ',
                   'DoubleRight': u' \u255a\u2550\u2550 ',
                   'Down': u' \u2503   ',
                   'DownRight': u' \u2523\u2501\u2501 ',
                   'Right': u' \u2517\u2501\u2501 ',
                   'Value': u'\u2192 '}
    else:   # ASCII fallback
        charset = {'Down': ' |   ',
                   'DownRight': ' |-- ',
                   'Right': ' \\-- ',
                   'DoubleDown': ' #   ',
                   'DoubleDownRight': ' #== ',
                   'DoubleRight': ' #== ',
                   'Value': ' -> '}
    if getattr(root, "multiplex", None):
        down = charset['DoubleDown']
        down_right = charset['DoubleDownRight']
        right = charset['DoubleRight']
    else:
        down = charset['Down']
        down_right = charset['DownRight']
        right = charset['Right']
    out = []
    if (verbose >= 2) and root.is_leaf:
        values = root.environment.iteritems()
    elif verbose in (1, 3):
        values = root.value.iteritems()
    else:
        values = None
    if values:
        prefix = charset['Value'].lstrip()
        for key, value in values:
            out.extend(prefixed_write(prefix, key + ': ', value))
    if root.children:
        for child in root.children[:-1]:
            lines = process_node(child)
            out.append(down_right + lines[0])
            out.extend(down + line for line in lines[1:])
        lines = process_node(root.children[-1])
        out.append(right + lines[0])
        out.extend(' ' * len(down_right) + line for line in lines[1:])
    # When not on TTY we need to force the encoding
    return '\n'.join(out).encode('utf-8' if use_utf8 else 'ascii')
