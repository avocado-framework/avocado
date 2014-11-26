#!/usr/bin/env python

import unittest
import os
import shutil
import sys
import tempfile

# simple magic for using scripts within a source tree
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
basedir = os.path.dirname(basedir)
if os.path.isdir(os.path.join(basedir, 'avocado')):
    sys.path.append(basedir)

from avocado import test
from avocado.utils import script


@unittest.skip("This class should not be tested per se")
class AvocadoPass(test.Test):

    def action(self):
        variable = True
        self.assertTrue(variable)
        self.whiteboard = 'foo'


@unittest.skip("This class should not be tested per se")
class AvocadoFailNoAction(test.Test):

    """
    I don't have an action() method defined!
    """
    pass

PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""


class TestClassTest(unittest.TestCase):

    def setUp(self):
        self.base_logdir = tempfile.mkdtemp(prefix='avocado_test_unittest')
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir)
        self.tst_instance_pass.run_avocado()

    def testFailNoActionRunTest(self):
        tst_instance = AvocadoFailNoAction()
        try:
            tst_instance.action()
            raise AssertionError("Test instance did not raise NotImplementedError")
        except NotImplementedError:
            pass

    def testFailNoActionRunAvocado(self):
        tst_instance = AvocadoFailNoAction()
        tst_instance.run_avocado()
        self.assertEqual(tst_instance.status, 'FAIL')
        self.assertEqual(tst_instance.fail_class, 'NotImplementedError')

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
        whiteboard_file = os.path.join(self.tst_instance_pass.logdir, 'whiteboard')
        self.assertTrue(os.path.isfile(whiteboard_file))
        with open(whiteboard_file, 'r') as whiteboard_file_obj:
            whiteboard_contents = whiteboard_file_obj.read().strip()
            self.assertTrue(whiteboard_contents, 'foo')

    def testTaggedNameNewTests(self):
        """
        New test instances should have crescent tag instances.
        """
        new_tst_instance = AvocadoPass(base_logdir=self.base_logdir)
        new_tst_instance.run_avocado()
        self.assertEqual(new_tst_instance.tagged_name, "AvocadoPass.1")
        self.assertEqual(new_tst_instance.tag, "1")

    def tearDown(self):
        if os.path.isdir(self.base_logdir):
            shutil.rmtree(self.base_logdir, ignore_errors=True)


class DropinClassTest(unittest.TestCase):

    def setUp(self):
        self.pass_script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_dropin_unittest')
        self.pass_script.save()

        self.fail_script = script.TemporaryScript(
            'avocado_fail.sh',
            FAIL_SCRIPT_CONTENTS,
            'avocado_dropin_unittest')
        self.fail_script.save()

        self.tst_instance_pass = test.DropinTest(
            path=self.pass_script.path,
            base_logdir=os.path.dirname(self.pass_script.path))
        self.tst_instance_pass.run_avocado()

        self.tst_instance_fail = test.DropinTest(
            path=self.fail_script.path,
            base_logdir=os.path.dirname(self.fail_script.path))
        self.tst_instance_fail.run_avocado()

    def testDropinPassStatus(self):
        self.assertEqual(self.tst_instance_pass.status, 'PASS')

    def testDropinFailStatus(self):
        self.assertEqual(self.tst_instance_fail.status, 'FAIL')

    def tearDown(self):
        self.pass_script.remove()
        self.fail_script.remove()

if __name__ == '__main__':
    unittest.main()
