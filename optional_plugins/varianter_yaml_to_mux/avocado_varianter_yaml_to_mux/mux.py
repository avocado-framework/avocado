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
#
# Authors: Lukas Doktor <ldoktor@redhat.com>

"""
This file contains mux-enabled implementations of parts useful for creating
a custom Varianter plugin.
"""
#
# Multiplex-enabled tree objects
#

import collections
import itertools
import re
import os

from six import iterkeys, iteritems
from six.moves import xrange as range

from avocado.core import tree
from avocado.core import varianter
from avocado.core import output


#
# Multiplex-enabled tree objects
#
REMOVE_NODE = 0
REMOVE_VALUE = 1


class MuxTree(object):

    """
    Object representing part of the tree from the root to leaves or another
    multiplex domain. Recursively it creates multiplexed variants of the full
    tree.
    """

    def __init__(self, root):
        """
        :param root: Root of this tree slice
        """
        self.pools = []
        for node in self._iter_mux_leaves(root):
            if node.is_leaf:
                self.pools.append(node)
            else:
                self.pools.append([MuxTree(child) for child in node.children])

    @staticmethod
    def _iter_mux_leaves(node):
        """ yield leaves or muxes of the tree """
        queue = collections.deque()
        while node is not None:
            if node.is_leaf or getattr(node, "multiplex", None):
                yield node
            else:
                queue.extendleft(reversed(node.children))
            try:
                node = queue.popleft()
            except IndexError:
                raise StopIteration

    def __iter__(self):
        """
        Iterates through variants and process the internal filters

        :yield valid variants
        """
        for variant in self.iter_variants():
            if self._valid_variant(variant):
                yield variant

    def iter_variants(self):
        """
        Iterates through variants without verifying the internal filters

        :yield all existing variants
        """
        pools = []
        for pool in self.pools:
            if isinstance(pool, list):
                # Don't process 2nd level filters in non-root pools
                pools.append(itertools.chain(*(_.iter_variants()
                                               for _ in pool)))
            else:
                pools.append([pool])
        variants = itertools.product(*pools)
        while True:
            yield list(itertools.chain(*next(variants)))

    @staticmethod
    def _valid_variant(variant):
        """
        Check the variant for validity of internal filters

        :return: whether the variant is valid or should be ignored/filtered
        """
        _filter_out = set()
        _filter_only = set()
        for node in variant:
            _filter_only.update(node.environment.filter_only)
            _filter_out.update(node.environment.filter_out)
        if not (_filter_only or _filter_out):
            return True
        filter_only = tuple(_filter_only)
        filter_out = tuple(_filter_out)
        filter_only_parents = [str(_).rsplit('/', 2)[0] + '/'
                               for _ in filter_only
                               if _]

        for out in filter_out:
            for node in variant:
                path = node.path + '/'
                if path.startswith(out):
                    return False
        for node in variant:
            keep = 0
            remove = 0
            path = node.path + '/'
            ppath = path.rsplit('/', 2)[0] + '/'
            for i in range(len(filter_only)):
                level = filter_only[i].count('/')
                if level < max(keep, remove):
                    continue
                if ppath.startswith(filter_only_parents[i]):
                    if path.startswith(filter_only[i]):
                        keep = level
                    else:
                        remove = level
            if remove > keep:
                return False
        return True


class MuxPlugin(object):
    """
    Base implementation of Mux-like Varianter plugin. It should be used as
    a base class in conjunction with
    :class:`avocado.core.plugin_interfaces.Varianter`.
    """
    root = None
    variants = None
    default_params = None
    paths = None
    debug = None

    def initialize_mux(self, root, paths, debug):
        """
        Initialize the basic values

        :note: We can't use __init__ as this object is intended to be used
               via dispatcher with no __init__ arguments.
        """
        self.root = root
        self.paths = paths
        self.debug = debug
        self.variant_ids = self._get_variant_ids()

    def _get_variant_ids(self):
        return [varianter.generate_variant_id(variant)
                for variant in MuxTree(self.root)]

    def __iter__(self):
        """
        See :meth:`avocado.core.plugin_interfaces.Varianter.__iter__`
        """
        if self.root is None:
            return

        for vid, variant in itertools.izip(self.variant_ids, self.variants):
            yield {"variant_id": vid,
                   "variant": variant,
                   "paths": self.paths}

    def update_defaults(self, defaults):
        """
        See
        :meth:`avocado.core.plugin_interfaces.Varianter.update_defaults`
        """
        if self.root is None:
            return
        if self.default_params:
            self.default_params.merge(defaults)
        self.default_params = defaults
        combination = defaults
        combination.merge(self.root)
        self.variants = MuxTree(combination)

    def to_str(self, summary, variants, **kwargs):
        """
        See :meth:`avocado.core.plugin_interfaces.Varianter.to_str`
        """
        if not self.variants:
            return ""
        out = []
        if summary:
            # Log tree representation
            out.append("Multiplex tree representation:")
            # summary == 0 means disable, but in plugin it's brief
            tree_repr = tree.tree_view(self.root, verbose=summary - 1,
                                       use_utf8=kwargs.get("use_utf8", None))
            out.append(tree_repr)
            out.append("")

        if variants:
            # variants == 0 means disable, but in plugin it's brief
            out.append("Multiplex variants (%s):" % len(self))
            for variant in self:
                out.extend(varianter.variant_to_str(variant, variants - 1,
                                                    kwargs, self.debug))
        return "\n".join(out)

    def __len__(self):
        """
        See :meth:`avocado.core.plugin_interfaces.Varianter.__len__`
        """
        if self.root is None:
            return 0
        return sum(1 for _ in self)


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
        for key, value in iteritems(values):
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
        for key in iterkeys(self):
            yield key, self[key]
        raise StopIteration


class Control(object):  # Few methods pylint: disable=R0903

    """ Container used to identify node vs. control sequence """

    def __init__(self, code, value=None):
        self.code = code
        self.value = value


class MuxTreeNode(tree.TreeNode):

    """
    Class for bounding nodes into tree-structure with support for
    multiplexation
    """

    def __init__(self, name='', value=None, parent=None, children=None):
        super(MuxTreeNode, self).__init__(name, value, parent, children)
        self.ctrl = []
        self.multiplex = None

    def __repr__(self):
        return '%s(name=%r)' % (self.__class__.__name__, self.name)

    def fingerprint(self):
        return "%s%s" % (super(MuxTreeNode, self).fingerprint(), self.ctrl)

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
                if ctrl.code == REMOVE_NODE:
                    remove = []
                    regexp = re.compile(ctrl.value)
                    for child in self.children:
                        if regexp.match(child.name):
                            remove.append(child)
                    for child in remove:
                        self.children.remove(child)
                elif ctrl.code == REMOVE_VALUE:
                    remove = []
                    regexp = re.compile(ctrl.value)
                    for key in self.value.iterkeys():
                        if regexp.match(key):
                            remove.append(key)
                    for key in remove:
                        self.value.pop(key, None)
        super(MuxTreeNode, self).merge(other)
        if other.multiplex is True:
            self.multiplex = True
        elif other.multiplex is False:
            self.multiplex = False


class TreeNodeDebug(tree.TreeNode):  # only container pylint: disable=R0903

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


class MuxTreeNodeDebug(MuxTreeNode, TreeNodeDebug):

    """
    Debug version of TreeNodeDebug
    :warning: Origin of the value is appended to all values thus it's not
    suitable for running tests.
    """

    def __init__(self, name='', value=None, parent=None, children=None,
                 srcyaml=None):
        MuxTreeNode.__init__(self, name, value, parent, children)
        TreeNodeDebug.__init__(self, name, value, parent, children,
                               srcyaml)

    def merge(self, other):
        MuxTreeNode.merge(self, other)
        TreeNodeDebug.merge(self, other)


#
# Tree filtering
#
def path_parent(path):
    """
    From a given path, return its parent path.

    :param path: the node path as string.
    :return: the parent path as string.
    """
    parent = path.rpartition('/')[0]
    if not parent:
        return '/'
    return parent


def apply_filters(root, filter_only=None, filter_out=None):
    """
    Apply a set of filters to the tree.

    The basic filtering is filter only, which includes nodes,
    and the filter out rules, that exclude nodes.

    Note that filter_out is stronger than filter_only, so if you filter out
    something, you could not bypass some nodes by using a filter_only rule.

    :param root: Root node of the multiplex tree.
    :param filter_only: the list of paths which will include nodes.
    :param filter_out: the list of paths which will exclude nodes.
    :return: the original tree minus the nodes filtered by the rules.
    """
    if filter_only is None:
        filter_only = []
    else:
        filter_only = [_.rstrip('/') for _ in filter_only if _]
    if filter_out is None:
        filter_out = []
    else:
        filter_out = [_.rstrip('/') for _ in filter_out if _]
    for node in root.iter_children_preorder():
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
    return root
