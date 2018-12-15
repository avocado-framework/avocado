import os
import shutil
import tempfile
import unittest
try:
    from unittest import mock
except ImportError:
    import mock

from avocado.core import test, exceptions
from avocado.utils import astring, script

from .. import setup_avocado_loggers


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

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="avocado_" + __name__)

    def _get_fake_filename_test(self, name):

        class FakeFilename(test.Test):
            @property
            def filename(self):
                return name

            def test(self):
                pass

        tst_id = test.TestID("test", name=name)
        return FakeFilename("test", tst_id, base_logdir=self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_ugly_name(self):
        def run(name, path_name):
            """ Initialize test and check the dirs were created """
            tst = self.DummyTest("test", test.TestID(1, name),
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

    def test_long_name(self):
        def check(uid, name, variant, exp_logdir):
            tst = self.DummyTest("test", test.TestID(uid, name, variant),
                                 base_logdir=self.tmpdir)
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
        max_length_name = os.path.join(self.tmpdir, "a" * 250)
        tst = self._get_fake_filename_test(max_length_name)
        self.assertEqual(os.path.join(self.tmpdir, max_length_name + ".data"),
                         tst.get_data('', 'file', False))

    def test_no_data_dir(self):
        """
        Tests that with a filename too long, no datadir is possible
        """
        above_limit_name = os.path.join(self.tmpdir, "a" * 251)
        tst = self._get_fake_filename_test(above_limit_name)
        self.assertFalse(tst.get_data('', 'file', False))
        tst._record_reference('stdout', 'stdout.expected')
        tst._record_reference('stderr', 'stderr.expected')
        tst._record_reference('output', 'output.expected')

    def test_all_dirs_exists_no_hang(self):
        with mock.patch('os.path.exists', return_value=True):
            self.assertRaises(exceptions.TestSetupFail, self.DummyTest, "test",
                              test.TestID(1, "name"), base_logdir=self.tmpdir)

    def test_try_override_test_variable(self):
        dummy_test = self.DummyTest(base_logdir=self.tmpdir)
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

        tst = GetDataTest("test", test.TestID(1, "test"),
                          base_logdir=self.tmpdir)
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
        tst = self.DummyTest("test", test.TestID(1, "test"),
                             base_logdir=self.tmpdir)
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

        self.base_logdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir)
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
                          base_logdir=self.base_logdir)

    def tearDown(self):
        shutil.rmtree(self.base_logdir)


class SimpleTestClassTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='avocado_' + __name__)
        self.script = None

    def test_simple_test_pass_status(self):
        self.script = script.TemporaryScript(
            'avocado_pass.sh',
            PASS_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.script.save()
        tst_instance = test.SimpleTest(
            name=test.TestID(1, self.script.path),
            base_logdir=self.tmpdir)
        tst_instance.run_avocado()
        self.assertEqual(tst_instance.status, 'PASS')

    def test_simple_test_fail_status(self):
        self.script = script.TemporaryScript(
            'avocado_fail.sh',
            FAIL_SCRIPT_CONTENTS,
            'avocado_simpletest_unittest')
        self.script.save()
        tst_instance = test.SimpleTest(
            name=test.TestID(1, self.script.path),
            base_logdir=self.tmpdir)
        tst_instance.run_avocado()
        self.assertEqual(tst_instance.status, 'FAIL')

    def tearDown(self):
        if self.script is not None:
            self.script.remove()
        shutil.rmtree(self.tmpdir)


class MockingTest(unittest.TestCase):

    def setUp(self):
        self.tests = []

    def test_init(self):
        # No params
        self.tests.append(test.MockingTest())
        # Positional
        self.tests.append(test.MockingTest("test", test.TestID(1, "my_name"),
                                           {}, None, "1",
                                           None, None, "extra_param1",
                                           "extra_param2"))
        self.assertEqual(self.tests[-1].name, "1-my_name")
        # Kwargs
        self.tests.append(test.MockingTest(methodName="test",
                                           name=test.TestID(1, "my_name2"),
                                           params={}, base_logdir=None,
                                           tag="a", job=None, runner_queue=None,
                                           extra1="extra_param1",
                                           extra2="extra_param2"))
        self.assertEqual(self.tests[-1].name, "1-my_name2")
        # both (theoretically impossible in python, but valid for nasty tests)
        # keyword args are used as they explicitly represent what they mean
        self.tests.append(test.MockingTest("not used", "who cares", {}, None, "0",
                                           None, None, "extra_param1",
                                           "extra_param2",
                                           methodName="test",
                                           name=test.TestID(1, "my_name3"),
                                           params={}, base_logdir=None,
                                           tag="3", job=None, runner_queue=None,
                                           extra1="extra_param3",
                                           extra2="extra_param4"))
        self.assertEqual(self.tests[-1].name, "1-my_name3")
        # combination
        self.tests.append(test.MockingTest("test", test.TestID(1, "my_name4"),
                                           tag="321",
                                           other_param="Whatever"))
        self.assertEqual(self.tests[-1].name, "1-my_name4")
        # ugly combination (positional argument overrides kwargs, this only
        # happens when the substituted class reorders the positional arguments.
        # We try to first match keyword args and then fall-back to positional
        # ones.
        name = "positional_method_name_becomes_test_name"
        tag = "positional_base_logdir_becomes_tag"
        self.tests.append(test.MockingTest(test.TestID(1, name), None, None, tag,
                                           methodName="test",
                                           other_param="Whatever"))
        self.assertEqual(self.tests[-1].name, "1-" + name)

    def tearDown(self):
        for tst in self.tests:
            try:
                shutil.rmtree(os.path.dirname(os.path.dirname(tst.logdir)))
            except Exception:
                pass


class TestID(unittest.TestCase):

    def test_uid_name(self):
        uid = 1
        name = 'file.py:klass.test_method'
        test_id = test.TestID(uid, name)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '1')
        self.assertEqual(test_id.str_filesystem,
                         astring.string_to_safe_path('%s-%s' % (uid, name)))
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_no_digits(self):
        uid = 1
        name = 'file.py:klass.test_method'
        test_id = test.TestID(uid, name, no_digits=2)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '01')
        self.assertEqual(test_id.str_filesystem,
                         astring.string_to_safe_path('%s-%s' % ('01', name)))
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_large_digits(self):
        """
        Tests that when the filesystem can only cope with the size of
        the Test ID, that's the only thing that will be kept.
        """
        uid = 1
        name = 'test'
        test_id = test.TestID(uid, name, no_digits=255)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_uid, '%0255i' % uid)
        self.assertEqual(test_id.str_filesystem, '%0255i' % uid)
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, '')

    def test_uid_name_uid_too_large_digits(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, not even the test uid, an exception will be
        raised.
        """
        test_id = test.TestID(1, 'test', no_digits=256)
        self.assertRaises(RuntimeError, lambda: test_id.str_filesystem)

    def test_uid_large_name(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, the name will be shortened.
        """
        uid = 1
        name = 'test_' * 51     # 255 characters
        test_id = test.TestID(uid, name)
        self.assertEqual(test_id.uid, 1)
        # only 253 can fit for the test name
        self.assertEqual(test_id.str_filesystem, '%s-%s' % (uid, name[:253]))
        self.assertIs(test_id.variant, None)
        self.assertIs(test_id.str_variant, "")

    def test_uid_name_large_variant(self):
        """
        Tests that when the filesystem can not cope with the size of
        the Test ID, and a variant name is present, the name will be
        removed.
        """
        uid = 1
        name = 'test'
        variant_id = 'fast_' * 51    # 255 characters
        variant = {'variant_id': variant_id}
        test_id = test.TestID(uid, name, variant=variant)
        self.assertEqual(test_id.uid, 1)
        self.assertEqual(test_id.str_filesystem, '%s_%s' % (uid, variant_id[:253]))
        self.assertIs(test_id.variant, variant_id)
        self.assertEqual(test_id.str_variant, ";%s" % variant_id)


if __name__ == '__main__':
    unittest.main()
