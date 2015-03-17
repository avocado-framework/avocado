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
#          Ademar Reis <areis@redhat.com>
#          Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Multiplex and create variants.
"""

import itertools

from avocado.core import tree

MULTIPLEX_CAPABLE = tree.MULTIPLEX_CAPABLE


def tree2pools(node, mux=True):
    """
    Process tree and flattens the structure to remaining leaves and
    list of lists of leaves per each multiplex group.
    :param node: Node to start with
    :return: tuple(`leaves`, `pools`), where `leaves` are directly inherited
    leaves of this node (no other multiplex in the middle). `pools` is list of
    lists of directly inherited leaves of the nested multiplex domains.
    """
    leaves = []
    pools = []
    if mux:
        # TODO: Get this multiplex leaves filters and store them in this pool
        # to support 2nd level filtering
        new_leaves = []
        for child in node.children:
            if child.is_leaf:
                new_leaves.append(child)
            else:
                _leaves, _pools = tree2pools(child, node.multiplex)
                new_leaves.extend(_leaves)
                # TODO: For 2nd level filters store this separately in case
                # this branch is filtered out
                pools.extend(_pools)
        if new_leaves:
            # TODO: Filter the new_leaves (and new_pools) before merging
            # into pools
            pools.append(new_leaves)
    else:
        for child in node.children:
            if child.is_leaf:
                leaves.append(child)
            else:
                _leaves, _pools = tree2pools(child, node.multiplex)
                leaves.extend(_leaves)
                pools.extend(_pools)
    return leaves, pools


def multiplex_yamls(input_yamls, filter_only=None, filter_out=None,
                    debug=False):
    if filter_only is None:
        filter_only = []
    if filter_out is None:
        filter_out = []
    input_tree = tree.create_from_yaml(input_yamls, debug)
    # TODO: Process filters and multiplex simultaneously
    final_tree = tree.apply_filters(input_tree, filter_only, filter_out)
    leaves, pools = tree2pools(final_tree, final_tree.multiplex)
    if leaves:  # Add remaining leaves (they are not variants, only endpoints
        pools.extend(leaves)
    return itertools.product(*pools)
