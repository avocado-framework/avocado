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

from . import output
from . import tree


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
        Iterates through variants
        """
        pools = []
        for pool in self.pools:
            if isinstance(pool, list):
                pools.append(itertools.chain(*pool))
            else:
                pools.append(pool)
        pools = itertools.product(*pools)
        while True:
            # TODO: Implement 2nd level filters here
            # TODO: This part takes most of the time, optimize it
            yield list(itertools.chain(*pools.next()))


class MuxPlugin(object):
    """
    Base implementation of Mux-like Varianter plugin. It should be used as
    a base class in conjunction with
    :class:`avocado.core.plugin_interfaces.VarianterPlugin`.
    """
    root = None
    variants = None
    default_params = None
    mux_path = None
    debug = None

    def initialize_mux(self, root, mux_path, debug):
        """
        Initialize the basic values

        :note: We can't use __init__ as this object is intended to be used
               via dispatcher with no __init__ arguments.
        """
        self.root = root
        self.mux_path = mux_path
        self.debug = debug

    def __iter__(self):
        """
        See :meth:`avocado.core.plugin_interfaces.VarianterPlugin.__iter__`
        """
        if self.root is None:
            return
        for i, variant in enumerate(self.variants, 1):
            yield i, (variant, self.mux_path)

    def update_defaults(self, defaults):
        """
        See
        :meth:`avocado.core.plugin_interfaces.VarianterPlugin.update_defaults`
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
        See :meth:`avocado.core.plugin_interfaces.VarianterPlugin.to_str`
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
            contents = variants - 1
            out.append("Multiplex variants:")
            for (index, tpl) in enumerate(self.variants):
                if not self.debug:
                    paths = ', '.join([x.path for x in tpl])
                else:
                    color = output.TERM_SUPPORT.LOWLIGHT
                    cend = output.TERM_SUPPORT.ENDC
                    paths = ', '.join(["%s%s@%s%s" % (_.name, color,
                                                      getattr(_, 'yaml',
                                                              "Unknown"),
                                                      cend)
                                       for _ in tpl])
                out.append('%sVariant %s:    %s' % ('\n' if contents else '',
                                                    index + 1, paths))
                if contents:
                    env = set()
                    for node in tpl:
                        for key, value in node.environment.iteritems():
                            origin = node.environment_origin[key].path
                            env.add(("%s:%s" % (origin, key), str(value)))
                    if not env:
                        continue
                    fmt = '    %%-%ds => %%s' % max([len(_[0]) for _ in env])
                    for record in sorted(env):
                        out.append(fmt % record)
        return "\n".join(out)

    def __len__(self):
        """
        See :meth:`avocado.core.plugin_interfaces.VarianterPlugin.__len__`
        """
        if self.root is None:
            return 0
        return sum(1 for _ in self)


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


class MuxTreeNodeDebug(MuxTreeNode, tree.TreeNodeDebug):

    """
    Debug version of TreeNodeDebug
    :warning: Origin of the value is appended to all values thus it's not
    suitable for running tests.
    """

    def __init__(self, name='', value=None, parent=None, children=None,
                 srcyaml=None):
        MuxTreeNode.__init__(self, name, value, parent, children)
        tree.TreeNodeDebug.__init__(self, name, value, parent, children,
                                    srcyaml)

    def merge(self, other):
        MuxTreeNode.merge(self, other)
        tree.TreeNodeDebug.merge(self, other)


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
