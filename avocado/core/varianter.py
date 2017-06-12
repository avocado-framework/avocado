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

import re

from . import tree
from . import dispatcher
from .output import LOG_JOB


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

    In this version each new "get()" call is logged into avocado.LOG_JOB.
    This is subject of change (separate file, perhaps)
    """

    # TODO: Use "test" to log params.get()

    def __init__(self, leaves, test_id, mux_path, default_params):
        """
        :param leaves: List of TreeNode leaves defining current variant
        :param test_id: test id
        :param mux_path: list of entry points
        :param default_params: dict of params used when no matches found

        .. note:: `default_params` will be deprecated by the end of 2017.
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
        return copy

    def __setstate__(self, orig):
        """ refresh log """
        self.__dict__.update(orig)

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
        LOG_JOB.debug("PARAMS (key=%s, path=%s, default=%s) => %r", key, path,
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
            LOG_JOB.warn(msg)
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
        ret = [(leaf.environment[key], leaf.environment.origin[key])
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
                yield (leaf.environment.origin[key].path, key, value)


class FakeVariantDispatcher(object):

    """
    This object can act instead of VarianterDispatcher to report loaded
    variants.
    """

    def __init__(self, state):
        for variant in state:
            variant["variant"] = [tree.TreeNodeEnvOnly(path, env)
                                  for path, env in variant["variant"]]
        self.variants = state

    def map_method(self, method, *args, **kwargs):
        """
        Reports list containing one result of map_method on self
        """
        if hasattr(self, method):
            return [getattr(self, method)(*args, **kwargs)]
        else:
            return []

    def __iter__(self):
        return iter(self.variants)

    def __len__(self):
        return sum(1 for _ in self)


class Varianter(object):

    """
    This object takes care of producing test variants
    """

    def __init__(self, debug=False, state=None):
        """
        :param debug: Store whether this instance should debug the mux
        :param state: Force-varianter state
        :note: people need to check whether mux uses debug and reflect that
               in order to provide the right results.
        """
        self.default_params = {}
        self._default_params = None
        if state is None:
            self.debug = debug
            self.node_class = tree.TreeNodeDebug if debug else tree.TreeNode
            self._variant_plugins = dispatcher.VarianterDispatcher()
            self._no_variants = None
        else:
            self.load(state)

    def parse(self, args):
        """
        Apply options defined on the cmdline and initialize the plugins.

        :param args: Parsed cmdline arguments
        """
        defaults = self._process_default_params(args)
        self._variant_plugins.map_method_copy("initialize", args)
        self._variant_plugins.map_method_copy("update_defaults", defaults)
        self._no_variants = sum(self._variant_plugins.map_method("__len__"))

    def _process_default_params(self, args):
        """
        Process the default params

        :param args: Parsed cmdline arguments
        """
        default_params = self.node_class()
        for default_param in self.default_params.itervalues():
            default_params.merge(default_param)
        self._default_params = default_params
        self.default_params.clear()     # We don't need these anymore
        # FIXME: Backward compatibility params, to be removed when 36 LTS is
        # discontinued
        if (not getattr(args, "variants_skip_defaults", False) and
                hasattr(args, "default_avocado_params")):
            self._default_params.merge(args.default_avocado_params)
        return self._default_params

    def is_parsed(self):
        """
        Reports whether the varianter was already parsed
        """
        return self._no_variants is not None

    def add_default_param(self, name, key, value, path=None):   # pylint: disable=E0202
        """
        Stores the path/key/value into default params

        This allow injecting default arguments which are mainly intended for
        machine/os-related params. It should not affect the test results
        and by definition it should not affect the variant id.

        :param name: Name of the component which injects this param
        :param key: Key to which we'd like to assign the value
        :param value: The key's value
        :param path: Optional path to the node to which we assign the value,
                     by default '/'.
        """
        if path is None:
            path = "/"
        if name not in self.default_params:
            self.default_params[name] = self.node_class()
        self.default_params[name].get_node(path, True).value[key] = value

    def to_str(self, summary=0, variants=0, **kwargs):
        """
        Return human readable representation

        The summary/variants accepts verbosity where 0 means do not display
        at all and maximum is up to the plugin.

        :param summary: How verbose summary to output (int)
        :param variants: How verbose list of variants to output (int)
        :param kwargs: Other free-form arguments
        :rtype: str
        """
        return "\n\n".join(self._variant_plugins.map_method("to_str", summary,
                                                            variants,
                                                            **kwargs))

    def get_number_of_tests(self, test_suite):
        """
        :return: overall number of tests * number of variants
        """
        # Currently number of tests is symmetrical
        if self._no_variants:
            return len(test_suite) * self._no_variants
        else:
            return len(test_suite)

    def dump(self):
        """
        Dump the variants in loadable-state

        This is lossy representation which takes all yielded variants and
        replaces the list of nodes with TreeNodeEnvOnly representations::

            [{'mux_path': mux_path,
              'variant_id': variant_id,
              'variant': dump_tree_nodes(original_variant)},
             {'mux_path': [str, str, ...],
              'variant_id': str,
              'variant': [(str, [(str, str, object), ...])],
             {'mux_path': ['/run/*'],
              'variant_id': 'cat-26c0'
              'variant': [('/pig/cat',
                           [('/pig', 'ant', 'fox'),
                            ('/pig/cat', 'dog', 'bee')])]}
             ...]

        where `dump_tree_nodes` looks like::

            [(node.path, environment_representation),
             (node.path, [(path1, key1, value1), (path2, key2, value2), ...]),
             ('/pig/cat', [('/pig', 'ant', 'fox')])

        :return: loadable Varianter representation
        """
        def dump_tree_node(node):
            """
            Turns TreeNode-like object into tuple(path, env_representation)
            """
            return (str(node.path),
                    [(str(node.environment.origin[key].path), str(key), value)
                     for key, value in node.environment.iteritems()])

        if not self.is_parsed():
            raise NotImplementedError("Dumping Varianter state before "
                                      "multiplexation is not supported.")
        variants = []
        for variant in self.itertests():
            safe_variant = {}
            safe_variant["mux_path"] = [str(pth)
                                        for pth in variant.get("mux_path")]
            safe_variant["variant_id"] = str(variant.get("variant_id"))
            safe_variant["variant"] = [dump_tree_node(_)
                                       for _ in variant.get("variant", [])]
            variants.append(safe_variant)

        return variants

    def load(self, state):
        """
        Load the variants state

        Current implementation supports loading from a list of loadable
        variants. It replaces the VariantDispatcher with fake implementation
        which reports the loaded (and initialized) variants.

        :param state: loadable Varianter representation
        """
        self.debug = False
        self.node_class = tree.TreeNode
        self._variant_plugins = FakeVariantDispatcher(state)
        self._no_variants = sum(self._variant_plugins.map_method("__len__"))

    def itertests(self):
        """
        Yields all variants of all plugins

        The variant is defined as dictionary with at least:
         * variant_id - name of the current variant
         * variant - AvocadoParams-compatible variant (usually a list of
                     TreeNodes but dict or simply None are also possible
                     values)
         * mux_path - default path(s)

        :yield variant
        """
        if self._no_variants:  # Copy template and modify it's params
            plugins_variants = self._variant_plugins.map_method("__iter__")
            iter_variants = (variant
                             for plugin_variants in plugins_variants
                             for variant in plugin_variants)
            for variant in iter(iter_variants):
                yield variant
        else:   # No variants, use template
            yield {"variant": self._default_params.get_leaves(),
                   "variant_id": None,
                   "mux_path": "/run"}
