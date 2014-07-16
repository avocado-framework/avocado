import sys
import types


"""
Versioning system provides class hierarchy which automatically select the right
version of a class. Class and module manipulation is used for this reason.

By this reason is:
    Advantage) Only one class with some version is working in one process.
               It is possible use class variables. Others version of same
               class have different class variables. Supports pickling.
               Much cleaner debugging and faster running of code than
               using of __getattribute__.
    Disadvantage) It is necessary create class with
                        fatory(orig_class, params for is_right_ver)
               access to specific class through class Manager.


Example of usage (in versionable_class_unittest):


# SIMPLE EXAPMLE

from versionable_class import Manager, factory, VersionableClass
#register module to class manager. Necessary for pickling.
man = Manager(__name__)
# pylint: disable=E1003

class VM(object):
    @classmethod
    def _is_right_ver(cls, version):
        return version < 1

    def __init__(self, *args, **kargs):
        super(VM, self).__init__(*args, **kargs)

    def fn1(self):
        print "fn1_VM"



class VM1(VM):
    @classmethod
    def _is_right_ver(cls, version):
        return version >= 1

    def __init__(self, *args, **kargs):
        super(VM1, self).__init__(*args, **kargs)

    def fn1(self):
        print "fn1_VM1"

class VM_container(test_vers.VersionableClass):
    __master__ = VM1


o = test_vers.factory(VM_container, version=0) # return class.
o = o()    # create instance of class
p = test_vers.factory(VM_container, version=2)()
o.fn1()
p.fn1()


# ADVANCED EXAPMLE

from versionable_class import Manager, factory, VersionableClass
man = Manager(__name__)
# pylint: disable=E1003


def qemu_verison():
    return 2


class VM(object):
    __slot__ = ["cls"]

    test_class_vm1 = None

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "qemu_version" in kargs:
            ver = kargs['qemu_version']
        else:
            ver = qemu_verison()
        if ver < 1:
            return True
        else:
            return False


    def __new__(cls, *args, **kargs):
        return super(VM, cls).__new__(cls, *args, **kargs)


    def __init__(self, *args, **kargs):
        super(VM, self).__init__()
        self.cls = self.__class__.__name__


    def __str__(self):
        return "%s" % self.cls


    def func1(self):
        print "VM_func1"


    def func3(self):
        pass


class VM1(VM):
    __slot__ = ["VM1_cls"]
    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "qemu_version" in kargs:
            ver = kargs['qemu_version']
        else:
            ver = qemu_verison()
        if ver > 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(VM1, self).__init__(*args, **kargs)
        self.cls = self.__class__.__name__
        self.VM1_cls = "VM1"


    def __str__(self):
        return "%s" % self.cls


    def func1(self):
        super(VM1, self).func1()


    def func2(self):
        print "func2"


    def func3(self):
        pass


class VM_container(VersionableClass):
    __master__ = VM1

    def __new__(cls, *args, **kargs):
        return super(man[cls, VM_container], cls).__new__(cls, *args, **kargs)


class BB(VM_container):
    test_class_bb = None

    def __new__(cls, *args, **kargs):
        return super(man[cls, BB], cls).__new__(cls, *args, **kargs)


    def func1(self):
        super(man[self.__class__, BB], self).func1()


    def func2(self):
        super(man[self.__class__, BB], self).func2()
"""


def isclass(obj):
    """
    :param obj: Object for inspection if obj is class.
    :return: true if the object is a class.
    """
    return isinstance(obj, (type, types.ClassType))


class ModuleWrapper(object):

    """
    Wrapper around module.

    Necessary for pickling of dynamic class.
    """

    def __init__(self, wrapped):
        """
        :param wrapped: module for wrapping.
        :type wrapped: Module.
        """
        self.wrapped = wrapped

    def __dir__(self):
        return dir(self.wrapped)

    def __getattr__(self, name):
        """
        Override method `__getattr__` allows manipulate with modules.

        :param name: Name of specific object.
        :type name: string.
        :return: specific class when name of class starts with managed or
                 normal attribute from wrapped class.
        """
        if name not in self.wrapped.__dict__:
            if name.startswith("managed"):
                cls_name = name.split("_")
                cls = self.wrapped.__dict__[cls_name[1]]
                m_cls, _ = Manager(self.wrapped.__name__, self).factory(cls,
                                                                        _class_names=cls_name)
                return m_cls
        cls = getattr(self.wrapped, name)
        return cls


class VersionableClass(object):

    """
    Class used for marking of mutable class.
    """
    def __new__(cls, *args, **kargs):
        """
        If this method is invoked it means that something went wrong because
        this class should be replaced by :class:`Manager` factory.
        """
        raise Exception("Class %s is not prepared for usage. "
                        "You have to call versionable_class.factory(cls) "
                        "before you can use it" % (cls))


class Manager(object):

    def __init__(self, name, wrapper=None):
        """
        Manager for module.

        :param name: Name of module.
        :type name: string
        :param wrapper: Module dictionary wrapper. Should be None.
        """
        __import__(name)
        if not wrapper:
            if not isinstance(sys.modules[name], ModuleWrapper):
                self.wrapper = ModuleWrapper(sys.modules[name])
                sys.modules[name] = self.wrapper
            else:
                self.wrapper = sys.modules[name]
        else:
            self.wrapper = wrapper

    def factory(self, _class, *args, **kargs):
        """
        Create new class with right version of subclasses.

        Goes through class structure and search subclasses with right version.

        :param _class: Class which should be prepared.
        :type _class: class.
        :param args: Params for _is_right_ver function.
        :params kargs: Params for _is_right_ver function.
        """
        def add_to_structure(cl, new_bases):
            if VersionableClass in cl.__mro__:
                cls, cls_vn = self.factory(cl, *args, **kargs)
                new_bases.append(cls)
                return cls_vn
            else:
                new_bases.append(cl)
                return ""

        _class_names = None
        if "_class_names" in kargs:
            _class_names = kargs["_class_names"]
        if (_class.__name__.startswith("managed") and
                hasattr(_class, "__original_class__")):
            _class = _class.__original_class__
        new_bases = []
        cls_ver_name = ""
        if VersionableClass in _class.__bases__:  # parent is VersionableClass
            for m_cls in _class.__bases__:
                if m_cls is VersionableClass:
                    mro = _class.__master__.__mro__    # Find good version.
                    if _class_names:
                        for cl in mro[:-1]:
                            if cl.__name__ in _class_names:
                                cls_ver_name += "_" + cl.__name__
                                cls_ver_name += add_to_structure(cl, new_bases)
                                break
                    else:
                        for cl in mro[:-1]:
                            if cl._is_right_ver(*args, **kargs):
                                cls_ver_name += "_" + cl.__name__
                                cls_ver_name += add_to_structure(cl, new_bases)
                                break
                else:
                    cls_ver_name += add_to_structure(m_cls, new_bases)
        else:
            for m_cls in _class.__bases__:
                if (VersionableClass in m_cls.__mro__ or
                        hasattr(m_cls, "__original_class__")):
                    cls, cls_vn = self.factory(m_cls, *args, **kargs)
                    new_bases.append(cls)
                    cls_ver_name += cls_vn
                else:
                    new_bases.append(m_cls)
        class_name = "managed_%s%s" % (_class.__name__, cls_ver_name)

        if hasattr(self.wrapper.wrapped, class_name):
            # Don't override already created class.
            return self.wrapper.wrapped.__dict__[class_name], cls_ver_name

        class_dict = _class.__dict__.copy()
        class_dict["__original_class__"] = _class
        cls = type(class_name, tuple(new_bases), class_dict)
        self.wrapper.wrapped.__dict__[class_name] = cls

        return cls, cls_ver_name

    def __getitem__(self, o_cls):
        return self.getcls(*o_cls)

    def getcls(self, cls, orig_class):
        """
        Return class correspond class and original class.

        :param cls: class for which should be found derived alternative.
        :type cls: class
        :param orig_class: Original class
        :type orig_class: class

        :return: Derived alternative class
        :rtype: class
        """
        for m_cls in cls.__mro__:
            if hasattr(m_cls, "__original_class__"):
                if m_cls.__original_class__ is orig_class:
                    return m_cls
            elif m_cls is orig_class:
                return m_cls
        raise Exception("Couldn't find derived alternative in %s for"
                        " class %s" % (cls, orig_class))


def factory(orig_cls, *args, **kargs):
    """
    Create class with specific version.

    :param orig_class: Class from which should be derived good version.
    :param args: list of parameters for _ir_right_ver
    :params kargs: dict of named parameters for _ir_right_ver
    :return: params specific class.
    :rtype: class
    """
    return Manager(orig_cls.__module__).factory(orig_cls, *args, **kargs)[0]
