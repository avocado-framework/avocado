import os
import shutil
import sys
import tempfile
from flexmock import flexmock, flexmock_teardown

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from avocado.core import test, exceptions
from avocado.utils import script

PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""


class DummyTest(test.Test):

    def test(self):
        pass


class TestClassTestUnit(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)

    def tearDown(self):
        flexmock_teardown()
        shutil.rmtree(self.tmpdir)

    def testUglyName(self):
        def run(name, path_name):
            """ Initialize test and check the dirs were created """
            tst = DummyTest("test", test.TestName(1, name),
                            base_logdir=self.tmpdir)
            self.assertEqual(os.path.basename(tst.logdir), path_name)
            self.assertTrue(os.path.exists(tst.logdir))
            self.assertEqual(os.path.dirname(os.path.dirname(tst.logdir)),
                             self.tmpdir)

        run("/absolute/path", "1-_absolute_path")
        run("./relative/path", "1-._relative_path")
        run("../../multi_level/relative/path",
            "1-.._.._multi_level_relative_path")
        # Greek word 'kosme'
        run("\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5",
            "1-\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5")
        # Particularly problematic noncharacters in 16-bit applications
        name = ("\xb7\x95\xef\xb7\x96\xef\xb7\x97\xef\xb7\x98\xef\xb7\x99"
                "\xef\xb7\x9a\xef\xb7\x9b\xef\xb7\x9c\xef\xb7\x9d\xef\xb7"
                "\x9e\xef\xb7\x9f\xef\xb7\xa0\xef\xb7\xa1\xef\xb7\xa2\xef"
                "\xb7\xa3\xef\xb7\xa4\xef\xb7\xa5\xef\xb7\xa6\xef\xb7\xa7"
                "\xef\xb7\xa8\xef\xb7\xa9\xef\xb7\xaa\xef\xb7\xab\xef\xb7"
                "\xac\xef\xb7\xad\xef\xb7\xae\xef\xb7\xaf")
        run(name, "1-" + name)

    def testLongName(self):
        def check(uid, name, variant, exp_logdir):
            tst = DummyTest("test", test.TestName(uid, name, variant))
            self.assertEqual(os.path.basename(tst.logdir), exp_logdir)
            return tst

        # Everything fits
        check(1, "a" * 253, None, "1-" + ("a" * 253))
        check(2, "a" * 251, 1, "2-" + ("a" * 251) + ";1")
        check(99, "a" * 249, 88, "99-" + ("a" * 249) + ";88")
        # Shrink name
        check(3, "a" * 252, 1, "3-" + ('a' * 251) + ";1")
        # Shrink variant
        check("a" * 253, "whatever", 99, "a" * 253 + ";9")
        check("a" * 254, "whatever", 99, "a" * 254 + ";")
        # No variant
        tst = check("a" * 255, "whatever", "whatever-else", "a" * 255)
        # Impossible to store (uid does not fit
        self.assertRaises(AssertionError, check, "a" * 256, "whatever", "else",
                          None)

        self.assertEqual(os.path.basename(tst.workdir),
                         os.path.basename(tst.logdir))
        flexmock(tst)
        tst.should_receive('filename').and_return(os.path.join(self.tmpdir,
                                                               "a"*250))
        self.assertEqual(os.path.join(self.tmpdir, "a"*250 + ".data"),
                         tst.datadir)
        tst.should_receive('filename').and_return("a"*251)
        self.assertFalse(tst.datadir)
        tst._record_reference_stdout       # Should does nothing
        tst._record_reference_stderr       # Should does nothing
        tst._record_reference_stdout()
        tst._record_reference_stderr()

    def testAllDirsExistsNoHang(self):
        flexmock(os.path)
        os.path.should_receive('exists').and_return(True)
        self.assertRaises(exceptions.TestSetupFail, DummyTest, "test",
                          test.TestName(1, "name"))


class TestClassTest(unittest.TestCase):

    def setUp(self):
        class AvocadoPass(test.Test):

            def test(self):
                variable = True
                self.assertTrue(variable)
                self.whiteboard = 'foo'

        self.base_logdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir)
        self.tst_instance_pass.run_avocado()

    def testClassAttributesName(self):
        self.assertEqual(self.tst_instance_pass.name, '0-AvocadoPass')

    def testClassAttributesStatus(self):
        self.assertEqual(self.tst_instance_pass.status, 'PASS')

    def testClassAttributesTimeElapsed(self):
        self.assertIsInstance(self.tst_instance_pass.time_elapsed, float)

    def testWhiteboardSave(self):
        whiteboard_file = os.path.join(
            self.tst_instance_pass.logdir, 'whiteboard')
        self.assertTrue(os.path.isfile(whiteboard_file))
        with open(whiteboard_file, 'r') as whiteboard_file_obj:
            whiteboard_contents = whiteboard_file_obj.read().strip()
            self.assertTrue(whiteboard_contents, 'foo')

    def testRunningTestTwiceWithTheSameUidFailure(self):
        class AvocadoPass(test.Test):

            def test(self):
                pass

        self.assertRaises(exceptions.TestSetupFail, AvocadoPass,
                          base_logdir=self.base_logdir)

    def testNotTestName(self):
        self.assertRaises(test.NameNotTestNameError,
                          test.Test, name='mytest')

    def tearDown(self):
        shutil.rmtree(self.base_logdir)


class SimpleTestClassTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
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
            name=test.TestName(1, self.pass_script.path),
            base_logdir=self.tmpdir)
        self.tst_instance_pass.run_avocado()

        self.tst_instance_fail = test.SimpleTest(
            name=test.TestName(1, self.fail_script.path),
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


class SkipTest(unittest.TestCase):

    def setUp(self):
        self.tests = []

    def test_init(self):
        # No params
        self.tests.append(test.SkipTest())
        self.assertRaises(exceptions.TestSkipError, self.tests[-1].setUp)
        self.assertRaises(RuntimeError, self.tests[-1].test)
        # Positional
        self.tests.append(test.SkipTest("test", test.TestName(1, "my_name"),
                                        {}, None, "1",
                                        None, None, "extra_param1",
                                        "extra_param2"))
        self.assertEqual(self.tests[-1].name, "1-my_name")
        # Kwargs
        self.tests.append(test.SkipTest(methodName="test",
                                        name=test.TestName(1, "my_name2"),
                                        params={}, base_logdir=None,
                                        tag="a", job=None, runner_queue=None,
                                        extra1="extra_param1",
                                        extra2="extra_param2"))
        self.assertEqual(self.tests[-1].name, "1-my_name2")
        # both (theoretically impossible in python, but valid for nasty tests)
        # keyword args are used as they explicitly represent what they mean
        self.tests.append(test.SkipTest("not used", "who cares", {}, None, "0",
                                        None, None, "extra_param1",
                                        "extra_param2",
                                        methodName="test",
                                        name=test.TestName(1, "my_name3"),
                                        params={}, base_logdir=None,
                                        tag="3", job=None, runner_queue=None,
                                        extra1="extra_param3",
                                        extra2="extra_param4"))
        self.assertEqual(self.tests[-1].name, "1-my_name3")
        # combination
        self.tests.append(test.SkipTest("test", test.TestName(1, "my_name4"),
                                        tag="321",
                                        other_param="Whatever"))
        self.assertEqual(self.tests[-1].name, "1-my_name4")
        # ugly combination (positional argument overrides kwargs, this only
        # happens when the substituted class reorders the positional arguments.
        # We try to first match keyword args and then fall-back to positional
        # ones.
        name = "positional_method_name_becomes_test_name"
        tag = "positional_base_logdir_becomes_tag"
        self.tests.append(test.SkipTest(test.TestName(1, name), None, None, tag,
                                        methodName="test",
                                        other_param="Whatever"))
        self.assertEqual(self.tests[-1].name, "1-" + name)

    def tearDown(self):
        for tst in self.tests:
            try:
                shutil.rmtree(os.path.dirname(tst.logdir))
            except Exception:
                pass

if __name__ == '__main__':
    unittest.main()
