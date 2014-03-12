#!/usr/bin/python
"""
Library used to let avocado tests find important paths in the system.
"""
import os
import sys
import glob
import shutil

_ROOT_PATH = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
DEFAULT_ROOT_DIR = os.path.abspath(_ROOT_PATH)
DEFAULT_TMP_DIR = os.path.join(DEFAULT_ROOT_DIR, 'tmp')


def get_root_dir():
    return DEFAULT_ROOT_DIR


def get_test_dir():
    return os.path.join(get_root_dir(), 'tests')


def get_logs_dir():
    return os.path.join(get_root_dir(), 'logs')


def get_tmp_dir():
    if not os.path.isdir(DEFAULT_TMP_DIR):
        os.makedirs(DEFAULT_TMP_DIR)
    return DEFAULT_TMP_DIR


def clean_tmp_files():
    if os.path.isdir(DEFAULT_TMP_DIR):
        hidden_paths = glob.glob(os.path.join(DEFAULT_TMP_DIR, ".??*"))
        paths = glob.glob(os.path.join(DEFAULT_TMP_DIR, "*"))
        for path in paths + hidden_paths:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == '__main__':
    print "root dir:         " + DEFAULT_ROOT_DIR
    print "tmp dir:          " + DEFAULT_TMP_DIR
