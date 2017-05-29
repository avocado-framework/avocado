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
# Copyright: Red Hat Inc. 2016-2017
# Author: Lukas Doktor <ldoktor@redhat.com>
"""Varianter plugin to parse yaml files to params"""

import copy
import os
import re
import sys

from avocado.core import tree, exit_codes, mux
from avocado.core.output import LOG_UI
from avocado.core.plugin_interfaces import CLI, Varianter


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
YAML_REMOVE_NODE = mux.REMOVE_NODE
YAML_REMOVE_VALUE = mux.REMOVE_VALUE
YAML_MUX = 102
YAML_FILTER_ONLY = 103
YAML_FILTER_OUT = 104

__RE_FILE_SPLIT = re.compile(r'(?<!\\):')   # split by ':' but not '\\:'
__RE_FILE_SUBS = re.compile(r'(?<!\\)\\:')  # substitute '\\:' but not '\\\\:'


class _BaseLoader(Loader):
    """
    YAML loader with additional features related to mux
    """
    Loader.add_constructor(u'!include',
                           lambda loader, node: mux.Control(YAML_INCLUDE))
    Loader.add_constructor(u'!using',
                           lambda loader, node: mux.Control(YAML_USING))
    Loader.add_constructor(u'!remove_node',
                           lambda loader, node: mux.Control(YAML_REMOVE_NODE))
    Loader.add_constructor(u'!remove_value',
                           lambda loader, node: mux.Control(YAML_REMOVE_VALUE))
    Loader.add_constructor(u'!filter-only',
                           lambda loader, node: mux.Control(YAML_FILTER_ONLY))
    Loader.add_constructor(u'!filter-out',
                           lambda loader, node: mux.Control(YAML_FILTER_OUT))


class Value(tuple):     # Few methods pylint: disable=R0903

    """ Used to mark values to simplify checking for node vs. value """
    pass


class ListOfNodeObjects(list):     # Few methods pylint: disable=R0903

    """
    Used to mark list as list of objects from whose node is going to be created
    """
    pass


def _create_from_yaml(path, cls_node=mux.MuxTreeNode):
    """ Create tree structure from yaml stream """
    def tree_node_from_values(name, values):
        """ Create `name` node and add values  """
        def handle_control_tag(node, value):
            """ Handling of YAML tags (except of !using) """
            def normalize_path(path):
                """ End the path with single '/', None when empty path """
                if not path:
                    return
                if path[-1] != '/':
                    path += '/'
                return path

            if value[0].code == YAML_INCLUDE:
                # Include file
                ypath = value[1]
                if not os.path.isabs(ypath):
                    ypath = os.path.join(os.path.dirname(path), ypath)
                if not os.path.exists(ypath):
                    raise ValueError("File '%s' included from '%s' does not "
                                     "exist." % (ypath, path))
                node.merge(_create_from_yaml('/:' + ypath, cls_node))
            elif value[0].code == YAML_REMOVE_NODE:
                value[0].value = value[1]   # set the name
                node.ctrl.append(value[0])    # add "blue pill" of death
            elif value[0].code == YAML_REMOVE_VALUE:
                value[0].value = value[1]   # set the name
                node.ctrl.append(value[0])
            elif value[0].code == YAML_MUX:
                node.multiplex = True
            elif value[0].code == YAML_FILTER_ONLY:
                new_value = normalize_path(value[1])
                if new_value:
                    node.filters[0].append(new_value)
            elif value[0].code == YAML_FILTER_OUT:
                new_value = normalize_path(value[1])
                if new_value:
                    node.filters[1].append(new_value)

        def handle_control_tag_using(name, using, value):
            """ Handling of the !using tag """
            if using:
                raise ValueError("!using can be used only once per "
                                 "node! (%s:%s)" % (path, name))
            using = value[1]
            if using[0] == '/':
                using = using[1:]
            if using[-1] == '/':
                using = using[:-1]
            return using

        node = cls_node(str(name))
        using = ''
        for value in values:
            if isinstance(value, cls_node):
                node.add_child(value)
            elif isinstance(value[0], mux.Control):
                if value[0].code == YAML_USING:
                    using = handle_control_tag_using(name, using, value)
                else:
                    handle_control_tag(node, value)
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
        objects.append((mux.Control(YAML_MUX), None))
        return objects

    # For each instance we need different `cls_node`, therefor different
    # !mux and default mapping loader constructors
    loader = copy.copy(_BaseLoader)
    loader.add_constructor(u'!mux', mux_loader)
    loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
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
        loaded_tree = yaml.load(stream, loader)
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
        node_cls = tree.get_named_tree_cls(path, mux.MuxTreeNodeDebug)
        tmp = _create_from_yaml(path, node_cls)
        if tmp:
            data.merge(tmp)

    if not debug:
        data = mux.MuxTreeNode()
        merge = _merge
    else:
        data = mux.MuxTreeNodeDebug()
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


class YamlToMuxCLI(CLI):

    """
    Defines arguments for YamlToMux plugin
    """

    name = 'yaml_to_mux'
    description = "YamlToMux options for the 'run' subcommand"

    def configure(self, parser):
        """
        Configures "run" and "variants" subparsers
        """
        if not MULTIPLEX_CAPABLE:
            return
        for name in ("run", "multiplex", "variants"):
            subparser = parser.subcommands.choices.get(name, None)
            if subparser is None:
                continue
            mux = subparser.add_argument_group("yaml to mux options")
            mux.add_argument("-m", "--mux-yaml", nargs='*', metavar="FILE",
                             help="Location of one or more Avocado"
                             " multiplex (.yaml) FILE(s) (order dependent)")
            mux.add_argument('--mux-filter-only', nargs='*', default=[],
                             help='Filter only path(s) from multiplexing')
            mux.add_argument('--mux-filter-out', nargs='*', default=[],
                             help='Filter out path(s) from multiplexing')
            mux.add_argument('--mux-path', nargs='*', default=None,
                             help="List of default paths used to determine "
                             "path priority when querying for parameters")
            mux.add_argument('--mux-inject', default=[], nargs='*',
                             help="Inject [path:]key:node values into the "
                             "final multiplex tree.")
            mux = subparser.add_argument_group("yaml to mux options "
                                               "[deprecated]")
            mux.add_argument("--multiplex", nargs='*',
                             default=None, metavar="FILE",
                             help="DEPRECATED: Location of one or more Avocado"
                             " multiplex (.yaml) FILE(s) (order dependent)")
            mux.add_argument("--filter-only", nargs='*', default=[],
                             help="DEPRECATED: Filter only path(s) from "
                             "multiplexing (use --mux-filter-only instead)")
            mux.add_argument("--filter-out", nargs='*', default=[],
                             help="DEPRECATED: Filter out path(s) from "
                             "multiplexing (use --mux-filter-out instead)")

    def run(self, args):
        """
        The YamlToMux varianter plugin handles these
        """


class YamlToMux(mux.MuxPlugin, Varianter):

    """
    Processes the mux options into varianter plugin
    """

    name = 'yaml_to_mux'
    description = 'Multiplexer plugin to parse yaml files to params'

    @staticmethod
    def _log_deprecation_msg(deprecated, current):
        """
        Log a message into the avocado.LOG_UI warning log
        """
        msg = "The use of '%s' is deprecated, please use '%s' instead"
        LOG_UI.warning(msg, deprecated, current)

    def initialize(self, args):
        # Deprecated filters
        only = getattr(args, "filter_only", None)
        if only:
            self._log_deprecation_msg("--filter-only", "--mux-filter-only")
            mux_filter_only = getattr(args, "mux_filter_only")
            if mux_filter_only:
                args.mux_filter_only = mux_filter_only + only
            else:
                args.mux_filter_only = only
        out = getattr(args, "filter_out", None)
        if out:
            self._log_deprecation_msg("--filter-out", "--mux-filter-out")
            mux_filter_out = getattr(args, "mux_filter_out")
            if mux_filter_out:
                args.mux_filter_out = mux_filter_out + out
            else:
                args.mux_filter_out = out
        if args.avocado_variants.debug:
            data = mux.MuxTreeNodeDebug()
        else:
            data = mux.MuxTreeNode()

        debug = getattr(args, "mux_debug", False)

        # Merge the multiplex
        multiplex_files = getattr(args, "mux_yaml", None)
        if multiplex_files:
            try:
                data.merge(create_from_yaml(multiplex_files, debug))
            except IOError as details:
                error_msg = "%s : %s" % (details.strerror, details.filename)
                LOG_UI.error(error_msg)
                if args.subcommand == 'run':
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                else:
                    sys.exit(exit_codes.AVOCADO_FAIL)

        # Deprecated --multiplex option
        multiplex_files = getattr(args, "multiplex", None)
        if multiplex_files:
            self._log_deprecation_msg("--multiplex", "--mux-yaml")
            try:
                data.merge(create_from_yaml(multiplex_files, debug))
                from_yaml = create_from_yaml(multiplex_files, debug)
                args.avocado_variants.data_merge(from_yaml)
            except IOError as details:
                error_msg = "%s : %s" % (details.strerror, details.filename)
                LOG_UI.error(error_msg)
                if args.subcommand == 'run':
                    sys.exit(exit_codes.AVOCADO_JOB_FAIL)
                else:
                    sys.exit(exit_codes.AVOCADO_FAIL)

        # Extend default multiplex tree of --mux-inject values
        for inject in getattr(args, "mux_inject", []):
            entry = inject.split(':', 3)
            if len(entry) < 2:
                raise ValueError("key:entry pairs required, found only %s"
                                 % (entry))
            elif len(entry) == 2:   # key, entry
                entry.insert(0, '')  # add path='' (root)
            data.get_node(entry[0], True).value[entry[1]] = entry[2]

        mux_filter_only = getattr(args, 'mux_filter_only', None)
        mux_filter_out = getattr(args, 'mux_filter_out', None)
        data = mux.apply_filters(data, mux_filter_only, mux_filter_out)
        if data != mux.MuxTreeNode():
            mux_path = getattr(args, "mux_path", ["/run/*"])
            if mux_path is None:
                mux_path = ["/run/*"]
            self.initialize_mux(data, mux_path, debug)
