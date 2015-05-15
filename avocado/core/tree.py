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
import itertools
import os
import re

try:
    import yaml
except ImportError:
    MULTIPLEX_CAPABLE = False
else:
    MULTIPLEX_CAPABLE = True
    try:
        from yaml import CLoader as Loader
    except ImportError:
        from yaml import Loader

from avocado.core import output

# Mapping for yaml flags
YAML_INCLUDE = 0
YAML_USING = 1
YAML_REMOVE_NODE = 2
YAML_REMOVE_VALUE = 3
YAML_MUX = 4

__RE_FILE_SPLIT = re.compile(r'(?<!\\):')   # split by ':' but not '\\:'
__RE_FILE_SUBS = re.compile(r'(?<!\\)\\:')  # substitute '\\:' but not '\\\\:'


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
        self.multiplex = False
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
        self.multiplex = other.multiplex
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
        if self.multiplex:
            node_name += "-<>"

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


class Value(tuple):     # Few methods pylint: disable=R0903

    """ Used to mark values to simplify checking for node vs. value """
    pass


class ListOfNodeObjects(list):     # Few methods pylint: disable=R0903

    """
    Used to mark list as list of objects from whose node is going to be created
    """
    pass


def _create_from_yaml(path, cls_node=TreeNode):
    """ Create tree structure from yaml stream """
    def tree_node_from_values(name, values):
        """ Create `name` node and add values  """
        node = cls_node(str(name))
        using = ''
        for value in values:
            if isinstance(value, TreeNode):
                node.add_child(value)
            elif isinstance(value[0], Control):
                if value[0].code == YAML_INCLUDE:
                    # Include file
                    ypath = value[1]
                    if not os.path.isabs(ypath):
                        ypath = os.path.join(os.path.dirname(path), ypath)
                    node.merge(_create_from_yaml(ypath, cls_node))
                elif value[0].code == YAML_USING:
                    if using:
                        raise ValueError("!using can be used only once per "
                                         "node! (%s:%s)" % (path, name))
                    using = value[1]
                    if using[0] == '/':
                        using = using[1:]
                    if using[-1] == '/':
                        using = using[:-1]
                elif value[0].code == YAML_REMOVE_NODE:
                    value[0].value = value[1]   # set the name
                    node.ctrl.append(value[0])    # add "blue pill" of death
                elif value[0].code == YAML_REMOVE_VALUE:
                    value[0].value = value[1]   # set the name
                    node.ctrl.append(value[0])
                elif value[0].code == YAML_MUX:
                    node.multiplex = True
            else:
                node.value[value[0]] = value[1]
        if using:
            if name is not '':
                for name in using.split('/')[::-1]:
                    node = cls_node(name, children=[node])
            else:
                using = using.split('/')[::-1]
                node.name = using.pop()
                while True:
                    if not using:
                        break
                    name = using.pop()  # 'using' is list pylint: disable=E1101
                    node = cls_node(name, children=[node])
                node = cls_node('', children=[node])
        return node

    def mapping_to_tree_loader(loader, node):
        """ Maps yaml mapping tag to TreeNode structure """
        _value = loader.construct_pairs(node)
        objects = ListOfNodeObjects()
        for name, values in _value:
            if isinstance(values, ListOfNodeObjects):   # New node from list
                objects.append(tree_node_from_values(name, values))
            elif values is None:            # Empty node
                objects.append(cls_node(str(name)))
            else:                           # Values
                objects.append(Value((name, values)))
        return objects

    def mux_loader(loader, obj):
        """
        Special !mux loader which allows to tag node as 'multiplex = False'.
        """
        if not isinstance(obj, yaml.ScalarNode):
            objects = mapping_to_tree_loader(loader, obj)
        else:   # This means it's empty node. Don't call mapping_to_tree_loader
            objects = ListOfNodeObjects()
        objects.append((Control(YAML_MUX), None))
        return objects

    Loader.add_constructor(u'!include',
                           lambda loader, node: Control(YAML_INCLUDE))
    Loader.add_constructor(u'!using',
                           lambda loader, node: Control(YAML_USING))
    Loader.add_constructor(u'!remove_node',
                           lambda loader, node: Control(YAML_REMOVE_NODE))
    Loader.add_constructor(u'!remove_value',
                           lambda loader, node: Control(YAML_REMOVE_VALUE))
    Loader.add_constructor(u'!mux', mux_loader)
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                           mapping_to_tree_loader)

    # Parse file name ([$using:]$path)
    path = __RE_FILE_SPLIT.split(path, 1)
    if len(path) == 1:
        path = __RE_FILE_SUBS.sub(':', path[0])
        using = None
    else:
        nodes = __RE_FILE_SUBS.sub(':', path[0]).strip('/').split('/')
        using = [node for node in nodes if node]
        path = __RE_FILE_SUBS.sub(':', path[1])

    # Load the tree
    with open(path) as stream:
        loaded_tree = yaml.load(stream, Loader)
        loaded_tree = tree_node_from_values('', loaded_tree)

    # Add prefix
    if using:
        loaded_tree = cls_node(using.pop(), children=loaded_tree.children)
        while True:
            if not using:
                break
            loaded_tree = cls_node(using.pop(), children=[loaded_tree])
        loaded_tree = cls_node('', children=[loaded_tree])
    return loaded_tree


def create_from_yaml(paths, debug=False):
    """
    Create tree structure from yaml-like file
    :param fileobj: File object to be processed
    :raise SyntaxError: When yaml-file is corrupted
    :return: Root of the created tree structure
    """
    def _merge(data, path):
        """ Normal run """
        data.merge(_create_from_yaml(path))

    def _merge_debug(data, path):
        """ Use NamedTreeNodeDebug magic """
        node_cls = get_named_tree_cls(path)
        data.merge(_create_from_yaml(path, node_cls))

    if not debug:
        data = TreeNode()
        merge = _merge
    else:
        data = TreeNodeDebug()
        merge = _merge_debug

    path = None
    try:
        for path in paths:
            merge(data, path)
    # Yaml can raise IndexError on some files
    except (yaml.YAMLError, IndexError) as details:
        if 'mapping values are not allowed in this context' in str(details):
            details = ("%s\nMake sure !tags and colons are separated by a "
                       "space (eg. !include :)" % details)
        msg = "Invalid multiplex file '%s': %s" % (path, details)
        raise IOError(2, msg, path)
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
                                 output.term_support.LOWLIGHT,
                                 self.yaml, self.node.path,
                                 output.term_support.ENDC)


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
        color = output.term_support.LOWLIGHT
        cend = output.term_support.ENDC
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
        if hasattr(other, 'yaml'):
            srcyaml = os.path.relpath(other.yaml)
            # when we use TreeNodeDebug, value is always ValueDict
            self.value.yaml_per_key.update(other.value.yaml_per_key)    # pylint: disable=E1101
        else:
            srcyaml = "Unknown"
        self.yaml = srcyaml
        self.value.yaml = srcyaml
        return super(TreeNodeDebug, self).merge(other)


def get_named_tree_cls(path):
    """ Return TreeNodeDebug class with hardcoded yaml path """
    class NamedTreeNodeDebug(TreeNodeDebug):    # pylint: disable=R0903

        """ Fake class with hardcoded yaml path """

        def __init__(self, name='', value=None, parent=None,
                     children=None):
            super(NamedTreeNodeDebug, self).__init__(name, value, parent,
                                                     children, path)
    return NamedTreeNodeDebug
