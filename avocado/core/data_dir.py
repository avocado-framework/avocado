#!/usr/bin/env python

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
# Copyright: Red Hat Inc. 2013-2015
# Author: Lucas Meneghel Rodrigues <lmr@redhat.com>

"""
Library used to let avocado tests find important paths in the system.

The general reasoning to find paths is:

* When running in tree, don't honor avocado.conf. Also, we get to
  run/display the example tests shipped in tree.
* When avocado.conf is in /etc/avocado, or ~/.config/avocado, then honor
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

from . import job_id
from . import settings
from ..utils import path as utils_path
from ..utils.data_structures import Borg

_BASE_DIR = os.path.join(sys.modules[__name__].__file__, "..", "..", "..")
_BASE_DIR = os.path.abspath(_BASE_DIR)
_IN_TREE_TESTS_DIR = os.path.join(_BASE_DIR, 'examples', 'tests')

SYSTEM_BASE_DIR = '/var/lib/avocado'
if 'VIRTUAL_ENV' in os.environ:
    SYSTEM_BASE_DIR = os.environ['VIRTUAL_ENV']
SYSTEM_TEST_DIR = os.path.join(SYSTEM_BASE_DIR, 'tests')
SYSTEM_DATA_DIR = os.path.join(SYSTEM_BASE_DIR, 'data')
SYSTEM_LOG_DIR = os.path.join(SYSTEM_BASE_DIR, 'job-results')

USER_BASE_DIR = os.path.expanduser('~/avocado')
USER_TEST_DIR = os.path.join(USER_BASE_DIR, 'tests')
USER_DATA_DIR = os.path.join(USER_BASE_DIR, 'data')
USER_LOG_DIR = os.path.join(USER_BASE_DIR, 'job-results')


def _get_settings_dir(dir_name):
    """
    Returns a given "datadir" directory as set by the configuration system
    """
    return os.path.expanduser(settings.settings.get_value('datadir.paths', dir_name))


def _get_rw_dir(settings_location, system_location, user_location):
    if utils_path.usable_rw_dir(settings_location):
        return settings_location

    if utils_path.usable_rw_dir(system_location):
        return system_location

    user_location = os.path.expanduser(user_location)
    if utils_path.usable_rw_dir(user_location):
        return user_location


def _get_ro_dir(settings_location, system_location, user_location):
    if not settings.settings.intree:
        if utils_path.usable_ro_dir(settings_location):
            return settings_location

    if utils_path.usable_ro_dir(system_location):
        return system_location

    user_location = os.path.expanduser(user_location)
    if utils_path.usable_ro_dir(user_location):
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
    return _get_rw_dir(_get_settings_dir('base_dir'),
                       SYSTEM_BASE_DIR, USER_BASE_DIR)


def get_test_dir():
    """
    Get the most appropriate test location.

    The test location is where we store tests written with the avocado API.
    """
    if settings.settings.intree:
        return _IN_TREE_TESTS_DIR
    return _get_ro_dir(_get_settings_dir('test_dir'), SYSTEM_TEST_DIR, USER_TEST_DIR)


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
    return _get_rw_dir(_get_settings_dir('data_dir'),
                       SYSTEM_DATA_DIR, USER_DATA_DIR)


def get_datafile_path(*args):
    """
    Get a path relative to the data dir.

    :param args: Arguments passed to os.path.join. Ex ('images', 'jeos.qcow2')
    """
    new_args = tuple([get_data_dir()] + list(args))
    return os.path.join(*new_args)


def get_logs_dir():
    """
    Get the most appropriate log dir location.

    The log dir is where we store job/test logs in general.
    """
    return _get_rw_dir(_get_settings_dir('logs_dir'),
                       SYSTEM_LOG_DIR, USER_LOG_DIR)


def create_job_logs_dir(logdir=None, unique_id=None):
    """
    Create a log directory for a job, or a stand alone execution of a test.

    :param logdir: Base log directory, if `None`, use value from configuration.
    :param unique_id: The unique identification. If `None`, create one.
    :rtype: basestring
    """
    start_time = time.strftime('%Y-%m-%dT%H.%M')
    if logdir is None:
        logdir = get_logs_dir()
    if not os.path.exists(logdir):
        utils_path.init_dir(logdir)
    # Stand alone tests handling
    if unique_id is None:
        unique_id = job_id.create_unique_job_id()

    debugdir = os.path.join(logdir, 'job-%s-%s' % (start_time, unique_id[:7]))
    for i in xrange(7, len(unique_id)):
        try:
            os.mkdir(debugdir)
        except OSError:
            debugdir += unique_id[i]
            continue
        return debugdir
    debugdir += "."
    for i in xrange(1000):
        try:
            os.mkdir(debugdir + str(i))
        except OSError:
            continue
        return debugdir + str(i)
    raise IOError("Unable to create unique logdir in 1000 iterations: %s"
                  % (debugdir))


class _TmpDirTracker(Borg):

    def __init__(self):
        Borg.__init__(self)

    def get(self):
        if not hasattr(self, 'tmp_dir'):
            self.tmp_dir = tempfile.mkdtemp(prefix='avocado_')
        return self.tmp_dir

    def __del__(self):
        tmp_dir = getattr(self, 'tmp_dir', None)
        if tmp_dir is not None:
            try:
                if os.path.isdir(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except AttributeError:
                pass

_tmp_tracker = _TmpDirTracker()


def get_tmp_dir():
    """
    Get the most appropriate tmp dir location.

    The tmp dir is where artifacts produced by the test are kept.

    Examples:
        * Copies of a test suite source code
        * Compiled test suite source code
    """
    tmp_dir = _tmp_tracker.get()
    # This assert is a security mechanism for avoiding re-creating
    # the temporary directory, since that's a security breach.
    msg = ('Temporary dir %s no longer exists. This likely means the '
           'directory was incorrectly deleted before the end of the job' %
           tmp_dir)
    assert os.path.isdir(tmp_dir), msg
    return tmp_dir


def clean_tmp_files():
    """
    Try to clean the tmp directory by removing it.

    This is a useful function for avocado entry points looking to clean after
    tests/jobs are done. If OSError is raised, silently ignore the error.
    """
    try:
        tmp_dir = get_tmp_dir()
    except AssertionError:
        return
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except OSError:
        pass
