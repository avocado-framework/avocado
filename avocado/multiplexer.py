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
import logging
import re

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


def parse_yamls(input_yamls, filter_only=None, filter_out=None,
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
    return pools


def multiplex_pools(pools):
    return itertools.product(*pools)


def multiplex_yamls(input_yamls, filter_only=None, filter_out=None,
                    debug=False):
    pools = parse_yamls(input_yamls, filter_only, filter_out, debug)
    return multiplex_pools(pools)


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

    def __init__(self, leaves, test_id, tag, mux_entry, default_params):
        """
        :param leaves: List of TreeNode leaves defining current variant
        :param test_id: test id
        :param tag: test tag
        :param mux_entry: list of entry points
        :param default_params: dict of params used when no matches found
        """
        self._rel_paths = []
        leaves = list(leaves)
        for i, path in enumerate(mux_entry):
            path_leaves = self._get_matching_leaves(path, leaves)
            self._rel_paths.append(AvocadoParam(path_leaves,
                                                '%d: %s' % (i, path)))
        # Don't use non-mux-entry params for relative paths
        path_leaves = self._get_matching_leaves('/*', leaves)
        self._abs_path = AvocadoParam(path_leaves, '*: *')
        self.id = test_id
        self.tag = tag
        self._log = logging.getLogger("avocado.test").debug
        self._cache = {}     # TODO: Implement something more efficient
        # TODO: Get rid of this and prepare something better
        self._default_parmas = default_params

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
        self._log("PARAMS: %-20s | %-20s | %-10s => %r"
                  % (key, path, default, value))

    def _get_matching_leaves(self, path, leaves):
        """
        Pops and returns list of matching nodes
        :param path: Path (str)
        :param leaves: list of TreeNode leaves
        """
        path = self._greedy_path(path)
        path_leaves = [leaf for leaf in leaves if path.match(leaf.path + '/')]
        for leaf in path_leaves:
            leaves.remove(leaf)
        return path_leaves

    @staticmethod
    def _greedy_path(path):
        """
        converts user-friendly asterisk path to python regexp and compiles it:
        path = ""             => ^$ only
        path = "/"            => / only
        path = "/asdf/fdsa"   => /asdf/fdsa only
        path = "asdf/fdsa"    => $MUX_ENTRY/?.*/asdf/fdsa
        path = "/*/asdf"      => /[^/]*/asdf
        path = "asdf/*"       => $MUX_ENTRY/?.*/asdf/.*
        path = "/asdf/*"      => /asdf/.*
        """
        if not path:
            return re.compile('^$')
        if path[0] != '/':
            prefix = '.*/'
        else:
            prefix = ''
        if path[-1] == '*':
            suffix = ''
            path = path[:-1]
        else:
            suffix = '$'
        return re.compile(prefix + path.replace('*', '[^/]*') + suffix)

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

    def get(self, *args, **kwargs):
        """
        Retrieve params

        Old API: ``params.get(key, failobj=None)`` (any matching param)
        New API: ``params.get(key, path=$MUX_ENTRY/*, default=None)``

        As old and new API overlaps, you must use all 3 arguments or
        explicitely use key argument "path" or "default".
        """
        def compatibility(args, kwargs):
            """
            Be 100% compatible with old API while allow _SOME OF_ the new APIs
            calls:
            OLD: get(key), get(key, default), get(key, failobj=default)
            NEW: get(key, path, default), get(key, path=path),
                 get(key, default=default)

            :warning: We are unable to distinguish old get(key, default) vs.
                      new get(key, path), therefor if you want to use the new
                      API you must specify path/default using named arguments
                      or supply all 3 arguments:
                      get(key, path, default), get(key, path=path),
                      get(key, default=default).
                      This will be removed in final version.
            """
            if len(args) < 1:
                raise TypeError("Incorrect arguments: params.get(%s, %s)"
                                % (args, kwargs))
            elif 'failobj' in kwargs:
                return [args[0], '/*', kwargs['failobj']]   # Old API
            elif len(args) > 2 or 'default' in kwargs or 'path' in kwargs:
                try:
                    if 'default' in kwargs:
                        default = kwargs['default']
                    elif len(args) > 2:
                        default = args[2]
                    else:
                        default = None
                    if 'path' in kwargs:
                        path = kwargs['path']
                    elif len(args) > 1:
                        path = args[1]
                    else:
                        path = None
                    key = args[0]
                    return [key, path, default]
                except IndexError:
                    raise TypeError("Incorrect arguments: params.get(%s, %s)"
                                    % (args, kwargs))
            else:   # Old API
                if len(args) == 1:
                    return [args[0], '/*', None]
                else:
                    return [args[0], '/*', args[1]]

        key, path, default = compatibility(args, kwargs)
        if path is None:    # default path is any relative path
            path = '*'
        try:
            return self._cache[(key, path, default)]
        except KeyError:
            value = self._get(key, path, default)
            self.log(key, path, default, value)
            self._cache[(key, path, default)] = value
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
        return self._default_parmas.get(key, default)

    def objects(self, key, path=None):
        """
        Return the names of objects defined using a given key.

        :param key: The name of the key whose value lists the objects
                (e.g. 'nics').
        """
        return self.get(path, key, "").split()

    def iteritems(self):
        """
        Very basic implementation which iterates through __ALL__ params,
        which generates lots of duplicite entries due to inherited values.
        """
        for param in self._rel_paths:
            for pair in param.iteritems():
                self.log(pair[0], '/*', None, pair[1])
                yield pair
        for pair in self._abs_path.iteritems():
            yield pair


class AvocadoParam(object):

    """
    This is a single slice params. It can contain multiple leaves and tries to
    find matching results.
    Currently it doesn't care about params origin, it requires single result
    or failure. In future it'll get the origin from LeafParam and if it's the
    same it'll proceed, otherwise raise exception (as it can't decide which
    variable is desired)
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
                if path.match(self._leaf_names[i])]

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
        which generates lots of duplicite entries due to inherited values.
        """
        for leaf in self._leaves:
            for pair in leaf.environment.iteritems():
                yield pair


class Mux(object):

    """
    This is a multiplex object which multiplexes the test_suite.
    """

    def __init__(self, args):
        mux_files = getattr(args, 'multiplex_files', None)
        filter_only = getattr(args, 'filter_only', None)
        filter_out = getattr(args, 'filter_out', None)
        if mux_files:
            self.pools = parse_yamls(mux_files, filter_only, filter_out)
        else:   # no variants
            self.pools = None
        self._mux_entry = getattr(args, 'mux_entry', None)
        if self._mux_entry is None:
            self._mux_entry = ['/test/*']

    def get_number_of_tests(self, test_suite):
        """
        :return: overall number of tests * multiplex variants
        """
        # Currently number of tests is symetrical
        if self.pools:
            return (len(test_suite) *
                    sum(1 for _ in multiplex_pools(self.pools)))
        else:
            return len(test_suite)

    def itertests(self, template):
        """
        Processes the template and yields test definition with proper params
        """
        if self.pools:  # Copy template and modify it's params
            i = None
            for i, variant in enumerate(multiplex_pools(self.pools)):
                test_factory = [template[0], template[1].copy()]
                test_factory[1]['params'] = (variant, self._mux_entry)
                yield test_factory
            if i is None:   # No variants, use template
                yield template
        else:   # No variants, use template
            yield template
