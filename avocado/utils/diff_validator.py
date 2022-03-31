# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; specifically version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# This code was inspired in the autotest project,
# client/shared/utils.py
# Authors: Plamen Dimitrov <plamen.dimitrov@intra2net.com>, Kristof Katus <kristof.katus@intra2net.com>

"""
Diff validator: Utility for testing file changes

Some typical use of this utility would be:

>>> import diff_validator
>>> change = diff_validator.Change()
>>> change.add_validated_files(["/etc/somerc"])
>>> change.append_expected_add("/etc/somerc", "this is a new line")
>>> change.append_expected_remove("/etc/somerc", "this line is removed")
>>> diff_validator.make_temp_file_copies(change.get_target_files())

After making changes through some in-test operation:

>>> changes = diff_validator.extract_changes(change.get_target_files())
>>> change_success = diff_validator.assert_change(changes, change.files_dict)

If test fails due to invalid change on the system:

>>> if not change_success:
>>>     changes = diff_validator.assert_change_dict(changes, change.files_dict)
>>>     raise DiffValidationError("Change is different than expected:\n%s" % diff_validator.create_diff_report(changes))
>>> else:
>>>     logging.info("Change made successfully")
>>> diff_validator.del_temp_file_copies(change.get_target_files())

"""

import difflib
import os
import shutil


class DiffValidationError(Exception):
    pass


def get_temp_file_path(file_path):
    """
    Generates a temporary filename.

    :param str file_path: file path prefix
    :returns: appended file path
    :rtype: str
    """
    return file_path + '.tmp'


def make_temp_file_copies(file_paths):
    """
    Creates temporary copies of the provided files.

    :param file_paths: file paths to be copied
    :type file_paths: [str]
    """
    for file_path in file_paths:
        temp_file_path = get_temp_file_path(file_path)
        shutil.copyfile(file_path, temp_file_path)


def del_temp_file_copies(file_paths):
    """
    Deletes all the provided files.

    :param file_paths: deleted file paths (their temporary versions)
    :type file_paths: [str]
    """
    for file_path in file_paths:
        temp_file_path = get_temp_file_path(file_path)
        os.remove(temp_file_path)


def parse_unified_diff_output(lines):
    """
    Parses the unified diff output of two files.

    :param lines: diff lines
    :type lines: [str]
    :returns: pair of adds and removes, where each is a list of trimmed lines
    :rtype: ([str], [str])
    """
    adds = []
    removes = []
    for line in lines:
        # ignore filepaths in the output
        if (len(line) > 2 and (line[:3] == "+++" or
                               line[:3] == "---")):
            continue
        # ignore line range information in the output
        elif len(line) > 1 and line[:2] == "@@":
            continue
        # gather adds
        elif len(line) > 0 and line[0] == "+":
            added_line = line[1:].lstrip().rstrip()
            if len(added_line) == 0:
                continue
            adds = adds + [added_line]
        # gather removes
        elif len(line) > 0 and line[0] == "-":
            removed_line = line[1:].lstrip().rstrip()
            if len(removed_line) == 0:
                continue
            removes = removes + [removed_line]
    return (adds, removes)


def extract_changes(file_paths, compared_file_paths=None):
    """
    Extracts diff information based on the new and temporarily saved old files.

    :param file_paths: original file paths (whose temporary versions will be retrieved)
    :type file_paths: [str]
    :param compared_file_paths: custom file paths to use instead of the temporary versions
    :type compared_file_paths: [str] or None
    :returns: file paths with corresponding diff information key-value pairs
    :rtype: {str, ([str], [str])}
    """
    changes = {}
    if compared_file_paths is None:
        compared_file_paths = []

    for i in range(len(file_paths)):
        temp_file_path = get_temp_file_path(file_paths[i])

        if len(compared_file_paths) > i:
            file1, file2 = compared_file_paths[i], file_paths[i]
        else:
            file1, file2 = temp_file_path, file_paths[i]
        with open(file1, encoding='utf-8') as f1:
            lines1 = f1.readlines()
        with open(file2, encoding='utf-8') as f2:
            lines2 = f2.readlines()
        lines = difflib.unified_diff(lines1, lines2,
                                     fromfile=file1, tofile=file2, n=0)

        changes[file_paths[i]] = parse_unified_diff_output(lines)
    return changes


def assert_change_dict(actual_result, expected_result):
    """
    Calculates unexpected line changes.

    :param actual_result: actual added and removed lines
    :type actual_result: {file_path, ([added_line, ...], [removed_line, ...])}
    :param expected_result: expected added and removed lines
    :type expected_result: {file_path, ([added_line, ...], [removed_line, ...])}
    :returns: detected differences as groups of lines with filepath keys and a tuple of
              (unexpected_adds, not_present_adds, unexpected_removes, not_present_removes)
    :rtype: {str, (str, str, str, str)}
    """
    change_diffs = {}
    for file_path, actual_changes in actual_result.items():
        expected_changes = expected_result[file_path]

        actual_adds = actual_changes[0]
        actual_removes = actual_changes[1]
        expected_adds = expected_changes[0]
        expected_removes = expected_changes[1]

        # Additional unexpected adds -- they should have been not added
        unexpected_adds = sorted(set(actual_adds) - set(expected_adds))
        # Not present expected adds -- they should have been added
        not_present_adds = sorted(set(expected_adds) - set(actual_adds))
        # Additional unexpected removes - they should have been not removed
        unexpected_removes = sorted(set(actual_removes) - set(expected_removes))
        # Not present expected removes - they should have been removed
        not_present_removes = sorted(set(expected_removes) -
                                     set(actual_removes))

        change_diffs[file_path] = (unexpected_adds, not_present_adds,
                                   unexpected_removes, not_present_removes)

    return change_diffs


def assert_change(actual_result, expected_result):
    """
    Condition wrapper of the upper method.

    :param actual_result: actual added and removed lines with filepath keys and a tuple of
                          ([added_line, ...], [removed_line, ...])
    :type actual_result: {str, ([str], [str])}
    :param expected_result: expected added and removed lines of type as the actual result
    :type expected_result: {str, ([str], [str])}
    :returns: whether changes were detected
    :rtype: bool
    """
    change_diffs = assert_change_dict(actual_result, expected_result)
    for file_change in change_diffs.values():
        for line_change in file_change:
            if len(line_change) != 0:
                return False
    return True


def create_diff_report(change_diffs):
    """
    Pretty prints the output of the `change_diffs` variable.

    :param change_diffs: detected differences as groups of lines with filepath keys and a tuple of
                         (unexpected_adds, not_present_adds, unexpected_removes, not_present_removes)
    :type: {str, (str, str, str, str)}
    :returns: print string of the line differences
    :rtype: str
    """
    diff_strings = []
    for file_path, change_diff in change_diffs.items():
        if not (change_diff[0] or change_diff[1] or
                change_diff[2] or change_diff[3]):
            continue
        diff_strings.append(f"--- {get_temp_file_path(file_path)}")
        diff_strings.append(f"+++ {file_path}")
        for iter_category in range(4):
            change_category = change_diff[iter_category]
            if iter_category == 0 and change_category:
                diff_strings.append("*++ Additional unexpected adds")
            elif iter_category == 1 and change_category:
                diff_strings.append("/++ Not present expected adds")
            elif iter_category == 2 and change_category:
                diff_strings.append("*-- Additional unexpected removes")
            elif iter_category == 3 and change_category:
                diff_strings.append("/-- Not present expected removes")
            for line_change in change_category:
                diff_strings.append(str(line_change).encode('unicode_escape').decode())
    return "\n".join(diff_strings)


class Change():
    """Class for tracking and validating file changes"""

    def __init__(self):
        """Creates a change object."""
        self.files_dict = {}

    def get_target_files(self):
        """Get added files for change."""
        return list(self.files_dict.keys())

    def add_validated_files(self, filenames):
        """
        Add file to change object.

        :param filenames: files to validate
        :type filenames: [str]
        """
        for filename in filenames:
            self.files_dict[filename] = ([], [])

    def append_expected_add(self, filename, line):
        """
        Append expected added line to a file.

        :param str filename: file to append to
        :param str line: line to append to as an expected addition
        """
        try:
            self.files_dict[filename][0].append(line)
        except KeyError:
            self.files_dict[filename] = ([], [])
            self.files_dict[filename][0].append(line)

    def append_expected_remove(self, filename, line):
        """
        Append removed added line to a file.

        :param str filename: file to append to
        :param str line: line to append to as an expected removal
        """
        try:
            self.files_dict[filename][1].append(line)
        except KeyError:
            self.files_dict[filename] = ([], [])
            self.files_dict[filename][1].append(line)

    def get_all_adds(self):
        """Return a list of the added lines for all validated files."""
        all_adds = []
        for f in list(self.files_dict.keys()):
            for add in self.files_dict[f][0]:
                all_adds.append(add)
        return all_adds

    def get_all_removes(self):
        """Return a list of the removed lines for all validated files."""
        all_removes = []
        for f in list(self.files_dict.keys()):
            for add in self.files_dict[f][1]:
                all_removes.append(add)
        return all_removes
