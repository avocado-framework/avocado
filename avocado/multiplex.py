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
# Author: Ruda Moura <rmoura@redhat.com>

"""
Module that multiplex arguments.
"""

def parent(element):
    e = element.rpartition('/')[0]
    if e == '':
        return '/'
    return e

def any_sibling(*args):
    result = (parent(arg[0]) for arg in args)
    result = set(result)
    return len(args) != len(result)

# only allow items which match the filter
# siblings and their children will be removed
def filter_only(keys, item):

    # the default rule is to accept
    ret = True

    for key in keys:
        # ignore empty filters
        if key == '':
            continue

        # key is part of the item, let the branch in
        if item.startswith(key):
            return True

        # siblings and their children, filter them out
        if parent(item).startswith(parent(key)):
            ret = False
            continue

    # everything else should go in
    return ret

# remove one item and its children
def filter_out(keys, item):

    for key in keys:
        # ignore empty filters
        if key == '':
            continue

        # key is part of the item, leave the branch out
        if item.startswith(key):
            return False

        # sibling and its children, let them in
        if item.startswith(parent(key)):
            continue

    # everything else should get in
    return True

def multiplex(*args, **kwargs):
    f_only = kwargs.get('filter_only', [''])
    f_out = kwargs.get('filter_out', [''])
    leaves = []
    parents = set()
    # filter args and create a set of parents
    for arg in args[0]:
        if filter_only(f_only, arg[0]) and filter_out(f_out, arg[0]):
            leaves.append(arg)
            parents.add(parent(arg[0]))

    pools = []
    for p in parents:
        pools.append(leaves)
        leaves = [x for x in leaves if parent(x[0]) != p]

    result = [[]]
    result_prev = [[]]
    for pool in pools:

        # second level of filtering above should use the filter strings
        # extracted from the node being worked on
        # (not implemented here, so using [] as placeholders)
        result = [x+[y] for x in result for y in pool \
            if any_sibling(*(x+[y])) is False and \
               filter_only([], y[0]) and \
               filter_out([], y[0])]

        # if a pool gets totally filtered out above, result will be empty
        if len(result) == 0:
            result = result_prev
        else:
            result_prev = result

    if result == [[]]:
        return

    for prod in result:
        yield tuple(prod)
