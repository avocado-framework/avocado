#!/usr/bin/env python

import os
import unittest

#from avocado.core import exceptions
from avocado.utils import config_change_validation as diffvalidate


class ConfigChangeValidationTest(unittest.TestCase):

    def setUp(self):
        self.config_change = diffvalidate.ConfigChange()
        self.config_files = ["file1.cnf", "file2.cnf"]
        with open(self.config_files[0], "w") as f:
            f.write("")
        with open(self.config_files[1], "w") as f:
            f.write("")

    def tearDown(self):
        diffvalidate.del_temp_file_copies(self.config_change.get_target_config_files())
        for config_file in self.config_files:
            os.unlink(config_file)

    def test_change_success(self):
        config_files = self.config_files
        with open(config_files[0], "w") as f:
            f.write("this line is removed\n")
        with open(config_files[1], "w") as f:
            f.write("this line is not removed\n")

        config_change = self.config_change
        config_change.add_validated_config_files(config_files)
        config_change.append_expected_add(config_files[0], "this is a new line")
        config_change.append_expected_remove(config_files[0], "this line is removed")
        config_change.append_expected_add(config_files[1], "this is a new line again")

        diffvalidate.make_temp_file_copies(config_change.get_target_config_files())
        with open(config_files[0], "w") as f:
            f.write("this is a new line")
        with open(config_files[1], "w") as f:
            f.write("this line is not removed\nthis is a new line again\n")

        changes = diffvalidate.extract_config_changes(config_change.get_target_config_files())
        change_success = diffvalidate.assert_config_change(changes, config_change.config_files_dict)
        change_dict = diffvalidate.assert_config_change_dict(changes, config_change.config_files_dict)
        self.assertTrue(change_success, "The change must be valid:\n%s" % diffvalidate.create_diff_report(change_dict))

    def test_change_wrong_no_change(self):
        config_files = self.config_files
        with open(config_files[0], "w") as f:
            f.write("this line is removed\n")

        config_change = self.config_change
        config_change.add_validated_config_files(config_files)
        config_change.append_expected_add(config_files[0], "this is a new line")
        config_change.append_expected_remove(config_files[0], "this line is removed")

        diffvalidate.make_temp_file_copies(config_change.get_target_config_files())

        changes = diffvalidate.extract_config_changes(config_change.get_target_config_files())
        change_success = diffvalidate.assert_config_change(changes, config_change.config_files_dict)
        change_dict = diffvalidate.assert_config_change_dict(changes, config_change.config_files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diffvalidate.create_diff_report(change_dict))

    def test_change_wrong_add(self):
        config_files = self.config_files
        with open(config_files[0], "w") as f:
            f.write("this line is removed\n")

        config_change = self.config_change
        config_change.add_validated_config_files(config_files)
        config_change.append_expected_add(config_files[0], "this is a new line")
        config_change.append_expected_remove(config_files[0], "this line is removed")

        diffvalidate.make_temp_file_copies(config_change.get_target_config_files())
        with open(config_files[0], "w") as f:
            f.write("this is a wrong new line\n")

        changes = diffvalidate.extract_config_changes(config_change.get_target_config_files())
        change_success = diffvalidate.assert_config_change(changes, config_change.config_files_dict)
        change_dict = diffvalidate.assert_config_change_dict(changes, config_change.config_files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diffvalidate.create_diff_report(change_dict))

    def test_change_unexpected_remove(self):
        config_files = self.config_files
        with open(config_files[0], "w") as f:
            f.write("this line is removed\n")

        config_change = self.config_change
        config_change.add_validated_config_files(config_files)
        config_change.append_expected_add(config_files[0], "this is a new line")

        diffvalidate.make_temp_file_copies(config_change.get_target_config_files())
        with open(config_files[0], "w") as f:
            f.write("this is a new line\n")

        changes = diffvalidate.extract_config_changes(config_change.get_target_config_files())
        change_success = diffvalidate.assert_config_change(changes, config_change.config_files_dict)
        change_dict = diffvalidate.assert_config_change_dict(changes, config_change.config_files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diffvalidate.create_diff_report(change_dict))

    def test_change_unexpected_add(self):
        config_files = self.config_files
        with open(config_files[0], "w") as f:
            f.write("this line is removed\n")

        config_change = self.config_change
        config_change.add_validated_config_files(config_files)
        config_change.append_expected_remove(config_files[0], "this line is removed")

        diffvalidate.make_temp_file_copies(config_change.get_target_config_files())
        with open(config_files[0], "w") as f:
            f.write("this is an unexpected new line\n")

        changes = diffvalidate.extract_config_changes(config_change.get_target_config_files())
        change_success = diffvalidate.assert_config_change(changes, config_change.config_files_dict)
        change_dict = diffvalidate.assert_config_change_dict(changes, config_change.config_files_dict)
        self.assertFalse(change_success, "The change must not be valid:\n%s" % diffvalidate.create_diff_report(change_dict))


if __name__ == '__main__':
    unittest.main()
