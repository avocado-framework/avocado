#!/usr/bin/python

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See LICENSE for more details.
#
# Copyright: Red Hat Inc. 2013-2014
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Library used to let avocado tests find important paths in the system.

The general reasoning to find paths is:

* When running in tree, don't honor settings.ini. Also, we get to
  run/display the example tests shipped in tree.
* When settings.ini is in /etc/avocado, or ~/.config/avocado, then honor
  the values there as much as possible. If they point to a location where
  we can't write to, use the next best location available.
* The next best location is the default system wide one.
* The next best location is the default user specific one.
"""
import os
import sys
import shutil
import time
import tempfile
import uuid

from avocado.core import job_id
from avocado.utils import path
from avocado.settings import settings

_BASE_DIR = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
_BASE_DIR = os.path.abspath(_BASE_DIR)
_IN_TREE_TESTS_DIR = os.path.join(_BASE_DIR, 'tests')

SETTINGS_BASE_DIR = os.path.expanduser(settings.get_value('runner', 'base_dir'))
SETTINGS_TEST_DIR = os.path.expanduser(settings.get_value('runner', 'test_dir'))
SETTINGS_DATA_DIR = os.path.expanduser(settings.get_value('runner', 'data_dir'))
SETTINGS_LOG_DIR = os.path.expanduser(settings.get_value('runner', 'logs_dir'))
SETTINGS_TMP_DIR = os.path.expanduser(settings.get_value('runner', 'tmp_dir'))

SYSTEM_BASE_DIR = '/var/lib/avocado'
SYSTEM_TEST_DIR = os.path.join(SYSTEM_BASE_DIR, 'tests')
SYSTEM_DATA_DIR = os.path.join(SYSTEM_BASE_DIR, 'data')
SYSTEM_LOG_DIR = os.path.join(SYSTEM_BASE_DIR, 'job-results')
SYSTEM_TMP_DIR = '/var/tmp/avocado'

USER_BASE_DIR = os.path.expanduser('~/avocado')
USER_TEST_DIR = os.path.join(USER_BASE_DIR, 'tests')
USER_DATA_DIR = os.path.join(USER_BASE_DIR, 'data')
USER_LOG_DIR = os.path.join(USER_BASE_DIR, 'job-results')
USER_TMP_DIR = '/var/tmp/avocado'


def _usable_rw_dir(directory):
    """
    Verify wether we can use this dir (read/write).

    Checks for appropriate permissions, and creates missing dirs as needed.

    :param directory: Directory
    """
    if os.path.isdir(directory):
        try:
            fd, path = tempfile.mkstemp(dir=directory)
            os.close(fd)
            os.unlink(path)
            return True
        except OSError:
            pass
    else:
        try:
            os.makedirs(directory)
            return True
        except OSError:
            pass

    return False


def _usable_ro_dir(directory):
    """
    Verify whether dir exists and we can access its contents.

    If a usable RO is there, use it no questions asked. If not, let's at
    least try to create one.

    :param directory: Directory
    """
    cwd = os.getcwd()
    if os.path.isdir(directory):
        try:
            os.chdir(directory)
            os.chdir(cwd)
            return True
        except OSError:
            pass
    else:
        try:
            os.makedirs(directory)
            return True
        except OSError:
            pass

    return False


def _get_rw_dir(settings_location, system_location, user_location):
    if not settings.intree:
        if _usable_rw_dir(settings_location):
            return settings_location

    if _usable_rw_dir(system_location):
        return system_location

    user_location = os.path.expanduser(user_location)
    if _usable_rw_dir(user_location):
        return user_location


def _get_ro_dir(settings_location, system_location, user_location):
    if not settings.intree:
        if _usable_ro_dir(settings_location):
            return settings_location

    if _usable_ro_dir(system_location):
        return system_location

    user_location = os.path.expanduser(user_location)
    if _usable_ro_dir(user_location):
        return user_location


def get_base_dir():
    """
    Get the most appropriate base dir.

    The base dir is the parent location for most of the avocado other
    important directories.

    Examples:
        * Log directory
        * Data directory
        * Tests directory
    """
    return _get_rw_dir(SETTINGS_BASE_DIR, SYSTEM_BASE_DIR, USER_BASE_DIR)


def get_test_dir():
    """
    Get the most appropriate test location.

    The test location is where we store tests written with the avocado API.
    """
    if settings.intree:
        return _IN_TREE_TESTS_DIR
    return _get_ro_dir(SETTINGS_TEST_DIR, SYSTEM_TEST_DIR, USER_TEST_DIR)


def get_data_dir():
    """
    Get the most appropriate data dir location.

    The data dir is the location where any data necessary to job and test
    operations are located.

    Examples:
        * ISO files
        * GPG files
        * VM images
        * Reference bitmaps
    """
    return _get_rw_dir(SETTINGS_DATA_DIR, SYSTEM_DATA_DIR, USER_DATA_DIR)


def get_logs_dir():
    """
    Get the most appropriate log dir location.

    The log dir is where we store job/test logs in general.
    """
    return _get_rw_dir(SETTINGS_LOG_DIR, SYSTEM_LOG_DIR, USER_LOG_DIR)


def get_job_logs_dir(args=None, unique_id=None):
    """
    Create a log directory for a job, or a stand alone execution of a test.

    Also, symlink the created dir with [avocado-logs-dir]/latest.

    :param args: :class:`argparse.Namespace` instance with cmdline arguments
                 (optional).
    :rtype: basestring
    """
    start_time = time.strftime('%Y-%m-%dT%H.%M')
    if args is not None:
        logdir = args.logdir or get_logs_dir()
    else:
        logdir = get_logs_dir()
    # Stand alone tests handling
    if unique_id is None:
        unique_id = job_id.get_job_id()

    debugbase = 'job-%s-%s' % (start_time, unique_id[:7])
    debugdir = path.init_dir(logdir, debugbase)
    latestdir = os.path.join(logdir, "latest")
    try:
        os.unlink(latestdir)
    except OSError:
        pass
    os.symlink(debugbase, latestdir)
    return debugdir


def get_tmp_dir():
    """
    Get the most appropriate tmp dir location.

    The tmp dir is where artifacts produced by the test are kept.

    Examples:
        * Copies of a test suite source code
        * Compiled test suite source code
    """
    return _get_rw_dir(SETTINGS_TMP_DIR, SYSTEM_TMP_DIR, USER_TMP_DIR)


def clean_tmp_files():
    """
    Try to clean the tmp directory by removing it.

    This is a useful function for avocado entry points looking to clean after
    tests/jobs are done. If OSError is raised, silently ignore the error.
    """
    tmp_dir = get_tmp_dir()
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except OSError:
        pass
