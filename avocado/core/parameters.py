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
# Copyright: Red Hat Inc. 2014-2017

"""
Module related to test parameters
"""

import logging
import re


class NoMatchError(KeyError):
    pass


class AvocadoParams:

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
    """

    def __init__(self, leaves, paths, logger_name=None):
        """
        :param leaves: List of TreeNode leaves defining current variant
        :param paths: list of entry points
        :param logger_name: the name of a logger to use to record attempts
                            to get parameters
        :type logger_name: str
        """
        self._rel_paths = []
        leaves = list(leaves)
        for i, path in enumerate(paths):
            path_leaves = self._get_matching_leaves(path, leaves)
            self._rel_paths.append(AvocadoParam(path_leaves,
                                                f'{int(i)}: {path}'))
        # Don't use non-mux-path params for relative paths
        path_leaves = self._get_matching_leaves('/*', leaves)
        self._abs_path = AvocadoParam(path_leaves, '*: *')
        self._cache = {}     # TODO: Implement something more efficient
        self._logger_name = logger_name

    def __eq__(self, other):
        if set(self.__dict__) != set(other.__dict__):
            return False
        for attr in self.__dict__:
            if (getattr(self, attr) != getattr(other, attr)):
                return False
        return True

    def __ne__(self, other):
        return not (self == other)

    def __repr__(self):
        return f"<AvocadoParams {self._str()}>"

    def __str__(self):
        return f"params {self._str()}"

    def _str(self):
        out = ",".join(_.str_leaves_variant for _ in self._rel_paths)
        if out:
            return self._abs_path.str_leaves_variant + ',' + out
        else:
            return self._abs_path.str_leaves_variant

    def _get_matching_leaves(self, path, leaves):
        """
        Pops and returns list of matching nodes
        :param path: Path (str)
        :param leaves: list of TreeNode leaves
        """
        path_re = self._greedy_path_to_re(path)
        path_leaves = [leaf for leaf in leaves if path_re.search(leaf.path + '/')]
        for leaf in path_leaves:
            leaves.remove(leaf)
        return path_leaves

    @staticmethod
    def _greedy_path_to_re(path):
        """
        Converts user-friendly path with asterisk to a regex and compiles it

        :param path: a more natural, file-system-like/glob-like
                     expression for the paths
        :type path: builtin.str
        :returns: a compiled regex
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
            if self._logger_name is not None:
                logger = logging.getLogger(self._logger_name)
                logger.debug("PARAMS (key=%s, path=%s, default=%s) => %r",
                             key, path, default, value)
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
        path_re = self._greedy_path_to_re(path)
        for param in self._rel_paths:
            try:
                return param.get_or_die(path_re, key)
            except NoMatchError:
                pass
        if self._is_abspath(path_re):
            try:
                return self._abs_path.get_or_die(path_re, key)
            except NoMatchError:
                pass
        return default

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


class AvocadoParam:

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
        return f"{self.name} ({self._leaf_names})"

    def _get_leaves(self, path):
        """
        Get all leaves matching the path
        """
        return [self._leaves[i]
                for i in range(len(self._leaf_names))
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
            raise NoMatchError(f"No matches to {path.pattern} => "
                               f" {key} in {self.str_leaves_variant}")
        # make sure all params come from the same origin
        if len(set([_[1].path for _ in ret])) == 1:
            return ret[0][0]
        else:
            raise ValueError("Multiple %s leaves contain the key '%s'; %s"  # pylint: disable=C0209
                             % (path.pattern, key,
                                ["%s=>%s" % (_[1].path, _[0])  # pylint: disable=C0209
                                 for _ in ret]))

    def iteritems(self):
        """
        Very basic implementation which iterates through __ALL__ params,
        which generates lots of duplicate entries due to inherited values.
        """
        for leaf in self._leaves:
            for key, value in leaf.environment.items():
                yield (leaf.environment.origin[key].path, key, value)
