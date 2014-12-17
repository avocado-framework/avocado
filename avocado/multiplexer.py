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

import collections

from avocado.core import tree


def any_sibling(*nodes):
    """
    Check if there is any sibling.

    :param nodes: the nodes to check.
    :return: `True` if there is any sibling or `False`.
    """
    if len(nodes) < 2:
        return False
    parents = set(node.parent for node in nodes)
    return len(nodes) != len(parents)


def multiplex(*args):
    leaves = []
    parents = collections.OrderedDict()
    # filter args and create a set of parents
    for arg in args[0]:
        leaves.append(arg)
        parents[arg.parent] = True

    pools = []
    for p in parents.keys():
        pools.append(leaves)
        leaves = [x for x in leaves if x.parent != p]

    result = [[]]
    result_prev = [[]]
    for pool in pools:

        # second level of filtering above should use the filter strings
        # extracted from the node being worked on
        items = []
        for x in result:
            for y in pool:
                item = x + [y]
                if any_sibling(*item) is False:
                    items.append(item)
        result = items

        # if a pool gets totally filtered out above, result will be empty
        if len(result) == 0:
            result = result_prev
        else:
            result_prev = result

    if result == [[]]:
        return

    for prod in result:
        yield tuple(prod)


def multiplex_yamls(input_yamls, filter_only=None, filter_out=None,
                    debug=False):
    if filter_only is None:
        filter_only = []
    if filter_out is None:
        filter_out = []
    input_tree = tree.create_from_yaml(input_yamls, debug)
    final_tree = tree.apply_filters(input_tree, filter_only, filter_out)
    leaves = (x for x in final_tree.iter_leaves() if x.parent is not None)
    variants = multiplex(leaves)
    return variants
