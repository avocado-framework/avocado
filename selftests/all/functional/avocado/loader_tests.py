import os
import sys
import unittest

# simple magic for using scripts within a source tree
basedir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..')
basedir = os.path.abspath(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado.utils import script
from avocado.utils import process

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
    print('Hello World!')
"""

PY_SIMPLE_TEST = """#!/usr/bin/python
def hello():
    print('Hello World!')

if __name__ == "__main__":
    hello()
"""

SIMPLE_TEST = """#!/bin/sh
true
"""


class LoaderTestFunctional(unittest.TestCase):

    def test_simple(self):
        os.chdir(basedir)
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest')
        simple_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % simple_test.path
        process.run(cmd_line)
        simple_test.remove()

    def test_simple_not_exec(self):
        os.chdir(basedir)
        simple_test = script.TemporaryScript('simpletest.sh', SIMPLE_TEST,
                                             'avocado_loader_unittest',
                                             mode=0664)
        simple_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % simple_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('NOT_A_TEST', result.stdout)
        simple_test.remove()

    def test_pass(self):
        avocado_pass_test = script.TemporaryScript('passtest.py',
                                                   AVOCADO_TEST_OK,
                                                   'avocado_loader_unittest')
        avocado_pass_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % avocado_pass_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 0
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_buggy_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py',
                                                    AVOCADO_TEST_BUGGY,
                                                    'avocado_loader_unittest')
        avocado_buggy_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % avocado_buggy_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))

    def test_buggy_not_exec(self):
        avocado_buggy_test = script.TemporaryScript('buggytest.py',
                                                    AVOCADO_TEST_BUGGY,
                                                    'avocado_loader_unittest',
                                                    mode=0664)
        avocado_buggy_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % avocado_buggy_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        avocado_buggy_test.remove()

    def test_load_not_a_test(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST,
                                                    'avocado_loader_unittest')
        avocado_not_a_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % avocado_not_a_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        avocado_not_a_test.remove()

    def test_load_not_a_test_not_exec(self):
        avocado_not_a_test = script.TemporaryScript('notatest.py', NOT_A_TEST,
                                                    'avocado_loader_unittest',
                                                    mode=0664)
        avocado_not_a_test.save()
        cmd_line = './scripts/avocado run --disable-sysinfo %s' % avocado_not_a_test.path
        result = process.run(cmd_line, ignore_status=True)
        expected_rc = 1
        self.assertEqual(result.exit_status, expected_rc,
                         "Avocado did not return rc %d:\n%s" %
                         (expected_rc, result))
        self.assertIn('NOT_A_TEST', result.stdout)
        avocado_not_a_test.remove()

if __name__ == '__main__':
    unittest.main()
