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
# Copyright: Red Hat Inc. 2016
# Author: Lukas Doktor <ldoktor@redhat.com>
"""Multiplexer plugin to parse yaml files to params"""

import logging
import os
import re
import sys

from avocado.core import tree, exit_codes
from avocado.core.plugin_interfaces import CLI


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


# Mapping for yaml flags
YAML_INCLUDE = 100
YAML_USING = 101
YAML_REMOVE_NODE = tree.REMOVE_NODE
YAML_REMOVE_VALUE = tree.REMOVE_VALUE
YAML_MUX = 102

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


def _create_from_yaml(path, cls_node=tree.TreeNode):
    """ Create tree structure from yaml stream """
    def tree_node_from_values(name, values):
        """ Create `name` node and add values  """
        node = cls_node(str(name))
        using = ''
        for value in values:
            if isinstance(value, tree.TreeNode):
                node.add_child(value)
            elif isinstance(value[0], tree.Control):
                if value[0].code == YAML_INCLUDE:
                    # Include file
                    ypath = value[1]
                    if not os.path.isabs(ypath):
                        ypath = os.path.join(os.path.dirname(path), ypath)
                    if not os.path.exists(ypath):
                        raise ValueError("File '%s' included from '%s' does not "
                                         "exist." % (ypath, path))
                    node.merge(_create_from_yaml('/:' + ypath, cls_node))
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
        _value = []
        for key_node, value_node in node.value:
            if key_node.tag.startswith('!'):    # reflect tags everywhere
                key = loader.construct_object(key_node)
            else:
                key = loader.construct_python_str(key_node)
            value = loader.construct_object(value_node)
            _value.append((key, value))
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
        Special !mux loader which allows to tag node as 'multiplex = True'.
        """
        if not isinstance(obj, yaml.ScalarNode):
            objects = mapping_to_tree_loader(loader, obj)
        else:   # This means it's empty node. Don't call mapping_to_tree_loader
            objects = ListOfNodeObjects()
        objects.append((tree.Control(YAML_MUX), None))
        return objects

    Loader.add_constructor(u'!include',
                           lambda loader, node: tree.Control(YAML_INCLUDE))
    Loader.add_constructor(u'!using',
                           lambda loader, node: tree.Control(YAML_USING))
    Loader.add_constructor(u'!remove_node',
                           lambda loader, node: tree.Control(YAML_REMOVE_NODE))
    Loader.add_constructor(u'!remove_value',
                           lambda loader, node: tree.Control(YAML_REMOVE_VALUE))
    Loader.add_constructor(u'!mux', mux_loader)
    Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                           mapping_to_tree_loader)

    # Parse file name ([$using:]$path)
    path = __RE_FILE_SPLIT.split(path, 1)
    if len(path) == 1:
        path = __RE_FILE_SUBS.sub(':', path[0])
        using = ["run"]
    else:
        nodes = __RE_FILE_SUBS.sub(':', path[0]).strip('/').split('/')
        using = [node for node in nodes if node]
        if not path[0].startswith('/'):  # relative path, put into /run
            using.insert(0, 'run')
        path = __RE_FILE_SUBS.sub(':', path[1])

    # Load the tree
    with open(path) as stream:
        loaded_tree = yaml.load(stream, Loader)
        if loaded_tree is None:
            return
        loaded_tree = tree_node_from_values('', loaded_tree)

    # Add prefix
    if using:
        loaded_tree.name = using.pop()
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
        tmp = _create_from_yaml(path)
        if tmp:
            data.merge(tmp)

    def _merge_debug(data, path):
        """ Use NamedTreeNodeDebug magic """
        node_cls = tree.get_named_tree_cls(path)
        tmp = _create_from_yaml(path, node_cls)
        if tmp:
            data.merge(tmp)

    if not debug:
        data = tree.TreeNode()
        merge = _merge
    else:
        data = tree.TreeNodeDebug()
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


class YamlToMux(CLI):

    """
    Registers callback to inject params from yaml file to the
    """

    name = 'yaml_to_mux'
    description = "YamlToMux options for the 'run' subcommand"

    def configure(self, parser):
        """
        Configures "run" and "multiplex" subparsers
        """
        if not MULTIPLEX_CAPABLE:
            return
        for name in ("run", "multiplex"):
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            mux = subparser.add_argument_group("yaml to mux options")
            mux.add_argument("-m", "--mux-yaml", nargs='*', metavar="FILE",
                             help="Location of one or more Avocado"
                             " multiplex (.yaml) FILE(s) (order dependent)")
            mux.add_argument("--multiplex", nargs='*',
                             default=None, metavar="FILE",
                             help="DEPRECATED: Location of one or more Avocado"
                             " multiplex (.yaml) FILE(s) (order dependent)")

    def run(self, args):
        # Merge the multiplex
        multiplex_files = getattr(args, "mux_yaml", None)
        if multiplex_files:
            debug = getattr(args, "mux_debug", False)
            try:
                args.mux.data_merge(create_from_yaml(multiplex_files, debug))
            except IOError as details:
                logging.getLogger("avocado.app").error(details.strerror)
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)

        # Deprecated --multiplex option
        multiplex_files = getattr(args, "multiplex", None)
        if multiplex_files:
            msg = ("The use of `--multiplex` is deprecated, use `--mux-yaml` "
                   "instead.")
            logging.getLogger("avocado.app").warning(msg)
            debug = getattr(args, "mux_debug", False)
            try:
                args.mux.data_merge(create_from_yaml(multiplex_files, debug))
            except IOError as details:
                logging.getLogger("avocado.app").error(details.strerror)
                sys.exit(exit_codes.AVOCADO_JOB_FAIL)
