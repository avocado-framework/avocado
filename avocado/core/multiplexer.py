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
import itertools
import logging
import re

from . import tree


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
        self.root = root
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
            if node.is_leaf or node.multiplex:
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


# TODO: Create multiplexer plugin and split these functions into multiple files
class NoMatchError(KeyError):
    pass


class AvocadoParams(object):

    """
    Params object used to retrieve params from given path. It supports
    absolute and relative paths. For relative paths one can define multiple
    paths to search for the value.
    It contains compatibility wrapper to act as the original avocado Params,
    but by special usage you can utilize the new API. See ``get()``
    docstring for details.

    You can also iterate through all keys, but this can generate quite a lot
    of duplicate entries inherited from ancestor nodes.  It shouldn't produce
    false values, though.

    In this version each new "get()" call is logged into "avocado.test" log.
    This is subject of change (separate file, perhaps)
    """

    # TODO: Use "test" to log params.get()

    def __init__(self, leaves, test_id, mux_path, default_params):
        """
        :param leaves: List of TreeNode leaves defining current variant
        :param test_id: test id
        :param mux_path: list of entry points
        :param default_params: dict of params used when no matches found
        """
        self._rel_paths = []
        leaves = list(leaves)
        for i, path in enumerate(mux_path):
            path_leaves = self._get_matching_leaves(path, leaves)
            self._rel_paths.append(AvocadoParam(path_leaves,
                                                '%d: %s' % (i, path)))
        # Don't use non-mux-path params for relative paths
        path_leaves = self._get_matching_leaves('/*', leaves)
        self._abs_path = AvocadoParam(path_leaves, '*: *')
        self.id = test_id
        self._log = logging.getLogger("avocado.test").debug
        self._cache = {}     # TODO: Implement something more efficient
        # TODO: Get rid of this and prepare something better
        self._default_params = default_params

    def __eq__(self, other):
        if set(self.__dict__.iterkeys()) != set(other.__dict__.iterkeys()):
            return False
        for attr in self.__dict__.iterkeys():
            if (getattr(self, attr) != getattr(other, attr)):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __getstate__(self):
        """ log can't be pickled """
        copy = self.__dict__.copy()
        del(copy['_log'])
        return copy

    def __setstate__(self, orig):
        """ refresh log """
        self.__dict__.update(orig)
        self._log = logging.getLogger("avocado.test").debug

    def __repr__(self):
        return "<AvocadoParams %s>" % self._str()

    def __str__(self):
        return "params {%s}" % self._str()

    def _str(self):
        out = ",".join(_.str_leaves_variant for _ in self._rel_paths)
        if out:
            return self._abs_path.str_leaves_variant + ',' + out
        else:
            return self._abs_path.str_leaves_variant

    def log(self, key, path, default, value):
        """ Predefined format for displaying params query """
        self._log("PARAMS (key=%s, path=%s, default=%s) => %r", key, path,
                  default, value)

    def _get_matching_leaves(self, path, leaves):
        """
        Pops and returns list of matching nodes
        :param path: Path (str)
        :param leaves: list of TreeNode leaves
        """
        path = self._greedy_path(path)
        path_leaves = [leaf for leaf in leaves if path.search(leaf.path + '/')]
        for leaf in path_leaves:
            leaves.remove(leaf)
        return path_leaves

    @staticmethod
    def _greedy_path(path):
        """
        converts user-friendly asterisk path to python regexp and compiles it:
        path = ""             => ^$
        path = "/"            => /
        path = "/foo/bar"     => /foo/bar
        path = "foo/bar"      => $MUX_ENTRY/?.*/foo/bar
        path = "/*/foo"       => /[^/]*/foo
        path = "foo/*"        => $MUX_ENTRY/?.*/foo/.*
        path = "/foo/*"       => /foo/.*
        """
        if not path:
            return re.compile('^$')
        if path[-1] == '*':
            suffix = ''
            path = path[:-1]
        else:
            suffix = '$'
        return re.compile(path.replace('*', '[^/]*') + suffix)

    @staticmethod
    def _is_abspath(path):
        """ Is this an absolute or relative path? """
        if path.pattern and path.pattern[0] == '/':
            return True
        else:
            return False

    def __getattr__(self, attr):
        """
        Compatibility to old Params
        :warning: This will be removed soon. Use params.get() instead
        """
        if attr == '__getnewargs__':    # pickling uses this attr
            raise AttributeError
        elif attr in self.__dict__:
            return self.__dict__[attr]
        else:
            msg = ("You're probably retrieving param %s via attributes "
                   " (self.params.$key) which is obsoleted. Use "
                   "self.params.get($key) instead." % attr)
            logging.getLogger("avocado.test").warn(msg)
            return self.get(attr)

    def get(self, key, path=None, default=None):
        """
        Retrieve value associated with key from params
        :param key: Key you're looking for
        :param path: namespace ['*']
        :param default: default value when not found
        :raise KeyError: In case of multiple different values (params clash)
        """
        if path is None:    # default path is any relative path
            path = '*'
        try:
            return self._cache[(key, path, default)]
        except (KeyError, TypeError):
            # KeyError - first query
            # TypeError - unable to hash
            value = self._get(key, path, default)
            self.log(key, path, default, value)
            try:
                self._cache[(key, path, default)] = value
            except TypeError:
                pass
            return value

    def _get(self, key, path, default):
        """
        Actual params retrieval
        :param key: key you're looking for
        :param path: namespace
        :param default: default value when not found
        :raise KeyError: In case of multiple different values (params clash)
        """
        path = self._greedy_path(path)
        for param in self._rel_paths:
            try:
                return param.get_or_die(path, key)
            except NoMatchError:
                pass
        if self._is_abspath(path):
            try:
                return self._abs_path.get_or_die(path, key)
            except NoMatchError:
                pass
        return self._default_params.get(key, default)

    def objects(self, key, path=None):
        """
        Return the names of objects defined using a given key.

        :param key: The name of the key whose value lists the objects
                (e.g. 'nics').
        """
        return self.get(path, key, "").split()

    def iteritems(self):
        """
        Iterate through all available params and yield origin, key and value
        of each unique value.
        """
        env = []
        for param in self._rel_paths:
            for path, key, value in param.iteritems():
                if (path, key) not in env:
                    env.append((path, key))
                    yield (path, key, value)
        for path, key, value in self._abs_path.iteritems():
            if (path, key) not in env:
                env.append((path, key))
                yield (path, key, value)


class AvocadoParam(object):

    """
    This is a single slice params. It can contain multiple leaves and tries to
    find matching results.
    """

    def __init__(self, leaves, name):
        """
        :param leaves: this slice's leaves
        :param name: this slice's name (identifier used in exceptions)
        """
        # Basic initialization
        self._leaves = leaves
        # names cache (leaf.path is quite expensive)
        self._leaf_names = [leaf.path + '/' for leaf in leaves]
        self.name = name

    def __eq__(self, other):
        if self.__dict__ == other.__dict__:
            return True
        else:
            return False

    def __ne__(self, other):
        return not (self == other)

    @property
    def str_leaves_variant(self):
        """ String with identifier and all params """
        return "%s (%s)" % (self.name, self._leaf_names)

    def _get_leaves(self, path):
        """
        Get all leaves matching the path
        """
        return [self._leaves[i]
                for i in xrange(len(self._leaf_names))
                if path.search(self._leaf_names[i])]

    def get_or_die(self, path, key):
        """
        Get a value or raise exception if not present
        :raise NoMatchError: When no matches
        :raise KeyError: When value is not certain (multiple matches)
        """
        leaves = self._get_leaves(path)
        ret = [(leaf.environment[key], leaf.environment_origin[key])
               for leaf in leaves
               if key in leaf.environment]
        if not ret:
            raise NoMatchError("No matches to %s => %s in %s"
                               % (path.pattern, key, self.str_leaves_variant))
        if len(set([_[1] for _ in ret])) == 1:  # single source of results
            return ret[0][0]
        else:
            raise ValueError("Multiple %s leaves contain the key '%s'; %s"
                             % (path.pattern, key,
                                ["%s=>%s" % (_[1].path, _[0])
                                 for _ in ret]))

    def iteritems(self):
        """
        Very basic implementation which iterates through __ALL__ params,
        which generates lots of duplicate entries due to inherited values.
        """
        for leaf in self._leaves:
            for key, value in leaf.environment.iteritems():
                yield (leaf.environment_origin[key].path, key, value)


def _report_mux_already_parsed(self, *args, **kwargs):
    """
    Raises exception describing that `self.data` alteration is restricted
    """
    raise RuntimeError("Mux already parsed, altering is restricted. %s %s"
                       % (args, kwargs))


class Mux(object):

    """
    This is a multiplex object which multiplexes the test_suite.
    """

    def __init__(self, debug=False):
        """
        :param debug: Store whether this instance should debug the mux
        :note: people need to check whether mux uses debug and reflect that
               in order to provide the right results.
        """
        self._has_multiple_variants = None
        self.variants = None
        self.debug = debug
        self.data = tree.TreeNodeDebug() if debug else tree.TreeNode()
        self._mux_path = None

    def parse(self, args):
        """
        Apply options defined on the cmdline

        :param args: Parsed cmdline arguments
        """
        filter_only = getattr(args, 'filter_only', None)
        filter_out = getattr(args, 'filter_out', None)
        self._parse_basic_injects(args)
        mux_tree = tree.apply_filters(self.data, filter_only, filter_out)
        self.variants = MuxTree(mux_tree)
        self._mux_path = getattr(args, 'mux_path', None)
        if self._mux_path is None:
            self._mux_path = ['/run/*']
        # disable data alteration (and remove data as they are not useful)
        self.data = None
        self.data_inject = _report_mux_already_parsed
        self.data_merge = _report_mux_already_parsed

    def _parse_basic_injects(self, args):
        """
        Inject data from the basic injects defined by Mux

        :param args: Parsed cmdline arguments
        """
        # FIXME: Backward compatibility params, to be removed when 36 LTS is
        # discontinued
        if (not getattr(args, "mux_skip_defaults", False) and
                hasattr(args, "default_avocado_params")):
            self.data_merge(args.default_avocado_params)

        # Extend default multiplex tree of --mux-inject values
        for inject in getattr(args, "mux_inject", []):
            entry = inject.split(':', 3)
            if len(entry) < 2:
                raise ValueError("key:entry pairs required, found only %s"
                                 % (entry))
            elif len(entry) == 2:   # key, entry
                self.data_inject(*entry)
            else:                   # path, key, entry
                self.data_inject(key=entry[1], value=entry[2], path=entry[0])

    def is_parsed(self):
        """
        Reports whether the tree was already multiplexed
        """
        return self.variants is not None

    def data_inject(self, key, value, path=None):
        """
        Inject entry to the mux tree (params database)

        :param key: Key to which we'd like to assign the value
        :param value: The key's value
        :param path: Optional path to the node to which we assign the value,
                     by default '/'.
        """
        if path:
            node = self.data.get_node(path, True)
        else:
            node = self.data
        node.value[key] = value

    def data_merge(self, tree):
        """
        Merge tree into the mux tree (params database)

        :param tree: Tree to be merged into this database.
        :type tree: :class:`avocado.core.tree.TreeNode`
        """
        self.data.merge(tree)

    def get_number_of_tests(self, test_suite):
        """
        :return: overall number of tests * multiplex variants
        """
        # Currently number of tests is symmetrical
        if self.variants:
            no_variants = sum(1 for _ in self.variants)
            if no_variants > 1:
                self._has_multiple_variants = True
            return (len(test_suite) * no_variants)
        else:
            return len(test_suite)

    def itertests(self):
        """
        Yield variant-id and test params

        :yield (variant-id, (list of leaves, list of multiplex paths))
        """
        if self.variants:  # Copy template and modify it's params
            if self._has_multiple_variants:
                for i, variant in enumerate(self.variants, 1):
                    yield i, (variant, self._mux_path)
            else:
                yield None, (iter(self.variants).next(), self._mux_path)
        else:   # No variants, use template
            yield None, None
