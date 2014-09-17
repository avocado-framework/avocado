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


def path_parent(path):
    """
    From a given path, return its parent path.

    :param path: the node path as string.
    :return: the parent path as string.
    """
    parent = path.rpartition('/')[0]
    if parent == '':
        return '/root'
    return parent


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

# only allow items which match the filter
# siblings and their children will be removed


def filter_only(keys, items):

    if isinstance(keys, str):
        keys = [keys]
    if isinstance(items, str):
        items = [items]

    # the default rule is to accept
    ret = True

    for key in keys:
        # ignore empty filters
        if key == '':
            continue

        for item in items:
            # key is part of the item, let the branch in
            if item.path.startswith(key):
                return True

            # siblings and their children, filter them out
            if item.parent.path.startswith(path_parent(key)):
                ret = False
                continue

    # everything else should go in
    return ret

# remove one item and its children


def filter_out(keys, items):

    if isinstance(keys, str):
        keys = [keys]
    if isinstance(items, str):
        items = [items]

    for key in keys:
        # ignore empty filters
        if key == '':
            continue

        for item in items:
            # key is part of the item, leave the branch out
            if item.path.startswith(key):
                return False

            # sibling and its children, let them in
            if item.path.startswith(path_parent(key)):
                continue

    # everything else should get in
    return True


def multiplex(*args, **kwargs):
    f_only = kwargs.get('filter_only', [''])
    f_out = kwargs.get('filter_out', [''])
    leaves = []
    parents = collections.OrderedDict()
    # filter args and create a set of parents
    for arg in args[0]:
        if filter_only(f_only, [arg]) and filter_out(f_out, [arg]):
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
        result = [x + [y] for x in result for y in pool
                  if any_sibling(*(x + [y])) is False and
                  filter_only(y.environment.get('filter-only', []), x + [y]) and
                  filter_out(y.environment.get('filter-out', []), x + [y])]

        # if a pool gets totally filtered out above, result will be empty
        if len(result) == 0:
            result = result_prev
        else:
            result_prev = result

    if result == [[]]:
        return

    for prod in result:
        yield tuple(prod)


def create_variants_from_yaml(input_yaml, filter_only=[], filter_out=[]):
    input_tree = tree.create_from_yaml(input_yaml)
    leaves = input_tree.get_leaves()
    variants = multiplex(leaves,
                         filter_only=filter_only,
                         filter_out=filter_out)
    return variants
