"""
Functions for merging equal expected files together
"""

import os
import shutil

from avocado.core.plugin_interfaces import JobPost
from avocado.utils import genio


def _merge_expected_files(parent_directory):
    """
    Finds all output, stdout and stderr expected files in subdirectories and
    groups equal files together. After that finds the biggest group for every
    file type and creates file in parent directory which is equal to all files
    in group. At the end it deletes files in group because they are no longer needed.
    :param parent_directory: Directory where should be merge file created
    :type parent_directory: str
    """

    stdout_dict = {}
    stderr_dict = {}
    output_dict = {}
    for path in os.listdir(parent_directory):
        variants_level_path = os.path.join(parent_directory, path)
        if os.path.isdir(variants_level_path):
            for filename in os.listdir(variants_level_path):
                path = os.path.join(variants_level_path, filename)
                if filename == 'output.expected':
                    _save_file_to_group(path, output_dict)
                elif filename == 'stdout.expected':
                    _save_file_to_group(path, stdout_dict)
                elif filename == 'stderr.expected':
                    _save_file_to_group(path, stderr_dict)

    for file_dic, filename in ((output_dict, 'output.expected'),
                               (stdout_dict, 'stdout.expected'),
                               (stderr_dict, 'stderr.expected')):
        if file_dic:
            merged_file = _get_best_group(file_dic)
            if merged_file is not None:
                not_useful_files = file_dic[merged_file]
                shutil.copyfile(merged_file, os.path.join(parent_directory,
                                                          filename))
                _delete_files(not_useful_files)


def _save_file_to_group(path, file_dict):
    """
    Saves file in to the dict under key which is the name of equal file
    :param path: file name for grouping
    :type path: str
    :param file_dict: dictionary with groups of equal files
    :type file_dict:  dict
    """
    is_same = False
    for key in file_dict:
        if genio.are_files_equal(key, path):
            file_dict[key].append(path)
            is_same = True
            break
    if not is_same:
        file_dict[path] = [path]


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
    for filename in files:
        os.remove(filename)
        try:
            os.rmdir(os.path.dirname(filename))
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


class FilesMerge(JobPost):

    """
    Plugin for merging equal expected files together
    """

    name = 'merge'
    description = 'Merge of equal expected files'

    def post(self, job):
        if job.config.get('run.output_check_record'):
            merge_expected_files(job.config.get('run.references'))
