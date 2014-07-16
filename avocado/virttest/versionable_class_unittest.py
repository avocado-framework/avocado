#!/usr/bin/python

import unittest
import cPickle
import sys

import common
from autotest.client.shared import utils
from autotest.client.shared.test_utils import mock
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


def system_version():
    return 2


class System(object):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "system_version" in kargs:
            ver = kargs['system_version']
        else:
            ver = system_version()
        if ver < 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(System, self).__init__()
        self.aa = self.__class__.__name__

    def __str__(self):
        return "VM1 %s" % self.aa


class System1(System):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "system_version" in kargs:
            ver = kargs['system_version']
        else:
            ver = system_version()
        if ver > 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(System1, self).__init__(*args, **kargs)
        self.aa = self.__class__.__name__

    def __str__(self):
        return "VM1 %s" % self.aa


class System_Container(VersionableClass):
    __master__ = System1

    def __new__(cls, *args, **kargs):
        return super(man[cls, System_Container], cls).__new__(cls, *args, **kargs)


class Q(object):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "q_version" in kargs:
            ver = kargs['q_version']
        else:
            ver = system_version()
        if ver < 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(Q, self).__init__()
        self.cls = self.__class__.__name__

    def __str__(self):
        return "%s" % self.cls


class Q1(Q):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "q_version" in kargs:
            ver = kargs['q_version']
        else:
            ver = system_version()
        if ver > 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(man[self.__class__, Q1], self).__init__(*args, **kargs)
        self.cls = self.__class__.__name__

    def __str__(self):
        return "%s" % self.cls


class Q_Container(VersionableClass):
    __master__ = Q1


class Sys(Q_Container):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "system_version" in kargs:
            ver = kargs['system_version']
        else:
            ver = system_version()
        if ver < 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(man[self.__class__, Sys], self).__init__(*args, **kargs)
        self.cls = self.__class__.__name__

    def __str__(self):
        return "%s" % self.cls


class Sys1(Sys):

    @classmethod
    def _is_right_ver(cls, *args, **kargs):
        ver = None
        if "system_version" in kargs:
            ver = kargs['system_version']
        else:
            ver = system_version()
        if ver > 1:
            return True
        else:
            return False

    def __init__(self, *args, **kargs):
        super(man[self.__class__, Sys1], self).__init__(*args, **kargs)
        self.cls = self.__class__.__name__

    def __str__(self):
        return "%s" % self.cls


class Sys_Container(VersionableClass):
    __master__ = Sys1

    def __new__(cls, *args, **kargs):
        return super(man[cls, Sys_Container], cls).__new__(cls, *args, **kargs)


class AA(Sys_Container, BB, System_Container):

    def __new__(cls, *args, **kargs):
        return super(man[cls, AA], cls).__new__(cls, *args, **kargs)


class TestVersionableClass(unittest.TestCase):

    def setUp(self):
        self.god = mock.mock_god(ut=self)
        self.god.stub_function(utils.logging, 'warn')
        self.god.stub_function(utils.logging, 'debug')
        self.version = 1

    def tearDown(self):
        self.god.unstub_all()

    def test_simple_versioning(self):
        self.god.stub_function(VM, "func1")
        self.god.stub_function(VM1, "func2")

        VM1.func2.expect_call()
        VM.func1.expect_call()

        mm = factory(BB)()
        # check class name.
        self.assertEqual(str(mm), "managed_BB_VM1")
        mm.func2()   # call BB.func2(m) -> VM1.func2
        mm.func1()   # call VM1.func1(m) -> VM.func1

        self.god.check_playback()

    def test_simple_create_by_params_v0(self):
        def wrap(mm):
            mm.VM1_cls

        self.god.stub_function(VM, "func3")
        self.god.stub_function(VM1, "func3")

        VM.func3.expect_call()

        mm = factory(BB, qemu_version=0)()
        # check class name.
        self.assertEqual(str(mm), "managed_BB_VM")
        mm.func3()   # call VM1.func1(m) -> VM.func1
        self.assertRaises(AttributeError, wrap, mm)

        self.god.check_playback()

    def test_simple_create_by_params_v1(self):
        self.god.stub_function(VM, "func3")
        self.god.stub_function(VM1, "func3")

        VM1.func3.expect_call()

        mm = factory(BB, qemu_version=2)()
        # check class name.
        self.assertEqual(str(mm), "managed_BB_VM1")
        mm.func3()   # call VM1.func1(m) -> VM.func1
        self.assertEqual(mm.VM1_cls, "VM1")

        self.god.check_playback()

    def test_sharing_data_in_same_version(self):
        mm = factory(BB)()
        bb = factory(BB)()
        cc = factory(BB, qemu_version=0)()

        # Get corespond class in versionable class
        man[bb.__class__, VM].test_class_vm1 = 1
        man[bb.__class__, BB].test_class_bb = 2
        man[cc.__class__, BB].test_class_bb = 3
        # check class name.
        self.assertEqual(bb.__class__.test_class_vm1,
                         mm.__class__.test_class_vm1)
        self.assertEqual(bb.__class__.test_class_bb,
                         mm.__class__.test_class_bb)

        # In class hierarchy is class which don't have to be versioned
        # because that first value should be equal and second one shouldn't.
        self.assertEqual(bb.__class__.test_class_vm1,
                         cc.__class__.test_class_vm1)
        self.assertNotEqual(bb.__class__.test_class_bb,
                            cc.__class__.test_class_bb)

    def test_complicated_versioning(self):
        self.god.stub_function(VM, "func3")
        self.god.stub_function(VM1, "func3")

        VM1.func3.expect_call()

        mm = factory(AA)()
        # check class name.
        self.assertEqual(str(mm), "managed_AA_Sys1_Q1_VM1_System1")
        mm.func3()   # call VM1.func1(m) -> VM.func1

        self.god.check_playback()

    def test_complicated_multiple_create_params(self):
        self.god.stub_function(VM, "func3")
        self.god.stub_function(VM1, "func3")

        VM1.func3.expect_call()

        mm = factory(AA, qemu_version=0, system_version=2, q_version=0)()
        # check class name.
        self.assertEqual(str(mm), "managed_AA_Sys1_Q_VM_System1")
        mm.func3()   # call VM1.func1(m) -> VM.func1

        self.god.check_playback()

    def test_pickleing(self):
        """
        Test pickling for example save vm env.
        """
        m = factory(AA, system_version=0, qemu_version=0)()
        mm = factory(BB, qemu_version=3)()

        f = open("/tmp/pick", "w+")
        cPickle.dump(m, f, cPickle.HIGHEST_PROTOCOL)
        cPickle.dump(mm, f, cPickle.HIGHEST_PROTOCOL)
        f.close()

        # Delete classes for ensure that pickel works correctly.
        name = m.__class__.__name__
        del m
        del globals()[name]

        name = mm.__class__.__name__
        del mm
        del globals()[name]

        f = open("/tmp/pick", "r+")
        c = cPickle.load(f)
        cc = cPickle.load(f)
        f.close()


if __name__ == "__main__":
    unittest.main()
