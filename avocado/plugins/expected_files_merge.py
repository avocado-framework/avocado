
"""
Functions for merging equal expected files together
"""

import os
import shutil

from avocado.core.plugin_interfaces import JobPost, CLI
from avocado.utils import genio


def _merge_expected_files(parent_directory):
    """
    Finds all output, stdout and stderr expected files in subdirectories and
    groups equal files together. After that finds the biggest group for every
    file type and creates file in parent directory which is equal to all files
    in group. At the end it deletes files in group because they are no long needed.
    :param parent_directory: Directory where should be merge file created
    :type parent_directory: str
    """

    stdout_dict = {}
    stderr_dict = {}
    output_dict = {}
    for path in os.listdir(parent_directory):
        variants_level_path = os.path.join(parent_directory, path)
        if os.path.isdir(variants_level_path):
            for file in os.listdir(variants_level_path):
                file = os.path.join(variants_level_path, file)
                if file.endswith('output.expected'):
                    _save_file_to_group(file, output_dict)
                elif file.endswith('stdout.expected'):
                    _save_file_to_group(file, stdout_dict)
                elif file.endswith('stderr.expected'):
                    _save_file_to_group(file, stderr_dict)
    if output_dict:
        merged_file = _get_best_group(output_dict)
        if merged_file is not None:
            not_useful_files = output_dict[merged_file]
            shutil.copyfile(merged_file, os.path.join(parent_directory, 'output.expected'))
            _delete_files(not_useful_files)
    if stdout_dict:
        merged_file = _get_best_group(stdout_dict)
        if merged_file is not None:
            not_useful_files = stdout_dict[merged_file]
            shutil.copyfile(merged_file, os.path.join(parent_directory, 'stdout.expected'))
            _delete_files(not_useful_files)
    if stderr_dict:
        merged_file = _get_best_group(stderr_dict)
        if merged_file is not None:
            not_useful_files = stderr_dict[merged_file]
            shutil.copyfile(merged_file, os.path.join(parent_directory, 'stderr.expected'))
            _delete_files(not_useful_files)


def _save_file_to_group(file, file_dict):
    """
    Saves file in to the dic under key which is the name of equal file
    :param file: file name for grouping
    :type file: str
    :param file_dict: dictionary with groups of equal files
    :type file_dict:  dict
    """
    is_same = False
    for key in file_dict:
        if genio.are_files_equal(key, file):
            file_dict[key].append(file)
            is_same = True
            break
    if not is_same:
        file_dict[file] = [file]


def _get_best_group(file_dict):
    """
    Finds the biggest group form dictionary
    :param file_dict: dictionary with groups of equal files
    :type file_dict:  dict
    :return: key to the biggest group or None
    :rtype:str
    """
    if len(file_dict) == 1:
        return list(file_dict)[0]
    size_array = [len(l)for _, l in file_dict.items()]
    max_size = max(size_array)
    min_size = min(size_array)
    if max_size == min_size:
        return None
    return max(file_dict, key=lambda x: len(file_dict[x]))


def _delete_files(files):
    """
    Deletes files and also directory if it's empty
    :param files: list of files which should be deleted
    :type files: list
    """
    for file in files:
        os.remove(file)
        try:
            os.rmdir(os.path.dirname(file))
        except OSError:
            continue


def merge_expected_files(references):
    """
    Cascade merge of equal expected files in job references from
    variant level to file level
    :param references: list of job references
    :type references: list
    """
    for reference in references:
        file_level_path = os.path.abspath("%s.data" % reference)
        if os.path.exists(file_level_path):
            for path in os.listdir(file_level_path):
                test_level_path = os.path.join(file_level_path, path)
                if os.path.isdir(test_level_path):
                    _merge_expected_files(test_level_path)
            _merge_expected_files(file_level_path)


class FilesMerge(JobPost, CLI):

    """
    Plugin for merging equal expected files together
    """

    name = 'merge'
    description = 'Merge of equal expected files'
    _instance = None
    output_check_record = False

    def __new__(class_, *args, **kwargs):
        if not isinstance(class_._instance, class_):
            class_._instance = object.__new__(class_, *args, **kwargs)
        return class_._instance

    def configure(self, parser):
        pass

    def run(self, config):
        if config.get('output_check_record', None):
            self.output_check_record = True

    def post(self, job):
        if self.output_check_record:
            merge_expected_files(job.config['references'])
