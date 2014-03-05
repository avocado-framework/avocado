#!/usr/bin/python
"""
Library used to let avocado tests find important paths in the system.
"""
import os
import sys
import glob
import shutil

_ROOT_PATH = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
ROOT_DIR = os.path.abspath(_ROOT_PATH)
TMP_DIR = os.path.join(ROOT_DIR, 'tmp')


def get_root_dir():
    return ROOT_DIR

def get_tmp_dir():
    if not os.path.isdir(TMP_DIR):
        os.makedirs(TMP_DIR)
    return TMP_DIR

def clean_tmp_files():
    if os.path.isdir(TMP_DIR):
        hidden_paths = glob.glob(os.path.join(TMP_DIR, ".??*"))
        paths = glob.glob(os.path.join(TMP_DIR, "*"))
        for path in paths + hidden_paths:
            shutil.rmtree(path, ignore_errors=True)


if __name__ == '__main__':
    print "root dir:         " + ROOT_DIR
    print "tmp dir:          " + TMP_DIR
