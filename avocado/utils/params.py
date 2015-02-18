import UserDict
from threading import Lock

from avocado.core import exceptions
from avocado import settings


class ParamNotFound(exceptions.TestError):
    pass


class ParamInvalidType(exceptions.TestError):
    pass


class Params(UserDict.IterableUserDict):

    """
    A dict-like object passed to every test.
    """
    lock = Lock()

    def __getitem__(self, key):
        """ overrides the error messages of missing params[$key] """
        try:
            value = UserDict.IterableUserDict.__getitem__(self, key)
            vtype = UserDict.IterableUserDict.get(self, "%s_type" % key)
            if vtype is not None:
                return settings.convert_value_type(value, vtype)
            else:
                return value
        except KeyError:
            raise ParamNotFound("Mandatory parameter '%s' is missing. "
                                "Check your cfg files for typos/mistakes" %
                                key)
        except Exception, details:
            raise ParamInvalidType("Parameter '%s' value '%r' failed to "
                                   "convert to %s: %s" %
                                   (key, value, vtype, details))

    def __getattr__(self, attr):
        try:
            return UserDict.IterableUserDict.__getattr__(self, attr)  # @UndefinedVariable
        except AttributeError:
            try:
                return self.__getitem__(attr)
            except ParamNotFound:
                return None

    def copy(self):
        new_dict = {}
        for key in self:
            new_dict[key] = self[key]
        return Params(new_dict)

    def objects(self, key):
        """
        Return the names of objects defined using a given key.

        :param key: The name of the key whose value lists the objects
                (e.g. 'nics').
        """
        return self.get(key, "").split()

    def object_params(self, obj_name):
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
        self.lock.acquire()
        new_dict = self.data.copy()
        self.lock.release()
        for key in new_dict.keys():
            if key.endswith(suffix):
                new_key = key.split(suffix)[0]
                new_dict[new_key] = new_dict[key]
        return new_dict

    def object_counts(self, count_key, base_name):
        """
        This is a generator method: to give it the name of a count key and a
        base_name, and it returns an iterator over all the values from params
        """
        count = self.get(count_key, 1)
        # Protect in case original is modified for some reason
        cpy = self.copy()
        for number in xrange(1, int(count) + 1):
            key = "%s%s" % (base_name, number)
            yield (key, cpy.get(key))
