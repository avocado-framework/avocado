#!/usr/bin/env python

import os
import sys
import unittest
import multiprocessing

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.core import exceptions
from avocado.utils import script
from avocado import loader
from avocado import test

AVOCADO_TEST_OK = """#!/usr/bin/python
from avocado import job
from avocado import test

class PassTest(test.Test):
    def action(self):
        pass

if __name__ == "__main__":
    job.main()
"""

AVOCADO_TEST_BUGGY = """#!/usr/bin/python
from avocado import job
from avocado import test
import adsh

class PassTest(test.Test):
    def action(self):
        pass

if __name__ == "__main__":
    job.main()
"""

NOT_A_TEST = """
def hello():
    print 'Hello World!'
"""

PY_SIMPLE_TEST = """#!/usr/bin/python
def hello():
    print 'Hello World!'

if __name__ == "__main__":
    hello()
"""

SIMPLE_TEST = """#!/bin/sh
true
"""


class _DebugJob(object):
    logdir = '.'


class WrapperTest(unittest.TestCase):

    def setUp(self):
        self.loader = loader.TestLoader(job=_DebugJob)
        self.queue = multiprocessing.Queue()

    def test_load_simple(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST, 'avocado_loader_unittest')
        simple_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': simple_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        tc.action()
        simple_test.remove()

    def test_load_simple_not_exec(self):
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST, 'avocado_loader_unittest', mode=0664)
        simple_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': simple_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.action)
        simple_test.remove()

    def test_load_pass(self):
        avocado_pass_test = script.TemporaryScript('passtest.py', AVOCADO_TEST_OK, 'avocado_loader_unittest')
        avocado_pass_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_pass_test.path},
                                                                queue=self.queue)
        self.assertTrue(str(test_class) == "<class 'passtest.PassTest'>", str(test_class))
        self.assertTrue(issubclass(test_class, test.Test))
        tc = test_class(**test_parameters)
        tc.action()
        avocado_pass_test.remove()

    def test_load_buggy_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py', AVOCADO_TEST_BUGGY, 'avocado_loader_unittest')
        avocado_buggy_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_buggy_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.TestFail, tc.action)
        avocado_buggy_test.remove()

    def test_load_buggy_not_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py', AVOCADO_TEST_BUGGY, 'avocado_loader_unittest',
                                                    mode=0664)
        avocado_buggy_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_buggy_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.BuggyTest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(ImportError, tc.action)
        avocado_buggy_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST, 'avocado_loader_unittest', mode=0664)
        avocado_not_a_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_not_a_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.NotATest, test_class)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.action)
        avocado_not_a_test.remove()

    def test_load_not_a_test_exec(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST, 'avocado_loader_unittest')
        avocado_not_a_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_not_a_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.SimpleTest, test_class)
        tc = test_class(**test_parameters)
        # The test can't be executed (no shebang), raising an OSError (OSError: [Errno 8] Exec format error)
        self.assertRaises(OSError, tc.action)
        avocado_not_a_test.remove()

    def test_py_simple_test(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py', PY_SIMPLE_TEST, 'avocado_loader_unittest')
        avocado_simple_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_simple_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.SimpleTest)
        tc = test_class(**test_parameters)
        tc.action()
        avocado_simple_test.remove()

    def test_py_simple_test_notexec(self):
        avocado_simple_test = script.TemporaryScript('simpletest.py', PY_SIMPLE_TEST, 'avocado_loader_unittest',
                                                     mode=0664)
        avocado_simple_test.save()
        test_class, test_parameters = self.loader.discover_test(params={'id': avocado_simple_test.path},
                                                                queue=self.queue)
        self.assertTrue(test_class == test.NotATest)
        tc = test_class(**test_parameters)
        self.assertRaises(exceptions.NotATestError, tc.action)
        avocado_simple_test.remove()

if __name__ == '__main__':
    unittest.main()
