#!/usr/bin/python
"""
Library used to let avocado tests find important paths in the system.
"""
import os
import sys
import glob
import shutil

from avocado.settings import settings

_ROOT_PATH = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
IN_TREE_ROOT_DIR = os.path.abspath(_ROOT_PATH)
IN_TREE_TMP_DIR = os.path.join(IN_TREE_ROOT_DIR, 'tmp')


def get_root_dir():
    if settings.intree:
        return IN_TREE_ROOT_DIR
    else:
        return settings.get_value('runner', 'root_dir')


def get_test_dir():
    if settings.intree:
        return os.path.join(get_root_dir(), 'tests')
    else:
        return settings.get_value('runner', 'test_dir')


def get_logs_dir():
    if settings.intree:
        return os.path.join(get_root_dir(), 'logs')
    else:
        return settings.get_value('runner', 'logs_dir')


def get_tmp_dir():
    if settings.intree:
        if not os.path.isdir(IN_TREE_TMP_DIR):
            os.makedirs(IN_TREE_TMP_DIR)
        return IN_TREE_TMP_DIR
    else:
        return settings.get_value('runner', 'tmp_dir')


def clean_tmp_files():
    tmp_dir = get_tmp_dir()
    if os.path.isdir(tmp_dir):
        hidden_paths = glob.glob(os.path.join(tmp_dir, ".??*"))
        paths = glob.glob(os.path.join(tmp_dir, "*"))
        for path in paths + hidden_paths:
            try:
                shutil.rmtree(path, ignore_errors=True)
            except OSError:
                pass


if __name__ == '__main__':
    print "root dir:         " + get_root_dir()
    print "tmp dir:          " + get_tmp_dir()
