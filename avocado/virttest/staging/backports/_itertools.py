"""
This module contains some itertools functions people have been using in
virt-test that are not present in python 2.4, the minimum supported version.
"""


def product(*args, **kwds):
    """
    (virt-test backport)
    Cartesian product of input iterables. Equivalent to nested for-loops.

    For example, product(A, B) returns the same as:  ((x,y) for x in A for y in B).
    The leftmost iterators are in the outermost for-loop, so the output tuples
    cycle in a manner similar to an odometer (with the rightmost element changing
    on every iteration).

    To compute the product of an iterable with itself, specify the number
    of repetitions with the optional repeat keyword argument. For example,
    product(A, repeat=4) means the same as product(A, A, A, A).

    product('ab', range(3)) --> ('a',0) ('a',1) ('a',2) ('b',0) ('b',1) ('b',2)
    product((0,1), (0,1), (0,1)) --> (0,0,0) (0,0,1) (0,1,0) (0,1,1) (1,0,0) ...
    """
    # product('ABCD', 'xy') --> Ax Ay Bx By Cx Cy Dx Dy
    # product(range(2), repeat=3) --> 000 001 010 011 100 101 110 111
    pools = map(tuple, args) * kwds.get('repeat', 1)
    result = [[]]
    for pool in pools:
        result = [x + [y] for x in result for y in pool]
    for prod in result:
        yield tuple(prod)
