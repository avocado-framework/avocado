import os
import shutil
import sys
import tempfile

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import test
from avocado.utils import script

PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""


class TestClassTest(unittest.TestCase):

    def setUp(self):
        class AvocadoPass(test.Test):

            def runTest(self):
                variable = True
                self.assertTrue(variable)
                self.whiteboard = 'foo'

        class EmptyTest(test.Test):

            """
            I don't have runTest() defined!
            """
            pass

        self.base_logdir = tempfile.mkdtemp(prefix='avocado_test_unittest')
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir)
        self.tst_instance_pass.run_avocado()
        self.tst_instance_pass_new = AvocadoPass(base_logdir=self.base_logdir)
        self.tst_instance_pass_new.run_avocado()
        self.tst_instance_empty = EmptyTest(base_logdir=self.base_logdir)
        self.tst_instance_empty.run_avocado()

    def testRunTest(self):
        self.assertEqual(self.tst_instance_empty.runTest(), None)

    def testRunAvocado(self):
        self.assertEqual(self.tst_instance_empty.status, 'PASS')

    def testClassAttributesName(self):
        self.assertEqual(self.tst_instance_pass.name, 'AvocadoPass')

    def testClassAttributesStatus(self):
        self.assertEqual(self.tst_instance_pass.status, 'PASS')

    def testClassAttributesTimeElapsed(self):
        self.assertIsInstance(self.tst_instance_pass.time_elapsed, float)

    def testClassAttributesTag(self):
        self.assertEqual(self.tst_instance_pass.tag, "0")

    def testClassAttributesTaggedName(self):
        self.assertEqual(self.tst_instance_pass.tagged_name, "AvocadoPass")

    def testWhiteboardSave(self):
        whiteboard_file = os.path.join(
            self.tst_instance_pass.logdir, 'whiteboard')
        self.assertTrue(os.path.isfile(whiteboard_file))
        with open(whiteboard_file, 'r') as whiteboard_file_obj:
            whiteboard_contents = whiteboard_file_obj.read().strip()
            self.assertTrue(whiteboard_contents, 'foo')

    def testTaggedNameNewTests(self):
        """
        New test instances should have crescent tag instances.
        """
        self.assertEqual(
            self.tst_instance_pass_new.tagged_name, "AvocadoPass.1")
        self.assertEqual(self.tst_instance_pass_new.tag, "1")

    def tearDown(self):
        shutil.rmtree(self.base_logdir)


class SimpleTestClassTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.pass_script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.pass_script.save()

        self.fail_script = script.TemporaryScript(
            'avocado_fail.sh',
            FAIL_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.fail_script.save()

        self.tst_instance_pass = test.SimpleTest(
            path=self.pass_script.path,
            base_logdir=self.tmpdir)
        self.tst_instance_pass.run_avocado()

        self.tst_instance_fail = test.SimpleTest(
            path=self.fail_script.path,
            base_logdir=self.tmpdir)
        self.tst_instance_fail.run_avocado()

    def testSimpleTestPassStatus(self):
        self.assertEqual(self.tst_instance_pass.status, 'PASS')

    def testSimpleTestFailStatus(self):
        self.assertEqual(self.tst_instance_fail.status, 'FAIL')

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()
        shutil.rmtree(self.tmpdir)

if __name__ == '__main__':
    unittest.main()
