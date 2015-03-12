import re
from threading import Lock


class NoMatchError(KeyError):
    pass


class LeafParams(object):

    """
    This class wraps the leaf and acts as it's values. In the future it should
    also report the origin so the underlying params can detect clashes.
    In the future we might consider merging these features into the TreeNode
    or alternatively moving these functions here and removeing them from
    TreeNode.
    """

    # TODO: Instead of environment use values and descend up until we reach
    #       the value. Return also the origin to allow comparism of possible
    #       clashes.

    def __init__(self, leaf):
        self.name = leaf.path + '/'     # we need the names to be ended with /
        self.leaf = leaf

    def __contains__(self, key):
        return key in self.leaf.environment

    def __getitem__(self, key):
        return self.leaf.environment[key]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


class AvocadoParams(object):

    """
    Main params object. It uses Test.get_resolution_order() to slice the
    provided list of leaves. Currently only first matching path contain the
    leaf although it's written to support booth ways.

    It supports quering for params of given path and key and copies the
    "objects", "object_params" and "object_counts" methods (not tested).

    Unsafely it also supports pickling, although to work properly params would
    have to be deepcopied.
    """

    # TODO: Use "test" to log params.get()

    def __init__(self, leaves, test_id, tag, mux_entry):
        self.lock = Lock()
        self._rel_paths = []
        leaves = list(leaves)
        for i, path in enumerate(mux_entry):
            path_leaves = self._get_params_from_leaves(path, leaves)
            self._rel_paths.append(AvocadoParam(path_leaves,
                                                '%d: %s' % (i, path)))
        # Don't use non-mux-entry params for relative paths
        path_leaves = self._get_params_from_leaves('/*', leaves)
        self._abs_path = AvocadoParam(path_leaves, '*: *')
        self.id = test_id
        self.tag = tag

    def __getstate__(self):
        copy = self.__dict__.copy()
        del(copy['lock'])
        return copy

    def __setstate__(self, orig):
        self.__dict__.update(orig)
        self.lock = Lock()

    def __str__(self):
        return "params {%s}" % ", ".join(_.name for _ in self._rel_paths)

    def _get_params_from_leaves(self, path, leaves):
        path_leaves = []
        path = self._greedy_path(path)
        for leaf in [leaf for leaf in leaves if path.match(leaf.path + '/')]:
            # FIXME: This means used leaves are not reused. Is this expected
            # behavior? If not remove the following line and as the matching
            # paths are unique and ordered match in self.get() for first path
            # match and get the value from there only (instead of get_or_die)
            leaves.remove(leaf)
            # FIXME: Do we want to keep absolute paths or should they be
            # converted to relative paths to `path` instead?
            path_leaves.append(LeafParams(leaf))
        return path_leaves

    @staticmethod
    def _greedy_path(path):
        """
        path = ""             => ^$ only
        path = "/"            => / only
        path = "/asdf/fdsa"   => /asdf/fdsa only
        path = "asdf/fdsa"    => .*/asdf/fdsa
        path = "/*/asdf"      => /[^/]*/asdf
        path = "asdf/*"       => .*/asdf/.*
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
        if path.pattern and path.pattern[0] == '/':
            return True
        else:
            return False

    def get(self, path, key, default=None):
        """
        Get a value according to test's resolution order.
        :param path: namespace
        :param key: key you're looking for
        :param default: default value when not found
        """
        # TODO: Add caching here
        path = self._greedy_path(path)
        for param in self._rel_paths:
            # TODO: Spedup: Check if the variant can match the path
            try:
                return param.get_or_die(path, key)
            except NoMatchError:
                pass
        if self._is_abspath(path):
            try:
                return self._abs_path.get_or_die(path, key)
            except NoMatchError:
                pass
        return default

    def _get_leaf(self, path):
        path = self._greedy_path(path)
        for param in self._rel_paths:
            try:
                return param.get_leaf(path)
            except NoMatchError:
                pass
        raise NoMatchError('No leaves matchng "%s" pattern found in %s'
                           % (path.pattern, self))

    def objects(self, key, path=None):
        """
        Return the names of objects defined using a given key.

        :param key: The name of the key whose value lists the objects
                (e.g. 'nics').
        """
        return self.get(path, key, "").split()

    def object_params(self, obj_name, path=None):
        """
        Return a dict-like object containing the parameters of an individual
        object.

        This method behaves as follows: the suffix '_' + obj_name is removed
        from all key names that have it.  Other key names are left unchanged.
        The values of keys with the suffix overwrite the values of their
        suffix-less versions.

        :param obj_name: The name of the object (objects are listed by the
                objects() method).
        """
        suffix = "_" + obj_name
        leaf = self._get_leaf(path)
        self.lock.acquire()
        new_dict = leaf.copy()
        self.lock.release()
        for key in new_dict.keys():
            if key.endswith(suffix):
                new_key = key.split(suffix)[0]
                new_dict[new_key] = new_dict[key]
        return new_dict

    def object_counts(self, count_key, base_name, path=None):
        """
        This is a generator method: to give it the name of a count key and a
        base_name, and it returns an iterator over all the values from params
        """
        count = self.get(count_key, 1)
        # Protect in case original is modified for some reason
        cpy = self._get_leaf(path).copy()
        for number in xrange(1, int(count) + 1):
            key = "%s%s" % (base_name, number)
            yield (key, cpy.get(key))


class AvocadoParam(object):

    """
    This is a single slice params. It can contain multiple leaves and tries to
    find matching results.
    Currently it doesn't care about params origin, it requires single result
    or failure. In future it'll get the origin from LeafParam and if it's the
    same it'll proceed.
    """

    def __init__(self, leaves, name):
        # Basic initialization
        self._leaves = leaves
        self.name = name

    @property
    def _str_leaves_variant(self):
        leaves = [_.name for _ in self._leaves]
        return "%s (%s)" % (self.name, leaves)

    def _get_leaves(self, path):
        return [leaf for leaf in self._leaves if path.match(leaf.name)]

    def get_leaf(self, path):
        leaves = self._get_leaves(path)
        if len(leaves) == 1:
            return leaves[0]
        elif len(leaves) == 0:
            raise NoMatchError('No leaves matchng "%s" pattern found in %s'
                               % (path.pattern, self._str_leaves_variant))
        else:
            raise KeyError('Multiple leaves matching "%s" found: %s'
                           % (path.pattern, self._str_leaves_variant))

    def get(self, path, key, default=None):
        """
        Returns value of key from $path path. Multiple matching path are
        acceptable when only one of them contains the key.
        """
        try:
            self.get_or_die(path, key)
        except NoMatchError:
            return default

    def get_or_die(self, path, key):
        """
        Get a value or raise exception if not present
        :raise NoMatchError: When no matches
        :raise KeyError: When value is not certain (multiple matches)
        """
        leaves = self._get_leaves(path)
        ret = [leaf[key] for leaf in leaves if key in leaf]
        if len(ret) == 1:
            return ret[0]
        elif not ret:
            raise NoMatchError("No matches to %s =>%s in %s"
                               % (path, key, self._str_leaves_variant))
        else:
            raise ValueError("Multiple %s leaves contain the key %s; %s"
                             % (path, key,
                                ["%s=>%s" % (leaf.name, leaf[key])
                                 for leaf in leaves if key in leaf]))
