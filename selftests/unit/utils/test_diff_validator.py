#!/usr/bin/env python

import os
import tempfile
import unittest

from avocado.utils import diff_validator
from selftests.utils import temp_dir_prefix


class ChangeValidationTest(unittest.TestCase):

    def setUp(self):
        prefix = temp_dir_prefix(__name__, self, 'setUp')
        self.tmpdir = tempfile.TemporaryDirectory(prefix=prefix)
        self.change = diff_validator.Change()
        self.files = [os.path.join(self.tmpdir.name, "file1.cnf"),
                      os.path.join(self.tmpdir.name, "file2.cnf")]
        with open(self.files[0], "w") as f:
            f.write("")
        with open(self.files[1], "w") as f:
            f.write("")

    def tearDown(self):
        diff_validator.del_temp_file_copies(self.change.get_target_files())
        self.tmpdir.cleanup()

    def test_change_success(self):
        files = self.files
        with open(files[0], "w") as f:
            f.write("this line is removed\n")
        with open(files[1], "w") as f:
            f.write("this line is not removed\n")

        change = self.change
        change.add_validated_files(files)
        change.append_expected_add(files[0], "this is a new line")
        change.append_expected_remove(files[0], "this line is removed")
        change.append_expected_add(files[1], "this is a new line again")

        diff_validator.make_temp_file_copies(change.get_target_files())
        with open(files[0], "w") as f:
            f.write("this is a new line")
        with open(files[1], "w") as f:
            f.write("this line is not removed\nthis is a new line again\n")

        changes = diff_validator.extract_changes(change.get_target_files())
        change_success = diff_validator.assert_change(changes, change.files_dict)
        change_dict = diff_validator.assert_change_dict(changes, change.files_dict)
        self.assertTrue(change_success, "The change must be valid:\n%s" % diff_validator.create_diff_report(change_dict))

    def test_change_wrong_no_change(self):
        files = self.files
        with open(files[0], "w") as f:
            f.write("this line is removed\n")

        change = self.change
        change.add_validated_files(files)
        change.append_expected_add(files[0], "this is a new line")
        change.append_expected_remove(files[0], "this line is removed")

        diff_validator.make_temp_file_copies(change.get_target_files())

        changes = diff_validator.extract_changes(change.get_target_files())
        change_success = diff_validator.assert_change(changes, change.files_dict)
        change_dict = diff_validator.assert_change_dict(changes, change.files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diff_validator.create_diff_report(change_dict))

    def test_change_wrong_add(self):
        files = self.files
        with open(files[0], "w") as f:
            f.write("this line is removed\n")

        change = self.change
        change.add_validated_files(files)
        change.append_expected_add(files[0], "this is a new line")
        change.append_expected_remove(files[0], "this line is removed")

        diff_validator.make_temp_file_copies(change.get_target_files())
        with open(files[0], "w") as f:
            f.write("this is a wrong new line\n")

        changes = diff_validator.extract_changes(change.get_target_files())
        change_success = diff_validator.assert_change(changes, change.files_dict)
        change_dict = diff_validator.assert_change_dict(changes, change.files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diff_validator.create_diff_report(change_dict))

    def test_change_unexpected_remove(self):
        files = self.files
        with open(files[0], "w") as f:
            f.write("this line is removed\n")

        change = self.change
        change.add_validated_files(files)
        change.append_expected_add(files[0], "this is a new line")

        diff_validator.make_temp_file_copies(change.get_target_files())
        with open(files[0], "w") as f:
            f.write("this is a new line\n")

        changes = diff_validator.extract_changes(change.get_target_files())
        change_success = diff_validator.assert_change(changes, change.files_dict)
        change_dict = diff_validator.assert_change_dict(changes, change.files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diff_validator.create_diff_report(change_dict))

    def test_change_unexpected_add(self):
        files = self.files
        with open(files[0], "w") as f:
            f.write("this line is removed\n")

        change = self.change
        change.add_validated_files(files)
        change.append_expected_remove(files[0], "this line is removed")

        diff_validator.make_temp_file_copies(change.get_target_files())
        with open(files[0], "w") as f:
            f.write("this is an unexpected new line\n")

        changes = diff_validator.extract_changes(change.get_target_files())
        change_success = diff_validator.assert_change(changes, change.files_dict)
        change_dict = diff_validator.assert_change_dict(changes, change.files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diff_validator.create_diff_report(change_dict))


if __name__ == '__main__':
    unittest.main()
