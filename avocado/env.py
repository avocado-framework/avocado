"""
Defines the Env class, a representation of relevant test objects that can be
pickled and unpickled between instances. It is used to persist state that would
be otherwise costly to reconstruct.

An example would be long lived processes that we want to preserve from
test A to test B, say, QEMU instances that have virtual machines that would
take too long to boot to be restarted every test.
"""

import cPickle
import UserDict
import os
import logging
import threading

ENV_VERSION = 1

log = logging.getLogger("avocado.test")


def get_env_version():
    return ENV_VERSION


class EnvSaveError(Exception):
    pass


def lock_safe(function):
    """
    Get the environment safe lock, run the function, then release the lock.

    Unfortunately, it only works if the 1st argument of the function is an
    Env instance. This is mostly to save up code.

    :param function: Function to wrap.
    """
    def wrapper(*args, **kwargs):
        env = args[0]
        env.save_lock.acquire()
        try:
            return function(*args, **kwargs)
        finally:
            env.save_lock.release()
    wrapper.__name__ = function.__name__
    wrapper.__doc__ = function.__doc__
    wrapper.__dict__.update(function.__dict__)
    return wrapper


class Env(UserDict.IterableUserDict):

    """
    A dict-like object containing global objects used by tests.
    """

    def __init__(self, filename=None, version=0):
        """
        Create an empty Env object or load an existing one from a file.

        If the version recorded in the file is lower than version, or if some
        error occurs during unpickling, or if filename is not supplied,
        create an empty Env object.

        :param filename: Path to an env file.
        :param version: Required env version (int).
        """
        UserDict.IterableUserDict.__init__(self)
        empty = {"version": version}
        self._filename = filename
        self._params = None
        self.save_lock = threading.RLock()
        if filename:
            try:
                if os.path.isfile(filename):
                    f = open(filename, "r")
                    env = cPickle.load(f)
                    f.close()
                    if env.get("version", 0) >= version:
                        self.data = env
                    else:
                        log.warn(
                            "Incompatible env file found. Not using it.")
                        self.data = empty
                else:
                    # No previous env file found, proceed...
                    log.warn("Creating new, empty env file")
                    self.data = empty
            # Almost any exception can be raised during unpickling, so let's
            # catch them all
            except Exception, e:
                log.warn("Exception thrown while loading env")
                log.warn(e)
                log.warn("Creating new, empty env file")
                self.data = empty
        else:
            log.warn("Creating new, empty env file")
            self.data = empty

    def save(self, filename=None):
        """
        Pickle the contents of the Env object into a file.

        :param filename: Filename to pickle the dict into.  If not supplied,
                use the filename from which the dict was loaded.
        """
        filename = filename or self._filename
        if filename is None:
            raise EnvSaveError("No filename specified for this env file")
        self.save_lock.acquire()
        try:
            f = open(filename, "w")
            cPickle.dump(self.data, f)
            f.close()
        finally:
            self.save_lock.release()

    def get_object(self, obj_type, name):
        try:
            return self.data["%s__%s" % (obj_type, name)]
        except KeyError:
            return None

    def get_all_objects(self, obj_type):
        """
        Return a list of all objects with prefix obj_type in this Env object.
        """
        obj_list = []
        for key in self.data.keys():
            if key and key.startswith("%s__" % obj_type):
                obj_list.append(self.data[key])
        return obj_list

    def clean_objects(self):
        """
        Destroy all objects registered in this Env object.
        """
        for key in self.data.keys():
            obj = self.data[key]
            if hasattr(obj, 'destroy'):
                try:
                    obj.destroy()
                except:
                    pass
        self.data = {}

    def destroy(self):
        """
        Destroy all objects stored in Env and remove the backing file.
        """
        self.clean_objects()
        if self._filename is not None:
            if os.path.isfile(self._filename):
                os.unlink(self._filename)

    @lock_safe
    def register_object(self, obj_type, name, obj):
        """
        Register an object in this Env object.

        :param obj_type: Object type.
        :param name: Object name.
        :param obj: Object.
        """
        self.data["%s__%s" % (obj_type, name)] = obj

    @lock_safe
    def unregister_object(self, obj_type, name):
        """
        Remove a given object.

        :param name: Object name.
        """
        del self.data["%s__%s" % (obj_type, name)]
