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
Tree data strucure with nodes and YAML.

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

from avocado.core import tree_node

# Mapping for yaml flags
YAML_INCLUDE = 0
YAML_USING = 1
YAML_REMOVE_NODE = 2
YAML_REMOVE_VALUE = 3
YAML_JOIN = 4

__RE_FILE_SPLIT = re.compile(r'(?<!\\):')   # split by ':' but not '\\:'
__RE_FILE_SUBS = re.compile(r'(?<!\\)\\:')  # substitute '\\:' but not '\\\\:'


class Value(tuple):     # Few methods pylint: disable=R0903

    """ Used to mark values to simplify checking for node vs. value """
    pass


class ListOfNodeObjects(list):     # Few methods pylint: disable=R0903

    """
    Used to mark list as list of objects from whose node is going to be created
    """
    pass


def _create_from_yaml(path, cls_node=tree_node.TreeNode):
    """ Create tree structure from yaml stream """
    def tree_node_from_values(name, values):
        """ Create `name` node and add values  """
        node = cls_node(str(name))
        using = ''
        for value in values:
            if isinstance(value, tree_node.TreeNode):
                node.add_child(value)
            elif isinstance(value[0], tree_node.Control):
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
                elif value[0].code == YAML_JOIN:
                    node.multiplex = False
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

    def join_loader(loader, obj):
        """
        Special !join loader which allows to tag node as 'multiplex = False'.
        """
        if not isinstance(obj, yaml.ScalarNode):
            objects = mapping_to_tree_loader(loader, obj)
        else:   # This means it's empty node. Don't call mapping_to_tree_loader
            objects = ListOfNodeObjects()
        objects.append((tree_node.Control(YAML_JOIN), None))
        return objects

    Loader.add_constructor(u'!include',
                           lambda loader, node: tree_node.Control(YAML_INCLUDE))
    Loader.add_constructor(u'!using',
                           lambda loader, node: tree_node.Control(YAML_USING))
    Loader.add_constructor(u'!remove_node',
                           lambda loader, node: tree_node.Control(YAML_REMOVE_NODE))
    Loader.add_constructor(u'!remove_value',
                           lambda loader, node: tree_node.Control(YAML_REMOVE_VALUE))
    Loader.add_constructor(u'!join', join_loader)
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
        node_cls = tree_debug.get_named_tree_cls(path)
        data.merge(_create_from_yaml(path, node_cls))

    if not debug:
        data = tree_node.TreeNode()
        merge = _merge
    else:
        from avocado.core import tree_debug
        data = tree_debug.TreeNodeDebug()
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
