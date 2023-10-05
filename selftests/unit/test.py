import os
import tempfile
import unittest.mock

from avocado.core import test
from avocado.core.test_id import TestID
from avocado.utils import path
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

    def setUp(self):
        prefix = temp_dir_prefix(self)
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)

    def _get_fake_filename_test(self, name):
        class FakeFilename(TestClassTestUnit.DummyTest):
            @property
            def filename(self):
                return name

        tst_id = TestID("test", name=name)
        return FakeFilename("test", tst_id, base_logdir=self.tmpdir.name)

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_ugly_name(self):
        def run(name, path_name):
            """Initialize test and check the dirs were created"""
            tst = self.DummyTest("test", TestID(1, name), base_logdir=self.tmpdir.name)
            self.assertEqual(os.path.basename(tst.workdir), path_name)
            self.assertTrue(os.path.exists(tst.workdir))
            self.assertEqual(
                os.path.dirname(os.path.dirname(tst.workdir)), self.tmpdir.name
            )

        run("/absolute/path", "1-_absolute_path")
        run("./relative/path", "1-._relative_path")
        run("../../multi_level/relative/path", "1-.._.._multi_level_relative_path")
        # Greek word 'kosme'
        run(
            "\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5",
            "1-\xce\xba\xe1\xbd\xb9\xcf\x83\xce\xbc\xce\xb5",
        )
        # Particularly problematic noncharacters in 16-bit applications
        name = (
            "\xb7\x95\xef\xb7\x96\xef\xb7\x97\xef\xb7\x98\xef\xb7\x99"
            "\xef\xb7\x9a\xef\xb7\x9b\xef\xb7\x9c\xef\xb7\x9d\xef\xb7"
            "\x9e\xef\xb7\x9f\xef\xb7\xa0\xef\xb7\xa1\xef\xb7\xa2\xef"
            "\xb7\xa3\xef\xb7\xa4\xef\xb7\xa5\xef\xb7\xa6\xef\xb7\xa7"
            "\xef\xb7\xa8\xef\xb7\xa9\xef\xb7\xaa\xef\xb7\xab\xef\xb7"
            "\xac\xef\xb7\xad\xef\xb7\xae\xef\xb7\xaf"
        )
        run(name, "1-" + name)

    def test_long_name(self):
        def check(uid, name, variant, exp_logdir):
            tst = self.DummyTest(
                "test", TestID(uid, name, variant), base_logdir=self.tmpdir.name
            )
            self.assertEqual(os.path.basename(tst.workdir), exp_logdir)
            return tst

        max_length = path.get_max_file_name_length(self.tmpdir.name)
        # uid takes 2 chars, but still fits
        length = max_length - 2
        check(1, "a" * length, None, "1-" + ("a" * length))
        # uid and variant each takes 2 chars, but still fits
        length = max_length - 4
        check(2, "a" * length, {"variant_id": 1}, "2-" + ("a" * length) + "_1")
        # uid and variant each takes 3 chars, but still fits
        length = max_length - 6
        check(99, "a" * length, {"variant_id": 88}, "99-" + ("a" * length) + "_88")
        # name is one char over limit, so name must shrink
        length = max_length - 3
        check(3, "a" * length, {"variant_id": 1}, "3-" + ("a" * (length - 1)) + "_1")
        # Shrink variant
        length = max_length - 2
        check("a" * length, "whatever", {"variant_id": 99}, "a" * length + "_9")
        length = max_length - 1
        check("a" * length, "whatever", {"variant_id": 99}, "a" * length + "_")
        # Impossible to store (uid does not fit
        self.assertRaises(
            RuntimeError,
            check,
            "a" * (max_length + 1),
            "whatever",
            {"variant_id": "else"},
            None,
        )

    def test_data_dir(self):
        """
        Checks `get_data()` won't report fs-unfriendly data dir name
        """
        # A conservative max length, based on commonly used filesystems
        max_length = 200
        with unittest.mock.patch(
            "avocado.core.test.TestData._max_name_length", return_value=max_length
        ):
            max_length_name = os.path.join(self.tmpdir.name, "a" * max_length)
            tst = self._get_fake_filename_test(max_length_name)
            self.assertEqual(
                os.path.join(self.tmpdir.name, max_length_name + ".data"),
                tst.get_data("", "file", False),
            )

    def test_no_data_dir(self):
        """
        Tests that with a filename too long, no datadir is possible
        """
        # A conservative max length, based on commonly used filesystems
        max_length = 200
        with unittest.mock.patch(
            "avocado.core.test.TestData._max_name_length", return_value=max_length
        ):
            above_limit_name = os.path.join(self.tmpdir.name, "a" * (max_length + 1))
            tst = self._get_fake_filename_test(above_limit_name)
            self.assertFalse(tst.get_data("", "file", False))

    def test_try_override_test_variable(self):
        dummy_test = self.DummyTest(base_logdir=self.tmpdir.name)
        self.assertRaises(AttributeError, setattr, dummy_test, "name", "whatever")
        self.assertRaises(AttributeError, setattr, dummy_test, "status", "whatever")


class TestClassTest(unittest.TestCase):
    def setUp(self):
        class AvocadoPass(test.Test):
            def test(self):
                variable = True
                self.assertTrue(variable)
                self.whiteboard = "foo"

        prefix = temp_dir_prefix(self)
        self.base_logdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.tst_instance_pass = AvocadoPass(base_logdir=self.base_logdir.name)
        self.tst_instance_pass.run_avocado()

    def test_class_attributes_name(self):
        self.assertEqual(self.tst_instance_pass.name, "0-AvocadoPass")

    def test_class_attributes_status(self):
        self.assertEqual(self.tst_instance_pass.status, "PASS")

    def test_class_attributes_time_elapsed(self):
        self.assertIsInstance(self.tst_instance_pass.time_elapsed, float)

    def tearDown(self):
        self.base_logdir.cleanup()


if __name__ == "__main__":
    unittest.main()
