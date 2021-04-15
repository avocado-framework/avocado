import os
import tempfile
import unittest.mock

from avocado.core import exceptions, test
from avocado.core.test_id import TestID
from avocado.utils import script
from selftests.utils import setup_avocado_loggers, temp_dir_prefix

setup_avocado_loggers()


PASS_SCRIPT_CONTENTS = """#!/bin/sh
true
"""

FAIL_SCRIPT_CONTENTS = """#!/bin/sh
false
"""


class TestClassTestUnit(unittest.TestCase):

    class DummyTest(test.Test):
        def test(self):
            pass

        def skip(self):
            self.skipTest('dummy skip test')

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def _get_fake_filename_test(self, name):

        class FakeFilename(test.Test):
            @property
            def filename(self):
                return name

            def test(self):
                pass

        tst_id = TestID("test", name=name)
        return FakeFilename("test", tst_id, base_logdir=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_ugly_name(self):
        def run(name, path_name):
            """ Initialize test and check the dirs were created """
            tst = self.DummyTest("test", TestID(1, name),
                                 base_logdir=self.tmpdir.name)
            self.assertEqual(os.path.basename(tst.logdir), path_name)
            self.assertTrue(os.path.exists(tst.logdir))
            self.assertEqual(os.path.dirname(os.path.dirname(tst.logdir)),
                             self.tmpdir.name)

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

    def test_long_name(self):
        def check(uid, name, variant, exp_logdir):
            tst = self.DummyTest("test", TestID(uid, name, variant),
                                 base_logdir=self.tmpdir.name)
            self.assertEqual(os.path.basename(tst.logdir), exp_logdir)
            return tst

        # Everything fits
        check(1, "a" * 253, None, "1-" + ("a" * 253))
        check(2, "a" * 251, {"variant_id": 1}, "2-" + ("a" * 251) + "_1")
        check(99, "a" * 249, {"variant_id": 88}, "99-" + ("a" * 249) + "_88")
        # Shrink name
        check(3, "a" * 252, {"variant_id": 1}, "3-" + ('a' * 251) + "_1")
        # Shrink variant
        check("a" * 253, "whatever", {"variant_id": 99}, "a" * 253 + "_9")
        check("a" * 254, "whatever", {"variant_id": 99}, "a" * 254 + "_")
        # No variant
        tst = check("a" * 255, "whatever", {"variant_id": "whatever-else"},
                    "a" * 255)
        # Impossible to store (uid does not fit
        self.assertRaises(RuntimeError, check, "a" * 256, "whatever",
                          {"variant_id": "else"}, None)

        self.assertEqual(os.path.basename(tst.workdir),
                         os.path.basename(tst.logdir))

    def test_data_dir(self):
        """
        Checks `get_data()` won't report fs-unfriendly data dir name
        """
        max_length_name = os.path.join(self.tmpdir.name, "a" * 250)
        tst = self._get_fake_filename_test(max_length_name)
        self.assertEqual(os.path.join(self.tmpdir.name, max_length_name + ".data"),
                         tst.get_data('', 'file', False))

    def test_no_data_dir(self):
        """
        Tests that with a filename too long, no datadir is possible
        """
        above_limit_name = os.path.join(self.tmpdir.name, "a" * 251)
        tst = self._get_fake_filename_test(above_limit_name)
        self.assertFalse(tst.get_data('', 'file', False))
        tst._record_reference('stdout', 'stdout.expected')
        tst._record_reference('stderr', 'stderr.expected')
        tst._record_reference('output', 'output.expected')

    def test_all_dirs_exists_no_hang(self):
        with unittest.mock.patch('os.path.exists', return_value=True):
            self.assertRaises(exceptions.TestSetupFail, self.DummyTest, "test",
                              TestID(1, "name"), base_logdir=self.tmpdir.name)

    def test_try_override_test_variable(self):
        dummy_test = self.DummyTest(base_logdir=self.tmpdir.name)
        self.assertRaises(AttributeError, setattr, dummy_test, "name", "whatever")
        self.assertRaises(AttributeError, setattr, dummy_test, "status", "whatever")

    def test_check_reference_success(self):
        '''
        Tests that a check is made, and is successful
        '''
        class GetDataTest(test.Test):
            def test(self):
                pass

            def get_data(self, filename, source=None, must_exist=True):
                # return the filename (path, really) unchanged
                return filename

        tst = GetDataTest("test", TestID(1, "test"),
                          base_logdir=self.tmpdir.name)
        content = 'expected content\n'
        content_path = os.path.join(tst.logdir, 'content')
        with open(content_path, 'w') as produced:
            produced.write(content)
        self.assertTrue(tst._check_reference(content_path,
                                             content_path,
                                             'content.diff',
                                             'content_diff',
                                             'Content'))

    def test_check_reference_does_not_exist(self):
        '''
        Tests that a check is not made for a file that does not exist
        '''
        tst = self.DummyTest("test", TestID(1, "test"),
                             base_logdir=self.tmpdir.name)
        self.assertFalse(tst._check_reference('does_not_exist',
                                              'stdout.expected',
                                              'stdout.diff',
                                              'stdout_diff',
                                              'Stdout'))


class TestClassTest(unittest.TestCase):

    def setUp(self):
        class AvocadoPass(test.Test):

            def test(self):
                variable = True
                self.assertTrue(variable)
                self.whiteboard = 'foo'

        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.base_logdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir.name)
        self.tst_instance_pass.run_avocado()

    def test_class_attributes_name(self):
        self.assertEqual(self.tst_instance_pass.name, '0-AvocadoPass')

    def test_class_attributes_status(self):
        self.assertEqual(self.tst_instance_pass.status, 'PASS')

    def test_class_attributes_time_elapsed(self):
        self.assertIsInstance(self.tst_instance_pass.time_elapsed, float)

    def test_whiteboard_save(self):
        whiteboard_file = os.path.join(
            self.tst_instance_pass.logdir, 'whiteboard')
        self.assertTrue(os.path.isfile(whiteboard_file))
        with open(whiteboard_file, 'r') as whiteboard_file_obj:
            whiteboard_contents = whiteboard_file_obj.read().strip()
            self.assertTrue(whiteboard_contents, 'foo')

    def test_running_test_twice_with_the_same_uid_failure(self):
        class AvocadoPass(test.Test):

            def test(self):
                pass

        self.assertRaises(exceptions.TestSetupFail, AvocadoPass,
                          base_logdir=self.base_logdir.name)

    def tearDown(self):
        self.base_logdir.cleanup()


class SimpleTestClassTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.script = None

    def test_simple_test_pass_status(self):
        self.script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.script.save()
        tst_instance = test.SimpleTest(
            name=TestID(1, self.script.path),
            base_logdir=self.tmpdir.name)
        tst_instance.run_avocado()
        self.assertEqual(tst_instance.status, 'PASS')

    def test_simple_test_fail_status(self):
        self.script = script.TemporaryScript(
            'avocado_fail.sh',
            FAIL_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.script.save()
        tst_instance = test.SimpleTest(
            name=TestID(1, self.script.path),
            base_logdir=self.tmpdir.name)
        tst_instance.run_avocado()
        self.assertEqual(tst_instance.status, 'FAIL')

    def tearDown(self):
        if self.script is not None:
            self.script.remove()
        self.tmpdir.cleanup()


class MockingTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def test_init_minimal_params(self):
        test.MockingTest(base_logdir=self.tmpdir.name)

    def test_init_positional(self):
        tst = test.MockingTest("test", TestID(1, "my_name"),
                               {}, None, "1",
                               None, None, "extra_param1",
                               "extra_param2", base_logdir=self.tmpdir.name)
        self.assertEqual(tst.name, "1-my_name")

    def test_init_kwargs(self):
        tst = test.MockingTest(methodName="test",
                               name=TestID(1, "my_name2"),
                               params={}, base_logdir=self.tmpdir.name,
                               tag="a", config=None, runner_queue=None,
                               extra1="extra_param1",
                               extra2="extra_param2")
        self.assertEqual(tst.name, "1-my_name2")

    def test_positional_kwargs(self):
        """
        Tests both positional and kwargs (theoretically impossible in
        python, but valid for nasty tests)

        keyword args are used as they explicitly represent what they mean
        """
        tst = test.MockingTest("not used", "who cares", {}, None, "0",
                               None, None, "extra_param1",
                               "extra_param2",
                               methodName="test",
                               name=TestID(1, "my_name3"),
                               params={}, base_logdir=self.tmpdir.name,
                               tag="3", config=None, runner_queue=None,
                               extra1="extra_param3",
                               extra2="extra_param4")
        self.assertEqual(tst.name, "1-my_name3")

    def test_combination(self):
        tst = test.MockingTest("test", TestID(1, "my_name4"),
                               tag="321",
                               other_param="Whatever",
                               base_logdir=self.tmpdir.name)
        self.assertEqual(tst.name, "1-my_name4")

    def test_combination_2(self):
        """
        Tests an ugly combination (positional argument overrides
        kwargs, this only happens when the substituted class reorders
        the positional arguments.  We try to first match keyword args
        and then fall-back to positional ones.
        """
        name = "positional_method_name_becomes_test_name"
        tag = "positional_base_logdir_becomes_tag"
        tst = test.MockingTest(TestID(1, name), None, None, tag,
                               methodName="test",
                               other_param="Whatever",
                               base_logdir=self.tmpdir.name)
        self.assertEqual(tst.name, "1-" + name)

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
