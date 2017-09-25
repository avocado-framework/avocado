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
import shutil
import time
import tempfile

from . import job_id
from . import settings
from .output import LOG_JOB
from ..utils import path as utils_path
from ..utils.data_structures import Borg

if 'VIRTUAL_ENV' in os.environ:
    SYSTEM_BASE_DIR = os.environ['VIRTUAL_ENV']
    USER_BASE_DIR = SYSTEM_BASE_DIR
else:
    SYSTEM_BASE_DIR = '/var/lib/avocado'
    USER_BASE_DIR = os.path.expanduser('~/avocado')

SYSTEM_TEST_DIR = os.path.join(SYSTEM_BASE_DIR, 'tests')
SYSTEM_DATA_DIR = os.path.join(SYSTEM_BASE_DIR, 'data')
SYSTEM_LOG_DIR = os.path.join(SYSTEM_BASE_DIR, 'job-results')

USER_TEST_DIR = os.path.join(USER_BASE_DIR, 'tests')
USER_DATA_DIR = os.path.join(USER_BASE_DIR, 'data')
USER_LOG_DIR = os.path.join(USER_BASE_DIR, 'job-results')


def _get_settings_dir(dir_name):
    """
    Returns a given "datadir" directory as set by the configuration system
    """
    path = settings.settings.get_value('datadir.paths', dir_name, 'path')
    return os.path.abspath(path)


def _get_rw_dir(settings_location, system_location, user_location):
    if utils_path.usable_rw_dir(settings_location):
        return settings_location

    if utils_path.usable_rw_dir(system_location):
        return system_location

    user_location = os.path.expanduser(user_location)
    if utils_path.usable_rw_dir(user_location):
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

    The heuristics used to determine the test dir are:
    1) If an explicit test dir is set in the configuration system, it
    is used.
    2) If user is running Avocado out of the source tree, the example
    test dir is used
    3) System wide test dir is used
    4) User default test dir (~/avocado/tests) is used
    """
    configured = _get_settings_dir('test_dir')
    if utils_path.usable_ro_dir(configured):
        return configured

    if settings.settings.intree:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base_dir, 'examples', 'tests')

    if utils_path.usable_ro_dir(SYSTEM_TEST_DIR):
        return SYSTEM_TEST_DIR

    if utils_path.usable_ro_dir(USER_TEST_DIR):
        return USER_TEST_DIR


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


def create_job_logs_dir(base_dir=None, unique_id=None):
    """
    Create a log directory for a job, or a stand alone execution of a test.

    :param base_dir: Base log directory, if `None`, use value from configuration.
    :param unique_id: The unique identification. If `None`, create one.
    :rtype: basestring
    """
    start_time = time.strftime('%Y-%m-%dT%H.%M')
    if base_dir is None:
        base_dir = get_logs_dir()
    if not os.path.exists(base_dir):
        utils_path.init_dir(base_dir)
    # Stand alone tests handling
    if unique_id is None:
        unique_id = job_id.create_unique_job_id()

    logdir = os.path.join(base_dir, 'job-%s-%s' % (start_time, unique_id[:7]))
    for i in xrange(7, len(unique_id)):
        try:
            os.mkdir(logdir)
        except OSError:
            logdir += unique_id[i]
            continue
        return logdir
    logdir += "."
    for i in xrange(1000):
        try:
            os.mkdir(logdir + str(i))
        except OSError:
            continue
        return logdir + str(i)
    raise IOError("Unable to create unique logdir in 1000 iterations: %s"
                  % (logdir))


class _TmpDirTracker(Borg):

    def __init__(self):
        Borg.__init__(self)
        self.basedir = None

    def get(self, basedir):
        if not hasattr(self, 'tmp_dir'):
            if basedir is not None:
                self.basedir = basedir
            self.tmp_dir = tempfile.mkdtemp(prefix='avocado_',
                                            dir=self.basedir)
        elif basedir is not None and basedir != self.basedir:
            LOG_JOB.error("The tmp_dir was already created. The new basedir "
                          "you're trying to provide will have no effect.")
        return self.tmp_dir

    def unittest_refresh_dir_tracker(self):
        """
        This force-removes the tmp_dir and refreshes the tracker to create new
        """
        if not hasattr(self, "tmp_dir"):
            return
        shutil.rmtree(self.__dict__.pop("tmp_dir"))

    def __del__(self):
        tmp_dir = getattr(self, 'tmp_dir', None)

        if tmp_dir is not None and self.basedir is None:
            try:
                if os.path.isdir(tmp_dir):
                    shutil.rmtree(tmp_dir)
            except AttributeError:
                pass


_tmp_tracker = _TmpDirTracker()


def get_tmp_dir(basedir=None):
    """
    Get the most appropriate tmp dir location.

    The tmp dir is where artifacts produced by the test are kept.

    Examples:
        * Copies of a test suite source code
        * Compiled test suite source code
    """
    tmp_dir = _tmp_tracker.get(basedir)
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
